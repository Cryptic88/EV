"""Real model smoke test without microphone capture or audio playback."""
from pathlib import Path
import wave
import numpy as np
from faster_whisper import WhisperModel
from config import settings
from core.state import AssistantState
from speech.speaker import Speaker
from speech.vad import VoiceActivityDetector


def main():
    print("Loading Kokoro ...", flush=True)
    speaker = Speaker(AssistantState())
    prepared = []
    # Exercise the production synthesis and playback queues without playing audio.
    speaker._play_prepared = prepared.append
    speaker.speak_stream(iter(["Hello.", "The local voice system is ready."]))
    assert len(prepared) == 2
    rate = prepared[0].sample_rate
    assert all(part.sample_rate == rate for part in prepared)
    audio = np.concatenate([part.samples for part in prepared])
    assert np.isfinite(audio).all() and len(audio) > rate
    path = Path("artifacts/local-voice-check.wav")
    path.parent.mkdir(exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    print("Checking Silero on silence and synthesized speech ...", flush=True)
    vad = VoiceActivityDetector()
    assert not any(vad.is_speech(np.zeros(512, dtype=np.float32)) for _ in range(32))
    # Linear interpolation is sufficient for this smoke test's VAD input.
    speech = np.interp(np.arange(0, len(audio), rate / settings.SAMPLE_RATE),
                       np.arange(len(audio)), audio).astype(np.float32)
    assert any(vad.is_speech(speech[i:i+512]) for i in range(0, len(speech) - 512, 512))
    print("Transcribing generated WAV ...", flush=True)
    whisper = WhisperModel(settings.WHISPER_MODEL_SIZE, device=settings.WHISPER_DEVICE,
                           compute_type=settings.WHISPER_COMPUTE_TYPE)
    segments, _ = whisper.transcribe(str(path), language="en", vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments)
    print(text, flush=True)
    assert "local" in text.lower() and "ready" in text.lower(), text
    print(f"PASS: Kokoro, Silero and Whisper. Sample: {path.resolve()}")


if __name__ == "__main__":
    main()
