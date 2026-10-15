"""Generate matching local voice samples without changing the active voice."""
from pathlib import Path
import time
import wave
import numpy as np
from kokoro_onnx import Kokoro
from config import settings


def main():
    model = Kokoro(settings.KOKORO_MODEL_PATH, settings.KOKORO_VOICES_PATH)
    folder = Path(settings.PROJECT_ROOT) / "artifacts" / "voices"
    folder.mkdir(parents=True, exist_ok=True)
    text = "Hi, I'm E.V. What would you like to work on? We can keep talking without repeating my name."
    for label, voice, language in [("Bella", "af_bella", "en-us"), ("Emma", "bf_emma", "en-gb")]:
        started = time.perf_counter()
        audio, rate = model.create(text, voice=voice, lang=language, speed=1.0)
        if not np.isfinite(audio).all() or len(audio) == 0:
            raise RuntimeError(f"Invalid audio for {label}")
        path = folder / f"{label.lower()}.wav"
        with wave.open(str(path), "wb") as output:
            output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            output.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
        print(f"{label}: {len(audio) / rate:.1f}s audio, generated in {time.perf_counter() - started:.1f}s: {path}", flush=True)


if __name__ == "__main__":
    main()
