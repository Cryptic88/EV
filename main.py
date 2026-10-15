import threading
import webbrowser
import argparse

from PIL import Image, ImageDraw
import pystray

from core.assistant import EVAssistant
from web.app import create_app


APP_URL = "http://127.0.0.1:5000"


def create_tray_image():

    size = 64
    image = Image.new("RGB", (size, size), "#020812")
    draw = ImageDraw.Draw(image)

    draw.ellipse(
        (6, 6, size - 6, size - 6),
        fill="#031b35",
        outline="#00b7ff",
        width=3,
    )

    draw.text((20, 18), "E.V.", fill="#c7d8ee")

    return image


def start_web_server(state):

    app = create_app(state)

    web_thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False,
        ),
        daemon=True,
    )

    web_thread.start()


def open_ui():

    webbrowser.open(APP_URL)


def run_assistant(assistant):
    # Windows audio/browser tools use COM on the assistant's worker thread.
    from comtypes import CoInitialize, CoUninitialize
    CoInitialize()
    try:
        assistant.run()
    finally:
        try:
            assistant.automation_tools.browser_tools.close()
        finally:
            CoUninitialize()


def build_tray_icon(assistant):

    def on_open_ui(icon, item):
        open_ui()

    def on_reset(icon, item):
        assistant.state.reset()

    def on_quit(icon, item):
        assistant.state.stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open UI", on_open_ui),
        pystray.MenuItem("Reset Assistant", on_reset),
        pystray.MenuItem("Quit", on_quit),
    )

    return pystray.Icon(
        "E.V.",
        create_tray_image(),
        "E.V. Assistant",
        menu,
    )


def main():

    parser = argparse.ArgumentParser(description='E.V. voice assistant')
    parser.add_argument('--connect-whatsapp', action='store_true', help='Open manual WhatsApp Web linking at startup')
    args = parser.parse_args()
    # Create E.V.
    assistant = EVAssistant()
    assistant.connect_whatsapp_on_start = args.connect_whatsapp

    # Start local web interface in the background.
    start_web_server(assistant.state)

    # Start the assistant in the background so the tray stays responsive.
    assistant_thread = threading.Thread(
        target=run_assistant,
        args=(assistant,),
        daemon=True,
    )

    assistant_thread.start()

    tray_icon = build_tray_icon(assistant)

    print()
    print("==============================")
    print(" E.V. - ENHANCED VOICE AI")
    print("==============================")
    print()
    print("Running in the background.")
    print("Open the UI from the tray menu or visit:")
    print(APP_URL)
    print()

    tray_icon.run()


if __name__ == "__main__":
    main()
