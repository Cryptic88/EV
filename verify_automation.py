"""Verify real managed-browser form workflows against a local-only test page."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
from unittest.mock import Mock
from tools.browser import BrowserTools
from tools.spotify import SpotifyTools


def main():
    submissions = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            html = b'''<!doctype html><html><head><title>E.V. test</title></head><body>
            <form method="post"><input name="note" aria-label="Test note">
            <input type="password" aria-label="Private password">
            <button type="submit">Send test</button></form></body></html>'''
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html)
        def do_POST(self):
            submissions.append(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><head><title>Complete</title></head><body>Test received</body></html>')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    folder = Path(__file__).resolve().parent / 'artifacts'
    folder.mkdir(exist_ok=True)
    temporary = tempfile.TemporaryDirectory(dir=folder, ignore_cleanup_errors=True)
    assert Path(temporary.name).resolve().is_relative_to(folder.resolve())
    gate = Mock()
    browser = BrowserTools(gate, headless=True, profile=temporary.name)
    try:
        print('Checking real Edge browser controls on localhost ...', flush=True)
        state = json.loads(browser.browser('open', url=f'http://127.0.0.1:{server.server_port}/'))
        page_id = state['page_id']
        assert not any('password' in row['label'].lower() for row in state['elements'])
        field = next(row['id'] for row in state['elements'] if row['label'] == 'Test note')
        button = next(row['id'] for row in state['elements'] if row['label'] == 'Send test')
        browser.browser('fill', page_id=page_id, element_id=field, text='Local automation check')
        gate.confirm.return_value = False
        browser.browser('submit', page_id=page_id, element_id=button)
        assert not submissions, 'Cancelled form was submitted'
        gate.confirm.return_value = True
        browser.browser('submit', page_id=page_id, element_id=button)
        assert submissions == [b'note=Local+automation+check'], submissions
        print('PASS: browser inspection, field filling, cancellation and confirmed local submission.', flush=True)
    finally:
        browser.close()
        server.shutdown()
        server.server_close()
        temporary.cleanup()
    print('Checking Windows Spotify session access ...', flush=True)
    print(SpotifyTools().spotify('status'), flush=True)


if __name__ == '__main__':
    main()
