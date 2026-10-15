"""Download public speech assets once; normal voice use then runs locally."""
import argparse
from pathlib import Path
import requests
import shutil
from config import settings


ASSETS = {
    settings.KOKORO_MODEL_PATH: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
    settings.KOKORO_VOICES_PATH: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
    settings.SILERO_MODEL_PATH: "https://raw.githubusercontent.com/snakers4/silero-vad/v5.1.2/src/silero_vad/data/silero_vad.onnx",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wake", action="store_true", help="Download openWakeWord shared feature models")
    args = parser.parse_args()
    if shutil.disk_usage(settings.PROJECT_ROOT).free < 2 * 1024 ** 3:
        raise SystemExit("Free at least 2 GB on the project drive before downloading speech models.")
    for filename, url in ASSETS.items():
        path = Path(filename)
        if path.is_file():
            print(f"Already present: {path.name}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".part")
        print(f"Downloading {path.name} ...", flush=True)
        try:
            with requests.get(url, stream=True, timeout=(20, 60)) as response:
                response.raise_for_status()
                downloaded = 0
                with temporary.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        output.write(chunk)
                        downloaded += len(chunk)
                        print(f"  {path.name}: {downloaded // (1024 * 1024)} MB", flush=True)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    from faster_whisper import WhisperModel
    print(f"Caching Whisper {settings.WHISPER_MODEL_SIZE} ...", flush=True)
    WhisperModel(settings.WHISPER_MODEL_SIZE, device=settings.WHISPER_DEVICE,
                 compute_type=settings.WHISPER_COMPUTE_TYPE)
    if settings.WAKE_BACKEND == "vosk":
        from vosk import Model
        Model(lang="en-us")
    if args.wake:
        from openwakeword.utils import download_models
        download_models()
    print("Speech models ready.")


if __name__ == "__main__":
    main()
