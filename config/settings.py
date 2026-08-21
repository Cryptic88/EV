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

SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.2
MAX_RECORD_SECONDS = 15

WAKE_WORD_COOLDOWN_SECONDS = 1.25


# =========================
# AI CONFIGURATION
# =========================

WHISPER_MODEL_SIZE = "base.en"

GROQ_MODEL = "openai/gpt-oss-20b"

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