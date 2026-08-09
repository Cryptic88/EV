import asyncio
import os
import tempfile

import edge_tts
from playsound import playsound

from config.settings import EDGE_VOICE


class Speaker:

    def __init__(self, state):
        self.state = state

    async def _generate_speech(self, text, output_path):

        communicate = edge_tts.Communicate(
            text,
            EDGE_VOICE
        )

        await communicate.save(output_path)

    def speak(self, text):

        self.state.log(f"E.V.: {text}")

        self.state.set_status("speaking")

        with tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        ) as tmp:

            output_path = tmp.name

        try:

            asyncio.run(
                self._generate_speech(
                    text,
                    output_path
                )
            )

            playsound(output_path)

        finally:

            if os.path.exists(output_path):
                os.remove(output_path)