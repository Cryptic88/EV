from faster_whisper import WhisperModel

from config.settings import WHISPER_MODEL_SIZE


class Transcriber:

    def __init__(self, state):

        self.state = state

        self.state.log(
            "Loading speech-to-text model "
            "(first run downloads it, please wait)..."
        )

        self.model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8"
        )

    def transcribe(self, audio):

        segments, _ = self.model.transcribe(
            audio,
            language="en"
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

        return text