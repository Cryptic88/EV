from faster_whisper import WhisperModel

from config.settings import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


class Transcriber:

    def __init__(self, state):

        self.state = state

        self.state.log(
            "Loading speech-to-text model "
            "(first run downloads it, please wait)..."
        )

        self.model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE
        )

    def transcribe(self, audio):

        if audio is None or len(audio) == 0:
            return ""

        segments, _ = self.model.transcribe(
            audio,
            language="en",
            vad_filter=True,
            condition_on_previous_text=False,
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

        return text
