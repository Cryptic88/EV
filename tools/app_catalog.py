"""Voice aliases and Windows launch targets for this laptop's installed apps."""
import json
from pathlib import Path
import re
from config.settings import PROJECT_ROOT


def normalize_app_name(name):
    # Speech recognition varies spacing, punctuation, and capitalization.
    return " ".join(re.sub(r"[^\w\s]", " ", name.casefold()).split())


class AppCatalog:
    def __init__(self, path=None):
        path = Path(path) if path is not None else Path(PROJECT_ROOT) / "config" / "app_shortcuts.json"
        self.apps = json.loads(path.read_text(encoding="utf-8"))["applications"]
        self.aliases = {}
        for app in self.apps:
            if not app["name"] or not app["target"] or not app["process_names"]:
                raise ValueError("App shortcuts require a name, launch target and process names")
            for alias in [app["name"], *app.get("aliases", []), *app["process_names"]]:
                key = normalize_app_name(alias)
                if key in self.aliases and self.aliases[key] is not app:
                    raise ValueError(f"Duplicate app alias: {alias}")
                self.aliases[key] = app

    def resolve(self, name):
        return self.aliases.get(normalize_app_name(name))

    def names(self):
        return [app["name"] for app in self.apps]
