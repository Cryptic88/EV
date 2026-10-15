from config.settings import SYSTEM_PROMPT
from tools.app_catalog import AppCatalog


def get_system_prompt():
    names = ", ".join(AppCatalog().names())
    return (SYSTEM_PROMPT + " Configured application shortcuts: " + names + ". "
            "Use the app's name as process_name for open_program or close_program. "
            "Outlook means the new Outlook; Outlook (classic) is a separate shortcut. "
            "If the user asks for their IDE without naming one, ask which IDE. "
            "Opening an application launches it; it does not give you tools to read "
            "messages or control the app's contents.")
