"""WhatsApp Web drafts with exact chat matching and confirmed sending."""
import re


class WhatsAppTools:
    def __init__(self, browser, confirmation):
        self.browser, self.confirmation = browser, confirmation
        self.page_id = None
        self.pending = None

    def _page(self):
        self.browser.start()
        page = next((p for p in self.browser.context.pages
                     if not p.is_closed() and p.url.startswith('https://web.whatsapp.com/')), None)
        if page is None:
            page = self.browser.context.new_page()
            page.goto('https://web.whatsapp.com/', wait_until='domcontentloaded', timeout=30000)
        self.page_id = self.browser.track(page)
        return page

    @staticmethod
    def _one(locator, label):
        if locator.count() != 1 or not locator.is_visible():
            raise ValueError(label + ' was not uniquely visible. Inspect the WhatsApp page; do not guess.')
        return locator

    def _chat(self, page, contact):
        search = page.get_by_role('textbox', name=re.compile('search', re.I))
        if search.count() != 1:
            raise ValueError('Link WhatsApp Web manually in the E.V. browser, then try again. A unique chat search field is required.')
        search.fill(contact)
        match = page.locator('#pane-side').get_by_text(contact, exact=True)
        match.first.wait_for(state='visible', timeout=6000)
        self._one(match, 'Exact chat name').click()
        self._verify_chat(page, contact)

    def _verify_chat(self, page, contact):
        if not page.url.startswith('https://web.whatsapp.com/'):
            raise ValueError('WhatsApp page changed.')
        self._one(page.locator('#main header').get_by_text(contact, exact=True), 'Chat recipient')

    def whatsapp(self, action, contact='', text=''):
        page = self._page()
        if action == 'connect':
            return ('WhatsApp Web is open in E.V.\'s browser. Link it manually with your phone if asked. '
                    f'Browser page ID: {self.page_id}.')
        if action in {'find', 'draft'}:
            if not contact.strip():
                raise ValueError('Provide the exact contact or group name.')
            self._chat(page, contact)
            if action == 'find':
                return f'Opened the exact chat for {contact}.'
            if not text.strip() or len(text) > 4000:
                raise ValueError('Provide a message of 1 to 4,000 characters.')
            composer = self._one(page.locator('#main footer [contenteditable="true"][role="textbox"]'), 'Message composer')
            existing = composer.inner_text().strip()
            if existing and existing != text.strip():
                raise ValueError('This chat already has an unsent draft; review it before replacing it.')
            composer.fill(text)
            self.pending = {'contact': contact, 'text': text, 'page_id': self.page_id}
            return f'Drafted for {contact}: {text}. Not sent. Use send only when the user asks to send it.'
        if action == 'send':
            if not self.pending or self.pending['page_id'] != self.page_id:
                raise ValueError('Prepare a WhatsApp draft first.')
            draft = dict(self.pending)
            self._verify_chat(page, draft['contact'])
            composer = self._one(page.locator('#main footer [contenteditable="true"][role="textbox"]'), 'Message composer')
            if composer.inner_text().strip() != draft['text'].strip():
                raise ValueError('The draft changed. Review it again before sending.')
            if not self.confirmation.confirm(f"Send WhatsApp to {draft['contact']}: {draft['text']}?"):
                return 'Cancelled. The WhatsApp message remains an unsent draft.'
            self._verify_chat(page, draft['contact'])
            if composer.inner_text().strip() != draft['text'].strip():
                raise ValueError('The draft changed during confirmation; not sent.')
            send = self._one(page.locator('#main footer').get_by_role('button', name=re.compile(r'^send$', re.I)), 'Send button')
            send.click()
            self.pending = None
            return 'WhatsApp send requested. Delivery is not confirmed.'
        raise ValueError('WhatsApp actions: connect, find, draft, send.')
