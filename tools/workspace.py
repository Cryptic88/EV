"""Bounded code/project operations with exact edits and build/test jobs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import uuid


class WorkspaceTools:
    def __init__(self, files):
        self.files = files
        self.jobs = {}

    def workspace(self, action, path='', text='', old_text='', new_text='',
                  editor='Visual Studio Code', framework='auto', job_id='', line=1):
        if action == 'job_status':
            job = self.jobs.get(job_id)
            if not job:
                raise ValueError('Unknown build/test job ID.')
            return json.dumps(job)
        target = self.files.path(path)
        if action == 'list':
            return '\n'.join(str(p) for p in list(target.iterdir())[:100]
                             if not p.name.startswith('.') and p.name != 'node_modules')
        if action == 'read':
            if target.stat().st_size > 1024 * 1024:
                raise ValueError('Choose a text file under 1 MB.')
            lines = target.read_text(encoding='utf-8-sig').splitlines()
            start = max(0, int(line) - 1)
            return '\n'.join(f'{i+1}: {s}' for i, s in enumerate(lines[start:start+200], start))[:16000]
        if action in {'create', 'replace'}:
            if len(text or new_text) > 200000:
                raise ValueError('The edit exceeds 200,000 characters.')
            if action == 'create':
                if target.exists():
                    raise ValueError('File already exists; use an exact replacement edit.')
                content = text
            else:
                content = target.read_text(encoding='utf-8')
                if not old_text or content.count(old_text) != 1:
                    raise ValueError('Old text must match exactly once. Read the file first.')
                content = content.replace(old_text, new_text, 1)
            return self.files.save(target, lambda tmp: tmp.write_text(content, encoding='utf-8'))
        if action == 'open':
            if not target.exists():
                raise ValueError('That file or project does not exist.')
            if editor.casefold() in {'vs code', 'vscode', 'visual studio code'}:
                exe = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Microsoft VS Code/Code.exe'
                if not exe.is_file():
                    exe = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Microsoft VS Code/Code.exe'
                if not exe.is_file():
                    raise ValueError('VS Code executable was not found.')
                subprocess.Popen([str(exe), '--reuse-window', str(target)], shell=False)
            elif editor.casefold() in {'visual studio', 'vs'}:
                if target.is_dir():
                    solutions = list(target.glob('*.sln')) + list(target.glob('*.slnx'))
                    if len(solutions) != 1:
                        raise ValueError('Specify one .sln or .slnx file for Visual Studio.')
                    target = solutions[0]
                vswhere = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
                if not vswhere.is_file():
                    raise ValueError('Visual Studio installation locator was not found.')
                executable = subprocess.check_output([str(vswhere), '-latest', '-products', '*',
                    '-property', 'productPath'], text=True, timeout=10).strip()
                if not executable or not Path(executable).is_file():
                    raise ValueError('Visual Studio executable was not found.')
                subprocess.Popen([executable, str(target)], shell=False)
            else:
                raise ValueError('Choose Visual Studio Code or Visual Studio.')
            return f'Opened {target} in {editor}.'
        if action in {'build', 'test'}:
            return self._start_job(target, action, framework)
        raise ValueError('Unknown workspace action.')

    def _start_job(self, folder, action, framework):
        if not folder.is_dir():
            raise ValueError('Choose the project folder.')
        if sum(j['status'] == 'running' for j in self.jobs.values()) >= 2:
            raise ValueError('Two jobs are already running; check their status first.')
        if framework == 'auto':
            if list(folder.glob('*.sln')) or list(folder.glob('*.csproj')) or list(folder.glob('*.slnx')):
                framework = 'dotnet'
            elif (folder / 'package.json').is_file():
                framework = 'npm'
            else:
                framework = 'python'
        if framework == 'dotnet':
            command = ['dotnet', action, '--nologo']
        elif framework == 'python':
            import sys
            python = folder / '.venv-local/Scripts/python.exe'
            if not python.exists():
                python = folder / '.venv/Scripts/python.exe'
            executable = str(python) if python.exists() else sys.executable
            if action == 'test':
                command = [executable, '-m', 'unittest', 'discover']
                if (folder / 'tests').is_dir():
                    command += ['-s', 'tests']
            else:
                command = [executable, '-m', 'compileall', '-q', '-x', r'(\.venv|\.runtime|node_modules|\.git)', '.']
        elif framework == 'pytest' and action == 'test':
            import sys
            python = folder / '.venv/Scripts/python.exe'
            command = [str(python) if python.exists() else sys.executable, '-m', 'pytest', '-q']
        elif framework == 'npm':
            package = json.loads((folder / 'package.json').read_text(encoding='utf-8'))
            if action not in package.get('scripts', {}):
                raise ValueError(f'package.json has no {action} script.')
            npm = shutil.which('npm.cmd')
            if not npm:
                raise ValueError('npm is not installed.')
            command = [os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', npm, 'run', action]
        else:
            raise ValueError('Choose auto, python, pytest, dotnet, or npm.')
        job_id = uuid.uuid4().hex[:12]
        log = Path(__file__).resolve().parents[1] / 'artifacts/jobs' / (job_id + '.log')
        log.parent.mkdir(parents=True, exist_ok=True)
        job = {'id': job_id, 'status': 'running', 'project': str(folder), 'action': action, 'log': str(log)}
        self.jobs[job_id] = job
        def run():
            try:
                with log.open('w', encoding='utf-8') as output:
                    process = subprocess.Popen(command, cwd=folder, stdout=output,
                        stderr=subprocess.STDOUT, shell=False,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    try:
                        job['exit_code'] = process.wait(timeout=180)
                        job['status'] = 'passed' if job['exit_code'] == 0 else 'failed'
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        job['status'] = 'timed_out'
                job['output'] = log.read_text(encoding='utf-8', errors='replace')[-12000:]
            except Exception as error:
                job.update(status='failed', error=str(error))
        threading.Thread(target=run, name='ev-project-job', daemon=True).start()
        return f'Started {action} job {job_id}. Use job_status with this ID to get the result.'
