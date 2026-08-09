import re
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

    def has_wake_phrase(self, text):

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.lower()
        ).strip()

        tokens = normalized.split()

        if not tokens:
            return False

        if tokens[0] == "ev":
            return True

        if len(tokens) >= 2 and tokens[0] == "e" and tokens[1] == "v":
            return True

        return False

    def strip_wake_phrase(self, text):

        cleaned = re.sub(
            r"^[^a-z0-9]*",
            "",
            text.lower()
        )

        cleaned = re.sub(
            r"^(e\s*\.?\s*v\s*\.?\s*)",
            "",
            cleaned
        )

        return cleaned.strip()

    def wake_cooldown(self):

        self.state.set_status("idle")
        time.sleep(WAKE_WORD_COOLDOWN_SECONDS)

    def run(self):

        self.state.reset()

        self.speaker.speak(
            "E.V. online. I'm listening."
        )

        while not self.state.is_stopped():

            # =========================
            # LISTEN
            # =========================

            audio = (
                self.listener
                .record_until_silence()
            )

            if self.state.is_stopped():
                break

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

            if not self.has_wake_phrase(user_text):
                self.wake_cooldown()
                continue

            user_text = self.strip_wake_phrase(user_text)

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

            reply = self.ai.ask(
                user_text
            )

            # =========================
            # SPEAK
            # =========================

            self.speaker.speak(
                reply
            )

            self.wake_cooldown()

        self.state.set_status(
            "idle"
        )