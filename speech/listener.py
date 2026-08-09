import json
import time
from collections import deque
import time
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

        return normalized.startswith("e v") or normalized.startswith("ev")

    def _chunk_to_audio(self, chunk):

        audio = np.frombuffer(
            chunk,
            dtype=np.int16
        ).astype(np.float32)

        return audio / 32768.0

    def record_until_wake_then_silence(self):

        self.state.set_status("listening")

        wake_recognizer = self._create_wake_recognizer()
        pre_roll = deque(maxlen=8)
        command_frames = []
        wake_detected = False
        silence_start = None
        start_time = time.time()

        block_size = 4000

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=block_size,
        ) as stream:

            while True:

                if self.state.is_stopped():
                    break

                if time.time() - start_time > MAX_RECORD_SECONDS:
                    break

                chunk, overflowed = stream.read(block_size)

                if overflowed:
                    continue

                audio_chunk = np.frombuffer(
                    chunk,
                    dtype=np.int16
                ).copy()

                if not wake_detected:

                    pre_roll.append(audio_chunk)

                    if wake_recognizer.AcceptWaveform(chunk):
                        result = json.loads(wake_recognizer.Result())
                        wake_text = result.get("text", "").strip()

                        if self._matches_wake_text(wake_text):
                            wake_detected = True
                            command_frames.extend(list(pre_roll))
                            silence_start = None
                            continue

                    partial = json.loads(
                        wake_recognizer.PartialResult()
                    ).get("partial", "").strip()

                    if self._matches_wake_text(partial):
                        wake_detected = True
                        command_frames.extend(list(pre_roll))
                        silence_start = None

                    continue

                command_frames.append(audio_chunk)

                volume = np.abs(audio_chunk).mean() / 32768.0

                if volume < SILENCE_THRESHOLD:

                    if silence_start is None:
                        silence_start = time.time()

                    elif (
                        time.time() - silence_start > SILENCE_DURATION
                        and len(command_frames) > 5
                    ):
                        break

                else:
                    silence_start = None

        if not wake_detected or not command_frames:
            return None

        audio = np.concatenate(command_frames, axis=0).flatten()

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