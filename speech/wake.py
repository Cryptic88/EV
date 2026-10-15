"""Local wake detectors; a custom E.V. ONNX model is opt-in."""
import json
from pathlib import Path
import numpy as np
from config import settings


class WakeDetector:
    def __init__(self):
        self.backend = settings.WAKE_BACKEND
        if self.backend == "vosk":
            from vosk import Model
            self.model = Model(lang="en-us")
        elif self.backend == "openwakeword":
            from openwakeword.model import Model
            if not settings.WAKE_MODEL_PATH or not Path(settings.WAKE_MODEL_PATH).is_file():
                raise ValueError("Set WAKE_MODEL_PATH to a trained E.V. .onnx model; see README.md")
            self.model = Model(wakeword_models=[settings.WAKE_MODEL_PATH], inference_framework="onnx")
        else:
            raise ValueError("WAKE_BACKEND must be vosk or openwakeword")
        self.reset()

    def reset(self):
        self.pending = np.empty(0, dtype=np.int16)
        if self.backend == "vosk":
            from vosk import KaldiRecognizer
            self.recognizer = KaldiRecognizer(self.model, settings.SAMPLE_RATE,
                json.dumps(["e v", "ev", "hey e v", "hey ev", "okay e v", "okay ev", "[unk]"]))
        else:
            self.model.reset()

    @staticmethod
    def matches(text):
        text = " ".join(text.lower().replace(".", " ").replace(",", " ").split())
        return any(text == phrase or text.startswith(phrase + " ") for phrase in
                   ("e v", "ev", "hey e v", "hey ev", "okay e v", "okay ev", "ok e v", "ok ev"))

    def detected(self, audio):
        if self.backend == "vosk":
            if self.recognizer.AcceptWaveform(audio.tobytes()):
                return self.matches(json.loads(self.recognizer.Result()).get("text", ""))
            return self.matches(json.loads(self.recognizer.PartialResult()).get("partial", ""))
        self.pending = np.concatenate((self.pending, audio))
        while self.pending.size >= 1280:  # 80 ms PCM frames for openWakeWord.
            frame, self.pending = self.pending[:1280], self.pending[1280:]
            if any(float(score) >= settings.WAKE_THRESHOLD for score in self.model.predict(frame).values()):
                return True
        return False
