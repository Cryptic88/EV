"""App workflow composition and compact LLM tool schemas."""
from tools.automation_common import FileAccess, ActionConfirmation
from tools.workspace import WorkspaceTools
from tools.office import OfficeTools
from tools.browser import BrowserTools
from tools.whatsapp import WhatsAppTools
from tools.outlook import OutlookTools
from tools.spotify import SpotifyTools


def schema(name, description, properties, required):
    return {'type': 'function', 'function': {'name': name, 'description': description,
        'parameters': {'type': 'object', 'properties': properties, 'required': required,
                       'additionalProperties': False}}}


def string(description='', choices=None):
    result = {'type': 'string'}
    if description:
        result['description'] = description
    if choices:
        result['enum'] = choices
    return result


class AutomationTools:
    def __init__(self, state, listener, transcriber, speaker):
        self.files = FileAccess()
        self.confirmation = ActionConfirmation(state, listener, transcriber, speaker)
        self.workspace_tools = WorkspaceTools(self.files)
        self.office = OfficeTools(self.files)
        self.browser_tools = BrowserTools(self.confirmation)
        self.whatsapp_tools = WhatsAppTools(self.browser_tools, self.confirmation)
        self.outlook_tools = OutlookTools(self.confirmation)
        self.spotify_tools = SpotifyTools()
        self.functions = {'workspace': self.workspace_tools.workspace, 'word_document': self.office.word,
            'excel_workbook': self.office.excel, 'browser_control': self.browser_tools.browser,
            'whatsapp': self.whatsapp_tools.whatsapp, 'outlook_mail': self.outlook_tools.outlook,
            'outlook_calendar': self.outlook_tools.calendar, 'spotify': self.spotify_tools.spotify}

    def get_tools(self):
        return [
            schema('workspace', 'Read/edit files within allowed folders, open VS Code/Visual Studio projects, '
                   'and run builds/tests. Read before replace. Jobs return IDs; check job_status before claiming success.', {
                'action': string(choices=['list', 'read', 'create', 'replace', 'open', 'build', 'test', 'job_status']),
                'path': string('Absolute project/file path, or relative to the first allowed root.'),
                'text': string(), 'old_text': string('Exact text appearing once.'), 'new_text': string(),
                'editor': string(choices=['Visual Studio Code', 'Visual Studio']),
                'framework': string(choices=['auto', 'python', 'pytest', 'dotnet', 'npm']),
                'job_id': string(), 'line': {'type': 'integer', 'minimum': 1}}, ['action']),
            schema('word_document', 'Create, read, append to, or replace text in .docx files. Edits keep backups. '
                   'Ask the user to save/close an active Word document before file edits.', {
                'action': string(choices=['create', 'open', 'read', 'append', 'replace']), 'path': string(),
                'text': string(), 'old_text': string(), 'new_text': string(), 'title': string()}, ['action', 'path']),
            schema('excel_workbook', 'Create/read/edit .xlsx files, sheets, cells and formulas. Values are a 2D array. '
                   'Formulas recalculate when opened in Excel. Ask the user to save/close an active workbook before edits.', {
                'action': string(choices=['create', 'open', 'sheets', 'read', 'write', 'formula', 'add_sheet']),
                'path': string(), 'sheet': string(), 'cell': string('Top-left A1 coordinate.'),
                'values': {'type': 'array', 'items': {'type': 'array', 'items': {'type': ['string', 'number', 'boolean', 'null']}}},
                'formula': string(), 'rows': {'type': 'integer'}, 'columns': {'type': 'integer'}}, ['action', 'path']),
            schema('browser_control', 'Operate E.V.\'s dedicated Edge browser. Open/inspect first; use returned element IDs '
                   'for click/fill/submit. Never guess IDs. Password entry/login is manual. Submissions require spoken confirmation.', {
                'action': string(choices=['open', 'tabs', 'inspect', 'read', 'click', 'fill', 'submit', 'scroll', 'back', 'close']),
                'page_id': string(), 'url': string(), 'element_id': string(), 'text': string()}, ['action']),
            schema('whatsapp', 'Use WhatsApp Web in E.V.\'s browser. connect opens a page for manual phone linking. '
                   'find/draft require exact chat names. Draft does not send. Send only at user request; spoken confirmation is mandatory.', {
                'action': string(choices=['connect', 'find', 'draft', 'send']), 'contact': string(), 'text': string()}, ['action']),
            schema('outlook_mail', 'Classic Outlook: search recent inbox by subject/sender, read and summarize, '
                   'draft emails or replies, and send reviewed drafts only at user request with spoken confirmation. '
                   'Requires a configured classic Outlook profile, not new Outlook.', {
                'action': string(choices=['search', 'read', 'draft', 'reply', 'send']), 'query': string(),
                'item_id': string('Returned mail ID or draft ID.'), 'to': string('Explicit email addresses.'),
                'subject': string(), 'body': string(), 'limit': {'type': 'integer'}}, ['action']),
            schema('outlook_calendar', 'List/create/update/delete personal, non-recurring calendar events in classic Outlook. '
                   'All changes require spoken confirmation. Times are ISO 8601; use the configured user timezone when unspecified.', {
                'action': string(choices=['list', 'create', 'update', 'delete']), 'item_id': string(),
                'subject': string(), 'start': string(), 'end': string(), 'location': string(), 'body': string(),
                'limit': {'type': 'integer'}}, ['action']),
            schema('spotify', 'Control the Spotify Windows media session: play/resume, pause, next, previous, status. '
                   'Search opens native Spotify search results; it does not automatically select a song.', {
                'action': string(choices=['search', 'play', 'pause', 'next', 'previous', 'status']),
                'query': string()}, ['action']),
        ]
