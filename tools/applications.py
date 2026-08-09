import os
import subprocess
import time
import webbrowser

import psutil
from pywinauto.keyboard import send_keys

from config.settings import CONFIRM_BEFORE_CLOSING


COMMON_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "word": "winword",
    "excel": "excel",
    "task manager": "taskmgr.exe",
}

BROWSER_PROCESS_NAMES = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "vivaldi.exe",
}

DEFAULT_BROWSER_PROCESS_NAMES = set()


class ApplicationTools:

    def __init__(self, state, listener, transcriber, speaker):
        self.state = state
        self.listener = listener
        self.transcriber = transcriber
        self.speaker = speaker
        self.default_browser_process_name = self._get_default_browser_process_name()

    def _get_default_browser_process_name(self) -> str:

        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
            ) as key:
                prog_id, _ = winreg.QueryValueEx(key, "ProgId")

            prog_id = (prog_id or "").lower()

            if "firefox" in prog_id:
                return "firefox.exe"

            if "chrome" in prog_id or "chromium" in prog_id or "edge" in prog_id:
                return "chrome.exe" if "chrome" in prog_id or "chromium" in prog_id else "msedge.exe"

            if "brave" in prog_id:
                return "brave.exe"

            if "opera" in prog_id:
                return "opera.exe"

            if "vivaldi" in prog_id:
                return "vivaldi.exe"

        except Exception:
            pass

        return "firefox.exe"

    def _is_default_browser_process(self, process_name: str) -> bool:

        if not self.default_browser_process_name:
            return process_name in BROWSER_PROCESS_NAMES

        return process_name == self.default_browser_process_name

    def close_program(self, process_name: str) -> str:

        matches = []

        for proc in psutil.process_iter(["pid", "name"]):

            try:

                name = proc.info["name"]

                if name and process_name.lower() in name.lower():
                    matches.append(proc)

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):
                continue

        if not matches:
            return (
                f"No running program matching "
                f"'{process_name}' was found."
            )

        # Confirmation
        if CONFIRM_BEFORE_CLOSING:

            names = ", ".join(
                sorted(
                    set(
                        p.info["name"]
                        for p in matches
                        if p.info["name"]
                    )
                )
            )

            self.speaker.speak(
                f"I found {names}. "
                "Say yes to confirm closing it."
            )

            audio = self.listener.record_until_silence()

            confirmation = self.transcriber.transcribe(
                audio
            ).lower()

            if "yes" not in confirmation:
                return "Okay, I left it running."

        closed = []

        for proc in matches:

            try:

                proc.terminate()

                if proc.info["name"]:
                    closed.append(proc.info["name"])

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):
                continue

        if closed:

            return (
                f"Closed: "
                f"{', '.join(sorted(set(closed)))}."
            )

        return (
            f"Found '{process_name}' "
            "but couldn't close it."
        )

    def open_program(self, process_name: str) -> str:

        target = COMMON_APPS.get(
            process_name.lower(),
            process_name
        )

        try:

            os.startfile(target)

            return f"Opening {process_name}."

        except FileNotFoundError:

            try:

                subprocess.Popen(
                    target,
                    shell=True
                )

                return f"Opening {process_name}."

            except Exception:

                return (
                    f"Couldn't find '{process_name}'. "
                    "Add its exact executable name "
                    "to COMMON_APPS if necessary."
                )

    def close_browser_tab(self, tab_keywords: str) -> str:

        keywords = [
            part.strip().lower()
            for part in tab_keywords.replace("|", ",").split(",")
            if part.strip()
        ]

        if not keywords:
            return "Please provide at least one tab keyword."

        try:
            from pywinauto import Desktop
        except ImportError:
            return (
                "Browser tab control is not available yet. "
                "Install the pywinauto dependency first."
            )

        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
        except Exception as error:
            return f"Couldn't inspect browser windows: {error}"

        for window in windows:

            try:

                process_id = window.process_id()
                process_name = psutil.Process(process_id).name().lower()

                if not self._is_default_browser_process(process_name):
                    continue

                if process_name == "firefox.exe":
                    return self._close_firefox_tab(window, keywords)

                tab_items = window.descendants(control_type="TabItem")

                for tab_item in tab_items:

                    tab_name = (tab_item.window_text() or "").strip()

                    if not tab_name:
                        continue

                    tab_name_lower = tab_name.lower()

                    if not all(keyword in tab_name_lower for keyword in keywords):
                        continue

                    tab_item.select()
                    window.set_focus()
                    window.type_keys("^w")

                    return (
                        f"Closed the browser tab '{tab_name}' in "
                        f"{process_name.replace('.exe', '').title()}."
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                Exception,
            ):
                continue

        return f"No browser tab matched: {tab_keywords}."

    def _close_firefox_tab(self, window, keywords) -> str:

        try:
            window.restore()
        except Exception:
            pass

        try:
            window.set_focus()
        except Exception:
            pass

        previous_title = None

        for _ in range(75):

            title = self._read_window_title(window)

            normalized_title = title.lower()

            if title:
                if all(keyword in normalized_title for keyword in keywords):
                    try:
                        window.type_keys("^w")
                    except Exception:
                        try:
                            send_keys("^w")
                        except Exception as error:
                            return f"Matched '{title}' but couldn't close it: {error}"

                    return f"Closed the Firefox tab '{title}'."

                if title == previous_title:
                    break

                previous_title = title

            try:
                window.type_keys("^{PGDN}")
            except Exception:
                try:
                    send_keys("^{PGDN}")
                except Exception as error:
                    return f"Couldn't cycle Firefox tabs: {error}"

            time.sleep(0.2)

        return f"No Firefox tab matched: {', '.join(keywords)}."

    def open_browser_tab(self, url: str) -> str:

        try:
            opened = webbrowser.open_new_tab(url)
        except Exception as error:
            return f"Couldn't open browser tab: {error}"

        if opened:
            return f"Opened a browser tab for {url}."

        return f"Tried to open {url}, but the browser rejected the request."

    def _read_window_title(self, window) -> str:

        for candidate in (
            getattr(window, "window_text", None),
            lambda: getattr(window.element_info, "name", ""),
        ):

            try:
                title = candidate()
            except Exception:
                continue

            if title:
                return title.strip()

        return ""