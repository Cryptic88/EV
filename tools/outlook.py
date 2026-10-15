"""Classic Outlook mail/calendar automation with confirmed external actions."""
from datetime import datetime, timedelta, timezone
import json
import re
import uuid
from zoneinfo import ZoneInfo
from config import settings


class OutlookTools:
    def __init__(self, confirmation):
        self.confirmation = confirmation
        self.references = {}
        self.drafts = {}

    @staticmethod
    def _app():
        import win32com.client
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Office\16.0\Outlook\Profiles') as profiles:
                if winreg.QueryInfoKey(profiles)[0] == 0:
                    raise RuntimeError('No configured classic Outlook profile.')
            app = win32com.client.Dispatch('Outlook.Application')
            if app.Session.Accounts.Count == 0:
                raise RuntimeError('No configured classic Outlook account.')
            return app
        except Exception as error:
            raise RuntimeError('Classic Outlook needs a configured mail profile. '
                'Open Outlook (classic) and finish account setup manually. '
                'New Outlook does not expose this automation interface.') from error

    def _reference(self, item, kind):
        token = uuid.uuid4().hex[:10]
        self.references[token] = (kind, item.EntryID, item.Parent.StoreID)
        return token

    def _item(self, app, token, kind):
        ref = self.references.get(token)
        if not ref or ref[0] != kind:
            raise ValueError('Use an ID returned by the corresponding search/list tool.')
        return app.Session.GetItemFromID(ref[1], ref[2])

    @staticmethod
    def _emails(value):
        values = [s.strip() for s in re.split('[;,]', value) if s.strip()]
        if not values or any(not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', v) for v in values):
            raise ValueError('Provide explicit recipient email addresses separated by semicolons.')
        return '; '.join(values)

    @staticmethod
    def _mail_fingerprint(mail):
        recipients = tuple((str(mail.Recipients.Item(i).Address), int(mail.Recipients.Item(i).Type))
                           for i in range(1, mail.Recipients.Count + 1))
        return (str(mail.To), str(mail.CC), str(mail.BCC), str(mail.Subject), str(mail.Body),
                recipients, int(mail.Attachments.Count))

    def outlook(self, action, query='', item_id='', to='', subject='', body='', limit=5):
        app = self._app()
        if action == 'search':
            items = app.Session.GetDefaultFolder(6).Items  # Inbox.
            items.Sort('[ReceivedTime]', True)
            rows = []
            for index in range(1, min(items.Count, 200) + 1):
                mail = items.Item(index)
                if getattr(mail, 'Class', 0) != 43:
                    continue
                haystack = f'{mail.Subject} {mail.SenderName} {mail.SenderEmailAddress}'
                if query.casefold() not in haystack.casefold():
                    continue
                rows.append({'id': self._reference(mail, 'mail'), 'subject': str(mail.Subject),
                    'sender': str(mail.SenderName), 'received': str(mail.ReceivedTime),
                    'preview': str(mail.Body)[:400]})
                if len(rows) >= min(20, max(1, int(limit))):
                    break
            return json.dumps({'messages': rows, 'scope': 'Most recent 200 inbox items; subject/sender search.'})
        if action == 'read':
            mail = self._item(app, item_id, 'mail')
            return json.dumps({'subject': str(mail.Subject), 'from': str(mail.SenderName),
                               'body': str(mail.Body)[:16000]})
        if action in {'draft', 'reply'}:
            if not body.strip() or len(body) > 12000:
                raise ValueError('Provide an email body of 1 to 12,000 characters.')
            if action == 'reply':
                mail = self._item(app, item_id, 'mail').Reply()
                mail.Body = body + '\r\n\r\n' + mail.Body
            else:
                mail = app.CreateItem(0)
                mail.To = self._emails(to)
                mail.Subject = subject
                mail.Body = body
            if not mail.Recipients.ResolveAll():
                raise ValueError('Outlook could not resolve every recipient. Review addresses manually.')
            mail.Save()
            token = self._reference(mail, 'draft')
            self.drafts[token] = self._mail_fingerprint(mail)
            return json.dumps({'draft_id': token, 'to': str(mail.To), 'subject': str(mail.Subject),
                               'preview': body, 'status': 'Saved as draft; not sent.'})
        if action == 'send':
            mail = self._item(app, item_id, 'draft')
            if mail.Attachments.Count:
                raise ValueError('This draft has attachments; review and send it manually in Outlook.')
            expected = self.drafts.get(item_id)
            if not expected or self._mail_fingerprint(mail) != expected:
                raise ValueError('The draft changed; prepare and review a fresh draft before sending.')
            preview = f'Send email to {mail.To}, subject {mail.Subject}: {mail.Body}'
            if len(preview) > 5000:
                raise ValueError('This email is too long for spoken review; send it manually in Outlook.')
            if not self.confirmation.confirm(preview):
                return 'Cancelled. The email remains a draft.'
            mail = self._item(app, item_id, 'draft')
            if self._mail_fingerprint(mail) != expected:
                raise ValueError('The draft changed during confirmation; not sent.')
            mail.Send()
            del self.drafts[item_id]
            return 'Email submitted to Outlook for sending. Delivery is not confirmed.'
        raise ValueError('Outlook actions: search, read, draft, reply, send.')

    @staticmethod
    def _date(value):
        date = datetime.fromisoformat(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=ZoneInfo(settings.AUTOMATION_TIMEZONE))
        return date

    def calendar(self, action, item_id='', subject='', start='', end='', location='', body='', limit=10):
        app = self._app()
        if action == 'list':
            begin = self._date(start) if start else datetime.now(ZoneInfo(settings.AUTOMATION_TIMEZONE))
            finish = self._date(end) if end else begin + timedelta(days=7)
            if finish <= begin or finish - begin > timedelta(days=90):
                raise ValueError('Choose a calendar window of up to 90 days.')
            items = app.Session.GetDefaultFolder(9).Items
            items.Sort('[Start]')
            items.IncludeRecurrences = True
            local_begin = begin.astimezone(ZoneInfo(settings.AUTOMATION_TIMEZONE))
            local_finish = finish.astimezone(ZoneInfo(settings.AUTOMATION_TIMEZONE))
            filtered = items.Restrict("[Start] >= '" + local_begin.strftime('%m/%d/%Y %I:%M %p') +
                                      "' AND [Start] < '" + local_finish.strftime('%m/%d/%Y %I:%M %p') + "'")
            rows = []
            item = filtered.GetFirst()
            while item is not None and len(rows) < min(30, max(1, int(limit))):
                rows.append({'id': self._reference(item, 'event'), 'subject': str(item.Subject),
                    'start': str(item.Start), 'end': str(item.End), 'location': str(item.Location)})
                item = filtered.GetNext()
            return json.dumps({'timezone': settings.AUTOMATION_TIMEZONE, 'events': rows})
        if action in {'update', 'delete'}:
            item = self._item(app, item_id, 'event')
            if item.IsRecurring or item.MeetingStatus != 0:
                raise ValueError('Manage recurring events and attendee meetings manually in Outlook.')
        elif action == 'create':
            if not subject or not start or not end:
                raise ValueError('A calendar event requires subject, start and end.')
            item = app.CreateItem(1)
        else:
            raise ValueError('Calendar actions: list, create, update, delete.')
        if action == 'delete':
            if not self.confirmation.confirm(f'Delete calendar event {item.Subject}, starting {item.Start}?'):
                return 'Cancelled; calendar unchanged.'
            item.Delete()
            return 'Calendar event deleted.'
        if bool(start) != bool(end):
            raise ValueError('Provide both start and end when changing the event time.')
        begin, finish = (self._date(start), self._date(end)) if start else (None, None)
        if begin and finish <= begin:
            raise ValueError('Event end must be after its start.')
        summary = f'{action.title()} calendar event {subject or item.Subject}'
        if begin:
            summary += f', from {begin.isoformat()} to {finish.isoformat()}'
        summary += f', at {location or getattr(item, "Location", "")}.'
        if not self.confirmation.confirm(summary):
            return 'Cancelled; calendar unchanged.'
        if subject:
            item.Subject = subject
        if begin:
            item.StartUTC = begin.astimezone(timezone.utc).replace(tzinfo=None)
            item.EndUTC = finish.astimezone(timezone.utc).replace(tzinfo=None)
        if location:
            item.Location = location
        if body:
            item.Body = body
        item.Save()
        return f'Calendar event saved. Event ID: {self._reference(item, "event")}.'
