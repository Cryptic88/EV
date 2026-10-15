import asyncio
from dataclasses import dataclass
import os
import queue
import re
import tempfile
import threading
from config import settings
from ai.streaming import SentenceBuffer


@dataclass
class PreparedSpeech:
    text: str
    samples: object = None
    sample_rate: int = 24000
    path: str = None


class Speaker:
    def __init__(self, state):
        self.state = state
        self.kokoro = None
        self.lock = threading.RLock()
        self.synthesis_lock = threading.Lock()
        if settings.TTS_BACKEND not in {"kokoro", "edge"}:
            raise ValueError("TTS_BACKEND must be kokoro or edge")

    def _prepare_local(self, text):
        import numpy as np
        from kokoro_onnx import Kokoro
        with self.synthesis_lock:
            if self.kokoro is None:
                self.kokoro = Kokoro(settings.KOKORO_MODEL_PATH, settings.KOKORO_VOICES_PATH)
            # Split multi-sentence prompts too: punctuation alone does not give
            # Kokoro a reliable pause, especially with its trimmed audio.
            sentences = SentenceBuffer()
            parts = sentences.feed(text + " ") + sentences.finish()
            audio_parts = []
            for part in parts:
                audio, rate = self.kokoro.create(part, voice=settings.KOKORO_VOICE,
                    speed=settings.KOKORO_SPEED, lang=settings.KOKORO_LANGUAGE)
                audio_parts.append(audio)
                if re.search(r'[.!?][\)\]"\u201d\u2019]*$', part.rstrip()):
                    audio_parts.append(np.zeros(round(rate * settings.SENTENCE_PAUSE_SECONDS),
                                                dtype=np.float32))
        return PreparedSpeech(text, samples=np.concatenate(audio_parts), sample_rate=rate)

    def _prepare_edge(self, text):
        import edge_tts
        async def generate(path):
            await edge_tts.Communicate(text, settings.EDGE_VOICE).save(path)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            path = tmp.name
        try:
            asyncio.run(generate(path))
            return PreparedSpeech(text, path=path)
        except BaseException:
            os.remove(path)
            raise

    def _prepare(self, text):
        if settings.TTS_BACKEND == "edge":
            return self._prepare_edge(text)
        try:
            return self._prepare_local(text)
        except Exception:
            if not settings.TTS_ALLOW_EDGE_FALLBACK:
                raise
            self.state.log("Local speech failed; using enabled Edge cloud fallback.")
            return self._prepare_edge(text)

    @staticmethod
    def _discard(prepared):
        if prepared.path and os.path.exists(prepared.path):
            os.remove(prepared.path)

    def _play_prepared(self, prepared):
        with self.lock:
            if self.state.is_stopped():
                return
            self.state.log(f"E.V.: {prepared.text}")
            self.state.set_status("speaking")
            if prepared.path:
                from playsound import playsound
                playsound(prepared.path)
                return
            import sounddevice as sd
            sd.play(prepared.samples, prepared.sample_rate)
            try:
                while sd.get_stream().active:
                    if self.state.stop_event.wait(0.05):
                        break
            finally:
                sd.stop()

    def speak(self, text):
        if not text or self.state.is_stopped():
            return
        prepared = self._prepare(text)
        try:
            self._play_prepared(prepared)
        finally:
            self._discard(prepared)

    def speak_stream(self, sentences, ai=None):
        """LLM -> bounded synthesis worker -> bounded playback worker.

        The next sentence is prepared while the previous audio plays. Tools
        drain both stages before opening a microphone for confirmation.
        """
        text_queue = queue.Queue(maxsize=2)
        audio_queue = queue.Queue(maxsize=2)
        errors = []

        def synthesize():
            while True:
                text = text_queue.get()
                try:
                    if text is None:
                        return
                    if not errors and not self.state.is_stopped():
                        audio_queue.put(self._prepare(text))
                except Exception as error:
                    errors.append(error)
                finally:
                    text_queue.task_done()

        def play():
            while True:
                prepared = audio_queue.get()
                try:
                    if prepared is None:
                        return
                    if not errors and not self.state.is_stopped():
                        self._play_prepared(prepared)
                except Exception as error:
                    errors.append(error)
                finally:
                    try:
                        if prepared is not None:
                            self._discard(prepared)
                    except Exception as error:
                        errors.append(error)
                    finally:
                        audio_queue.task_done()

        def drain():
            text_queue.join()
            audio_queue.join()
            if errors:
                raise errors[0]

        synthesis = threading.Thread(target=synthesize, name="ev-synthesis", daemon=True)
        playback = threading.Thread(target=play, name="ev-playback", daemon=True)
        synthesis.start()
        playback.start()
        if ai is not None:
            ai.before_tool = drain
        try:
            for sentence in sentences:
                if self.state.is_stopped() or errors:
                    break
                if sentence.strip():
                    text_queue.put(sentence)
        finally:
            text_queue.put(None)
            synthesis.join()
            audio_queue.put(None)
            playback.join()
            if ai is not None:
                ai.before_tool = lambda: None
            close = getattr(sentences, "close", None)
            if close:
                close()
        if errors:
            raise errors[0]
