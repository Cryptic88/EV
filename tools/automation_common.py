"""Shared file scope, reversible writes, and spoken action confirmation."""
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
from config import settings


class FileAccess:
    def __init__(self, roots=None):
        self.roots = [Path(p).expanduser().resolve() for p in
                      (roots or settings.AUTOMATION_ROOTS)]

    def path(self, value, suffixes=None):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.roots[0] / path
        path = path.resolve()
        if not any(path.is_relative_to(root) for root in self.roots):
            raise ValueError("Choose a file inside an allowed Documents/project folder.")
        blocked = {'.git', '.ssh', '.aws', '.codex', '.venv', '.venv-local',
                   '.runtime', '.ev-backups', 'node_modules', '__pycache__'}
        if any(part.casefold() in blocked for part in path.parts):
            raise ValueError("That internal folder is excluded from app automation.")
        if path.name.casefold().startswith('.env') or path.suffix.casefold() in {'.pem', '.key', '.pfx'}:
            raise ValueError("Credential files are excluded from app automation.")
        if suffixes and path.suffix.casefold() not in suffixes:
            raise ValueError("Supported file types: " + ', '.join(sorted(suffixes)))
        return path

    def backup(self, path):
        if path.exists():
            if path.stat().st_size > 25 * 1024 * 1024:
                raise ValueError("This file exceeds the 25 MB edit limit.")
            folder = path.parent / '.ev-backups'
            folder.mkdir(exist_ok=True)
            target = folder / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8] + '-' + path.name)
            shutil.copy2(path, target)
            return target

    def save(self, path, writer):
        path.parent.mkdir(parents=True, exist_ok=True)
        backup = self.backup(path)
        fd, name = tempfile.mkstemp(suffix=path.suffix, dir=path.parent)
        os.close(fd)
        try:
            writer(Path(name))
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)
        return f"Saved {path}." + (f" Backup: {backup}." if backup else '')


class ActionConfirmation:
    def __init__(self, state, listener, transcriber, speaker):
        self.state, self.listener = state, listener
        self.transcriber, self.speaker = transcriber, speaker

    def confirm(self, summary):
        if self.state.is_stopped():
            return False
        self.speaker.speak(summary + ' Say confirm to proceed, or cancel.')
        heard = self.transcriber.transcribe(self.listener.record_until_silence()) or ''
        answer = re.sub(r'[^a-z ]', ' ', heard.casefold())
        answer = ' '.join(answer.split())
        return not self.state.is_stopped() and answer in {
            'confirm', 'yes', 'yes confirm', 'yes please', 'confirm it', 'go ahead'}
