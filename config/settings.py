import os


def _load_local_env_file():

    env_path = os.path.join(
        os.path.dirname(
            os.path.dirname(__file__)
        ),
        ".env"
    )

    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:

        for raw_line in env_file:

            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


_load_local_env_file()


# =========================
# AUDIO CONFIGURATION
# =========================

SAMPLE_RATE = 16000
MICROPHONE_DEVICE = os.getenv("MICROPHONE_DEVICE", "").strip() or None
if MICROPHONE_DEVICE is not None and MICROPHONE_DEVICE.isdecimal():
    MICROPHONE_DEVICE = int(MICROPHONE_DEVICE)

SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = float(os.getenv("SILENCE_DURATION", "0.8"))
MAX_RECORD_SECONDS = 15
FOLLOW_UP_SECONDS = float(os.getenv("FOLLOW_UP_SECONDS", "8"))
REPLY_TAIL_SECONDS = float(os.getenv("REPLY_TAIL_SECONDS", "0.2"))

WAKE_WORD_COOLDOWN_SECONDS = 1.25


# =========================
# AI CONFIGURATION
# =========================

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

EDGE_VOICE = os.getenv("EDGE_VOICE", "en-US-JennyNeural")

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
AUTOMATION_ROOTS = [p for p in os.getenv("AUTOMATION_ROOTS", PROJECT_ROOT).split(os.pathsep) if p]
AUTOMATION_TIMEZONE = os.getenv("AUTOMATION_TIMEZONE", "Africa/Johannesburg")
MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "10"))
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
TTS_BACKEND = os.getenv("TTS_BACKEND", "kokoro").lower()
# Never send speech to a cloud fallback unless explicitly enabled.
TTS_ALLOW_EDGE_FALLBACK = os.getenv("TTS_ALLOW_EDGE_FALLBACK", "false").lower() == "true"
KOKORO_MODEL_PATH = os.getenv("KOKORO_MODEL_PATH", os.path.join(MODEL_DIR, "kokoro-v1.0.int8.onnx"))
KOKORO_VOICES_PATH = os.getenv("KOKORO_VOICES_PATH", os.path.join(MODEL_DIR, "voices-v1.0.bin"))
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_bella")
KOKORO_LANGUAGE = os.getenv("KOKORO_LANGUAGE", "en-us")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))
SENTENCE_PAUSE_SECONDS = max(0.0, float(os.getenv("SENTENCE_PAUSE_SECONDS", "0.35")))
VAD_BACKEND = os.getenv("VAD_BACKEND", "silero").lower()
SILERO_MODEL_PATH = os.getenv("SILERO_MODEL_PATH", os.path.join(MODEL_DIR, "silero_vad.onnx"))
VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.5"))
WAKE_BACKEND = os.getenv("WAKE_BACKEND", "vosk").lower()
WAKE_MODEL_PATH = os.getenv("WAKE_MODEL_PATH", "")
WAKE_THRESHOLD = float(os.getenv("WAKE_THRESHOLD", "0.5"))
COMMAND_START_TIMEOUT = float(os.getenv("COMMAND_START_TIMEOUT", "5"))
LLM_BACKEND = os.getenv("LLM_BACKEND", "groq").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")


# =========================
# ASSISTANT CONFIGURATION
# =========================

SYSTEM_PROMPT = (
    "You are E.V., a calm, sharp, hyper-competent personal AI assistant. "

    "Speak concisely and naturally, like you're talking out loud, not writing "
    "an essay. Keep replies to 1-3 sentences unless the user asks for detail. "
    "Use contractions and everyday words. Answer the actual question first. "
    "Vary your sentence lengths and use natural punctuation for spoken pauses. "
    "Skip repetitive openings like 'Certainly', 'Of course', and 'Sure thing'. "
    "Don't repeat the user's request or add a stock offer of more help. "
    "Use plain spoken text, without markdown, bullet lists, or stage directions. "
    "Treat brief follow-ups as part of the ongoing conversation. "

    "You have a dry wit but stay useful and to the point. "

    "You can close programs, open programs, close browser tabs by matching "
    "tab title keywords, and open browser tabs in the default browser. "

    "You can also use browser_search to open a supported website and search "
    "inside it. Supported browser-search websites currently include YouTube, "
    "Google, and Bing. "

    "For example, if the user says 'open YouTube and search for The Boys', "
    "call browser_search with site='youtube' and query='The Boys'. "

    "If the user says 'search YouTube for funny car videos', use "
    "browser_search with site='youtube' and query='funny car videos'. "

    "Do NOT use search_web when the user specifically wants to search "
    "inside YouTube, Google, or Bing. "

    "Use search_web when the user wants information from the internet "
    "rather than browser control. "

    "You can read a specific webpage with read_webpage. "

    "You can adjust the system volume when clearly asked. "

    "Only use the local tools listed by the application. "
    "Never invent tools that are not provided. "

    "Only call a tool when the user's request matches it. "

    "Summarize information naturally in 1-3 spoken sentences instead "
    "of reading URLs or long text aloud."
)

# =========================
# SAFETY / TOOL CONFIG
# =========================

CONFIRM_BEFORE_CLOSING = True


# =========================
# API CONFIGURATION
# =========================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
