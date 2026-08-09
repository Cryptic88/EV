import time

from speech.listener import MicrophoneListener
from speech.transcriber import Transcriber
from speech.speaker import Speaker

from ai.groq_client import GroqClient

from tools.applications import ApplicationTools
from tools.volume import VolumeTools
from tools.registry import ToolRegistry

from core.state import AssistantState
from config.settings import WAKE_WORD_COOLDOWN_SECONDS


class EVAssistant:

    def __init__(self):

        # =========================
        # STATE
        # =========================

        self.state = AssistantState()

        # =========================
        # SPEECH SYSTEM
        # =========================

        self.listener = MicrophoneListener(
            self.state
        )

        self.transcriber = Transcriber(
            self.state
        )

        self.speaker = Speaker(
            self.state
        )

        # =========================
        # SYSTEM TOOLS
        # =========================

        self.application_tools = ApplicationTools(
            self.state,
            self.listener,
            self.transcriber,
            self.speaker
        )

        self.volume_tools = VolumeTools()

        # =========================
        # TOOL REGISTRY
        # =========================

        self.tool_registry = ToolRegistry(
            self.application_tools,
            self.volume_tools
        )

        # =========================
        # AI
        # =========================

        self.ai = GroqClient(
            self.state,
            self.tool_registry
        )

    def should_exit(self, text):

        exit_phrases = [
            "goodbye e.v.",
            "goodbye ev",
            "shut down e.v.",
            "exit"
        ]

        text = text.lower()

        return any(
            phrase in text
            for phrase in exit_phrases
        )

    def wake_cooldown(self):

        self.state.set_status("idle")
        time.sleep(WAKE_WORD_COOLDOWN_SECONDS)

    def run(self):

        self.state.reset()

        try:
            self.speaker.speak(
                "E.V. online. I'm listening."
            )
        except Exception as error:
            self.state.log(
                f"Startup voice output failed: {error}"
            )

        while not self.state.is_stopped():

            # =========================
            # LISTEN
            # =========================

            audio = (
                self.listener
                .record_until_wake_then_silence()
            )

            if self.state.is_stopped():
                break

            if audio is None:
                self.wake_cooldown()
                continue

            # =========================
            # TRANSCRIBE
            # =========================

            self.state.set_status(
                "thinking"
            )

            user_text = (
                self.transcriber
                .transcribe(audio)
            )

            if not user_text:
                self.wake_cooldown()
                continue

            self.state.log(
                f"You: {user_text}"
            )

            # =========================
            # EXIT CHECK
            # =========================

            if self.should_exit(user_text):

                self.speaker.speak(
                    "Shutting down. Goodbye."
                )

                break

            # =========================
            # AI RESPONSE
            # =========================

            try:
                reply = self.ai.ask(
                    user_text
                )
            except Exception as error:
                self.state.log(
                    f"AI request failed: {error}"
                )
                reply = (
                    "I heard you, but I couldn't process that right now."
                )

            # =========================
            # SPEAK
            # =========================

            try:
                self.speaker.speak(
                    reply
                )
            except Exception as error:
                self.state.log(
                    f"Voice output failed: {error}"
                )

            self.wake_cooldown()

        self.state.set_status(
            "idle"
        )