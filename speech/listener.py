import json
import time
from collections import deque
import queue
 
import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer, Model
 
from config.settings import (
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MAX_RECORD_SECONDS,
)
 
 
class MicrophoneListener:
 
    def __init__(self, state):
        self.state = state
        self.wake_model = Model(lang="en-us")
 
    def _create_wake_recognizer(self):
 
        grammar = json.dumps([
            "e v",
            "ev",
        ])
 
        return KaldiRecognizer(
            self.wake_model,
            SAMPLE_RATE,
            grammar,
        )
 
    def _matches_wake_text(self, text):
 
        normalized = " ".join(
            text.lower().replace(".", " ").replace(",", " ").split()
        )
 
        if not normalized:
            return False
 
        # Require the actual "e v" / "ev" phrase, not a bare single letter -
        # a lone "e" or "v" is too easy to false-trigger on background
        # noise, breathing, or the start of an unrelated word, which was
        # opening the command window before you'd said anything.
        return (
            normalized in {"e v", "ev"}
            or normalized.startswith("e v ")
            or normalized.startswith("ev ")
            or normalized.startswith("hey e v")
            or normalized.startswith("hey ev")
            or normalized.startswith("okay e v")
            or normalized.startswith("okay ev")
            or normalized.startswith("ok e v")
            or normalized.startswith("ok ev")
        )
 
    def record_until_wake_then_silence(self):
 
        self.state.set_status("listening")
 
        wake_recognizer = self._create_wake_recognizer()
        pre_roll = deque(maxlen=8)
        command_frames = []
        wake_detected = False
        silence_start = None
        start_time = time.time()
        command_start_time = None
 
        block_size = 1600
 
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=block_size,
        ) as stream:
 
            while True:
 
                if self.state.is_stopped():
                    break
 
                # Two separate budgets: MAX_RECORD_SECONDS to hear the wake
                # word at all, then a FRESH MAX_RECORD_SECONDS window to
                # actually say the command once "E.V." is detected. Without
                # this, time spent waiting for the wake word ate into the
                # time you had left to speak your actual request.
                if wake_detected:
                    if time.time() - command_start_time > MAX_RECORD_SECONDS:
                        break
                else:
                    if time.time() - start_time > MAX_RECORD_SECONDS:
                        break
 
                chunk, overflowed = stream.read(block_size)
 
                if overflowed:
                    continue
 
                chunk_bytes = bytes(chunk)
 
                audio_chunk = np.frombuffer(
                    chunk_bytes,
                    dtype=np.int16
                ).copy()
 
                if not wake_detected:
 
                    pre_roll.append(audio_chunk)
 
                    if wake_recognizer.AcceptWaveform(chunk_bytes):
                        result = json.loads(wake_recognizer.Result())
                        wake_text = result.get("text", "").strip()
 
                        if wake_text:
                            self.state.log(f"[wake] heard: '{wake_text}'")
 
                        if self._matches_wake_text(wake_text):
                            self.state.log("[wake] wake word detected")
                            wake_detected = True
                            command_start_time = time.time()
                            command_frames.extend(list(pre_roll))
                            silence_start = None
                            continue
 
                    partial = json.loads(
                        wake_recognizer.PartialResult()
                    ).get("partial", "").strip()
 
                    if self._matches_wake_text(partial):
                        self.state.log(f"[wake] wake word detected (partial: '{partial}')")
                        wake_detected = True
                        command_start_time = time.time()
                        command_frames.extend(list(pre_roll))
                        silence_start = None
 
                    continue
 
                command_frames.append(audio_chunk)
 
                volume = np.abs(audio_chunk).mean() / 32768.0
 
                # Grace period: don't let silence end the recording in the
                # first 0.8s after the wake word - there's often a brief
                # natural pause between saying "E.V." and starting your
                # actual command.
                grace_period_active = (
                    time.time() - command_start_time < 0.8
                )
 
                if volume < SILENCE_THRESHOLD and not grace_period_active:
 
                    if silence_start is None:
                        silence_start = time.time()
 
                    elif (
                        time.time() - silence_start > SILENCE_DURATION
                        and len(command_frames) > 5
                    ):
                        break
 
                else:
                    silence_start = None
 
        if not wake_detected:
            self.state.log("[wake] timed out - no wake word heard, listening again")
            return None
 
        if not command_frames:
            return None
 
        audio = np.concatenate(command_frames, axis=0).flatten()
 
        # RawInputStream gives us raw int16 samples (~-32768 to 32767).
        # Whisper expects normalized float32 samples in [-1, 1] - without
        # this conversion, Whisper receives wildly out-of-range values and
        # hallucinates plausible-sounding but wrong text instead of failing
        # loudly.
        audio = audio.astype(np.float32) / 32768.0
 
        return audio
 
    def record_until_silence(self):
        """
        Records microphone input until the user stops talking.
        Returns the recorded audio as a NumPy array.
        """
 
        self.state.set_status("listening")
 
        audio_queue = queue.Queue()
 
        def callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())
 
        frames = []
 
        silence_start = None
        start_time = time.time()
 
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            callback=callback
        ):
 
            while True:
 
                if self.state.is_stopped():
                    break
 
                try:
                    chunk = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
 
                frames.append(chunk)
 
                volume = np.abs(chunk).mean()
 
                # Detect silence
                if volume < SILENCE_THRESHOLD:
 
                    if silence_start is None:
                        silence_start = time.time()
 
                    elif (
                        time.time() - silence_start > SILENCE_DURATION
                        and len(frames) > 5
                    ):
                        break
 
                else:
                    silence_start = None
 
                # Maximum recording time
                if time.time() - start_time > MAX_RECORD_SECONDS:
                    break
 
        if not frames:
            return np.zeros(1, dtype=np.float32)
 
        audio = np.concatenate(frames, axis=0).flatten()
 
        return audio
