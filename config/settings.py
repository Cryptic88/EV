import os


# =========================
# AUDIO CONFIGURATION
# =========================

SAMPLE_RATE = 16000

SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.2
MAX_RECORD_SECONDS = 15

WAKE_WORD_COOLDOWN_SECONDS = 1.25


# =========================
# AI CONFIGURATION
# =========================

WHISPER_MODEL_SIZE = "base.en"

GROQ_MODEL = "llama-3.1-8b-instant"

EDGE_VOICE = "en-US-JennyNeural"


# =========================
# ASSISTANT CONFIGURATION
# =========================

SYSTEM_PROMPT = (
    "You are E.V., a calm, sharp, hyper-competent personal AI assistant. "
    "Speak concisely and naturally, like you're talking out loud, not writing "
    "an essay. Keep replies to 1-3 sentences unless the user asks for detail. "
    "You have a dry wit but stay useful and to the point. "
    "You can close programs, open programs, close browser tabs by matching "
    "tab title keywords, and open browser tabs in the default browser when "
    "clearly asked. Adjust the system volume when clearly asked. "
    "You do not have web search, browser, or internet access. Only use the "
    "local tools listed by the application. Never invent tools that are not "
    "provided. "
    "Only treat a message as a command when it begins with a clear wake phrase "
    "like 'E V' or 'EV' spoken by the user. Ignore background noise and partial "
    "matches. "
    "Only call a tool when the user's request matches it."
)


# =========================
# SAFETY / TOOL CONFIG
# =========================

CONFIRM_BEFORE_CLOSING = True


# =========================
# API CONFIGURATION
# =========================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")