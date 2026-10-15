"""Silero ONNX recurrent inference at 16 kHz, without a PyTorch runtime.

State/context contract follows silero-vad's official OnnxWrapper.
"""
import numpy as np
from config import settings


class VoiceActivityDetector:
    def __init__(self):
        self.session = None
        if settings.VAD_BACKEND == "silero":
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(settings.SILERO_MODEL_PATH,
                sess_options=options, providers=["CPUExecutionProvider"])
        elif settings.VAD_BACKEND != "energy":
            raise ValueError("VAD_BACKEND must be silero or energy")
        self.reset()

    def reset(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)
        self.pending = np.empty(0, dtype=np.float32)

    def is_speech(self, audio):
        audio = np.asarray(audio, dtype=np.float32).ravel()
        if self.session is None:
            return bool(np.abs(audio).mean() >= settings.SILENCE_THRESHOLD)
        self.pending = np.concatenate((self.pending, audio))
        scores = []
        while self.pending.size >= 512:
            window, self.pending = self.pending[:512], self.pending[512:]
            model_input = np.concatenate((self.context, window[None, :]), axis=1)
            probability, self.state = self.session.run(None, {
                "input": model_input, "state": self.state,
                "sr": np.array(settings.SAMPLE_RATE, dtype=np.int64)})
            self.context = model_input[:, -64:].copy()
            scores.append(float(probability.ravel()[0]))
        return bool(scores and max(scores) >= settings.VAD_THRESHOLD)
