from speech.listener import MicrophoneListener
from speech.transcriber import Transcriber
from speech.speaker import Speaker

from ai.groq_client import GroqClient

from tools.applications import ApplicationTools
from tools.volume import VolumeTools
from tools.web_search import WebTools
from tools.registry import ToolRegistry

from core.state import AssistantState
from config.settings import WAKE_WORD_COOLDOWN_SECONDS
from config import settings


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

        self.web_tools = WebTools()

        # =========================
        # TOOL REGISTRY
        # =========================

        self.tool_registry = ToolRegistry(
            self.application_tools,
            self.volume_tools,
            self.web_tools
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
        self.state.stop_event.wait(WAKE_WORD_COOLDOWN_SECONDS)

    def run(self):

        self.state.reset()
        follow_up = False

        try:
            self.speaker.speak(
                "Hey, I'm here. Tell me what's on your mind."
            )
            follow_up = settings.FOLLOW_UP_SECONDS > 0
            if follow_up:
                self.state.stop_event.wait(settings.REPLY_TAIL_SECONDS)
        except Exception as error:
            self.state.log(
                f"Startup voice output failed: {error}"
            )

        while not self.state.is_stopped():

            # =========================
            # LISTEN
            # =========================

            audio = (self.listener.record_followup() if follow_up else
                     self.listener.record_until_wake_then_silence())
            follow_up = False

            if self.state.is_stopped():
                break

            if audio is None:
                continue

            # =========================
            # TRANSCRIBE
            # =========================

            self.state.set_status(
                "thinking"
            )

            self.state.log(
                f"[debug] captured {len(audio) / 16000:.2f}s of audio"
            )

            user_text = (
                self.transcriber
                .transcribe(audio)
            )

            if not user_text:
                self.state.log(
                    "[debug] transcription was empty - nothing usable heard"
                )
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
                self.speaker.speak_stream(self.ai.ask_stream(user_text), ai=self.ai)
                follow_up = settings.FOLLOW_UP_SECONDS > 0
            except Exception as error:
                self.state.log(
                    f"AI request failed: {error}"
                )
                try:
                    self.speaker.speak("I couldn't finish that request. Please try again.")
                except Exception as voice_error:
                    self.state.log(f"Voice output failed: {voice_error}")

            if follow_up:
                self.state.log(f"[conversation] Listening for a follow-up for {settings.FOLLOW_UP_SECONDS:g}s")
                self.state.stop_event.wait(settings.REPLY_TAIL_SECONDS)
            else:
                self.wake_cooldown()

        self.state.set_status(
            "idle"
        )
