import time
from collections import deque
import numpy as np
import sounddevice as sd
from config import settings
from speech.vad import VoiceActivityDetector
from speech.wake import WakeDetector


class MicrophoneListener:
    def __init__(self, state):
        self.state = state
        self.wake = WakeDetector()
        self.vad = VoiceActivityDetector()
        device = sd.query_devices(settings.MICROPHONE_DEVICE, kind="input")
        host = sd.query_hostapis(device["hostapi"])["name"]
        self.state.log(f"[audio] Microphone: {device['name']} ({host})")

    def record_until_wake_then_silence(self):
        return self._record(wait_for_wake=True)

    def record_until_silence(self):
        return self._record(wait_for_wake=False)

    def record_followup(self):
        return self._record(wait_for_wake=False, start_timeout=settings.FOLLOW_UP_SECONDS)

    def _record(self, wait_for_wake, start_timeout=None):
        if start_timeout is None:
            start_timeout = settings.COMMAND_START_TIMEOUT
        self.state.set_status("listening")
        self.vad.reset()
        if wait_for_wake:
            self.wake.reset()
        pre_roll = deque(maxlen=25)  # 800 ms preserves commands spoken immediately.
        frames = []
        active = not wait_for_wake
        started = time.monotonic() if active else None
        last_speech = None
        speech_started = None
        with sd.RawInputStream(samplerate=settings.SAMPLE_RATE, channels=1,
                               dtype="int16", blocksize=512,
                               device=settings.MICROPHONE_DEVICE) as stream:
            self.state.log("[audio] Microphone stream open (16000 Hz, mono)")
            while not self.state.is_stopped():
                chunk, overflowed = stream.read(512)
                if overflowed:
                    self.vad.reset()
                    continue
                pcm = np.frombuffer(bytes(chunk), dtype=np.int16).copy()
                audio = pcm.astype(np.float32) / 32768.0
                now = time.monotonic()
                if not active:
                    pre_roll.append(audio)
                    if self.wake.detected(pcm):
                        self.state.log("[wake] E.V. detected")
                        active, started = True, now
                        self.vad.reset()
                    continue
                speech = self.vad.is_speech(audio)
                if last_speech is None:
                    # Keep only the lead-in, not the whole idle follow-up window.
                    pre_roll.append(audio)
                    if not speech:
                        if now - started >= start_timeout:
                            return None
                        continue
                    frames.extend(pre_roll)
                    speech_started = now
                else:
                    frames.append(audio)
                if speech:
                    last_speech = now
                if last_speech is not None and now - last_speech >= settings.SILENCE_DURATION:
                    break
                if now - speech_started >= settings.MAX_RECORD_SECONDS:
                    break
        if self.state.is_stopped() or not frames or last_speech is None:
            return None
        return np.concatenate(frames).astype(np.float32)
