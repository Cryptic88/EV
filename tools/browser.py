"""Managed Edge browser with observed element references and bounded actions."""
import json
from pathlib import Path
import re
import time
from urllib.parse import urlparse
import uuid
from config import settings


class BrowserTools:
    def __init__(self, confirmation, headless=False, profile=None):
        self.confirmation = confirmation
        self.headless = headless
        self.profile = Path(profile or Path(settings.PROJECT_ROOT) / 'artifacts/browser-profile')
        self.driver = self.context = None
        self.pages, self.elements = {}, {}

    def start(self):
        if self.context is None:
            from playwright.sync_api import sync_playwright
            self.driver = sync_playwright().start()
            self.context = self.driver.chromium.launch_persistent_context(
                str(self.profile), channel='msedge', headless=self.headless,
                accept_downloads=False, viewport=None)

    @staticmethod
    def validate_url(url):
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Use an HTTP/HTTPS URL without embedded credentials.')

    def page(self, page_id):
        page = self.pages.get(page_id)
        if page is None or page.is_closed():
            raise ValueError('Unknown browser page. Open it or list tabs first.')
        self.validate_url(page.url)
        return page

    def track(self, page):
        for key, value in self.pages.items():
            if value is page:
                return key
        key = uuid.uuid4().hex[:8]
        self.pages[key] = page
        return key

    def inspect(self, page_id):
        page = self.page(page_id)
        # References are rebuilt every inspection; never click guessed selectors.
        self.elements = {k: v for k, v in self.elements.items() if v['page_id'] != page_id}
        rows = []
        controls = page.locator('a,button,input,textarea,select,[role="button"],[contenteditable="true"]')
        for index in range(min(controls.count(), 250)):
            node = controls.nth(index)
            if not node.is_visible():
                continue
            meta = node.evaluate("""el => ({tag:el.tagName.toLowerCase(),type:el.type||'',
                role:el.getAttribute('role')||'',label:el.getAttribute('aria-label')||el.labels?.[0]?.innerText||el.getAttribute('placeholder')||el.innerText||el.getAttribute('name')||'',
                password:el.type==='password',submit:el.type==='submit'&&!!el.form})""")
            if meta['password']:
                continue
            token = uuid.uuid4().hex[:10]
            node.evaluate('(el,id)=>el.setAttribute("data-ev-ref",id)', token)
            locator = page.locator('[data-ev-ref="' + token + '"]')
            self.elements[token] = dict(page_id=page_id, locator=locator, url=page.url,
                label=str(meta['label'])[:150], submit=meta['submit'], at=time.monotonic())
            rows.append(dict(id=token, tag=meta['tag'], role=meta['role'], label=str(meta['label'])[:150]))
            if len(rows) >= 70:
                break
        return json.dumps({'page_id': page_id, 'url': page.url, 'title': page.title(), 'elements': rows})

    def browser(self, action, page_id='', url='', element_id='', text=''):
        if action == 'open':
            self.validate_url(url)
            self.start()
            page = self.context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            return self.inspect(self.track(page))
        if action == 'tabs':
            self.start()
            return json.dumps([{'page_id': self.track(p), 'title': p.title(), 'url': p.url}
                               for p in self.context.pages if not p.is_closed()])
        page = self.page(page_id)
        if action == 'inspect':
            return self.inspect(page_id)
        if action == 'read':
            return page.locator('body').inner_text(timeout=5000)[:16000]
        if action == 'back':
            page.go_back(wait_until='domcontentloaded', timeout=30000)
            return self.inspect(page_id)
        if action == 'scroll':
            page.mouse.wheel(0, -600 if text == 'up' else 600)
            return self.inspect(page_id)
        if action == 'close':
            page.close()
            return 'Closed browser page.'
        entry = self.elements.get(element_id)
        if (not entry or entry['page_id'] != page_id or entry['url'] != page.url
                or time.monotonic() - entry['at'] > 120):
            raise ValueError('Element reference is stale; inspect the page again.')
        node = entry['locator']
        if node.count() != 1 or not node.is_visible() or not node.is_enabled():
            raise ValueError('That element changed or is unavailable; inspect again.')
        if action == 'fill':
            if node.get_attribute('type') == 'password':
                raise ValueError('Enter passwords manually in the browser.')
            node.fill(text, timeout=5000)
            return 'Field filled. The form has not been submitted.'
        if action in {'click', 'submit'}:
            risky = action == 'submit' or bool(re.search(
                r'\b(send|submit|post|publish|delete|remove|buy|purchase|pay|checkout|subscribe|confirm)\b',
                entry['label'], re.I)) or (entry['submit'] and not re.search(r'search|find', entry['label'], re.I))
            if risky and not self.confirmation.confirm('Activate ' + (entry['label'] or 'this form') + ' on ' + urlparse(page.url).netloc + '?'):
                return 'Cancelled; nothing was submitted.'
            # Confirmation can take time; verify the element still belongs to this page.
            if page.url != entry['url'] or node.count() != 1 or not node.is_visible():
                raise ValueError('The page changed during confirmation; inspect again.')
            node.click(timeout=5000)
            return self.inspect(page_id)
        raise ValueError('Unknown browser action.')

    def close(self):
        if self.context:
            self.context.close()
            self.context = None
        if self.driver:
            self.driver.stop()
            self.driver = None
