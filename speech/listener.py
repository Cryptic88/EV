import time
import queue

import numpy as np
import sounddevice as sd

from config.settings import (
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MAX_RECORD_SECONDS,
)


class MicrophoneListener:

    def __init__(self, state):
        self.state = state

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