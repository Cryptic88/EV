# E.V. app workflows

E.V. has eight additional tool groups for coding, Word, Excel, browser interaction, WhatsApp, Outlook mail/calendar, and Spotify. App-launch shortcuts remain available. Heart, the AMD microphone, and the existing speech pacing are preserved.

## Files and IDEs

You authorized editing inside `C:/Users/rynop/Documents`. `AUTOMATION_ROOTS` in `.env` sets allowed roots; separate multiple Windows paths with semicolons. Paths outside those roots, credential files, Git metadata, virtual environments and internal backup folders are excluded. Edits make timestamped copies in a sibling `.ev-backups` folder before atomically replacing the file. Save active IDE/Office changes before asking E.V. to edit files on disk.

Examples:

- “Open my project at C:\Users\rynop\Documents\EV in VS Code.”
- “Read main.py in my EV project.”
- “Replace this exact text in that file with …”
- “Create a Python file called hello.py in my project with …”
- “Run the tests in my EV project.”
- “Check the status of that test job.”

VS Code opens project folders or files. Visual Studio uses its installed executable and accepts a named solution/project file. Folder opening requires one `.sln` or `.slnx`. Builds/tests support Python/unittest, pytest, .NET and npm scripts. Jobs run in the requested project with a three-minute limit and return a job ID. E.V. must check the result before claiming success. npm uses the project's existing build/test scripts. Package installation, arbitrary terminal commands, repository deletion and commits are not included.

## Word and Excel

- “Create a Word document called meeting-notes.docx in Documents, titled Meeting notes, with …”
- “Append these notes to meeting-notes.docx.”
- “Open meeting-notes.docx in Word.”
- “Replace this exact phrase in my Word document with …”
- “Create budget.xlsx with Item and Cost columns.”
- “Write 100, 200 and 300 into B2 through B4.”
- “Put =SUM(B2:B4) into B5.”
- “Read the first ten rows of that workbook.”
- “Open that workbook in Excel.”

Word supports `.docx` creation, opening, text reading, appending paragraphs and exact text replacement across ordinary text runs, including table paragraphs. Complex fields, tracked changes, text boxes, embedded objects and arbitrary layout editing are not covered. Excel supports `.xlsx`, opening, worksheet listing/creation, cell grids and formulas, with up to 2,000 cells per write. Formulas are stored; Excel recalculates them when opened. These workflows edit saved files, not unsaved live app buffers.

## Browser interaction

- “Open https://example.com in E.V.'s browser.”
- “Read that page.”
- “Find the search field and enter …”
- “Click the button labelled …”
- “Submit that form.”

Browser controls use a dedicated Microsoft Edge profile stored under `artifacts/browser-profile`. Existing Firefox/browser-launch shortcuts remain available. E.V. first inspects the page, then uses returned element references to click or fill fields. References expire and are rebuilt after inspection. Submission and recognized send/purchase/delete actions require spoken confirmation. Password entry and signing in are manual. No file uploads are exposed. Website text is untrusted content and cannot authorize actions.

## WhatsApp

Say **“Connect WhatsApp Web”**. A browser window opens at WhatsApp Web. Link it yourself with your phone; E.V. does not handle the QR/login step. The existing desktop WhatsApp shortcut still opens the desktop app, while messaging workflows use the linked web session.

You can also launch `.\.venv-local\Scripts\python.exe main.py --connect-whatsapp` to show the linking page at startup.

- “Find the chat named [exact contact or group name].”
- “Draft a WhatsApp to [exact name] saying …”
- “Send that WhatsApp.”

E.V. requires an exact, unique chat match and verifies the chat header and message draft before sending. Drafting does not send. Sending reads back the recipient and message and requires “confirm” or another accepted affirmative. Changing the chat/draft during confirmation cancels the send. An existing different unsent draft is preserved. Sending reports a send request, not confirmed delivery. WhatsApp interface changes may require selector updates; unavailable/ambiguous fields produce an error rather than guessed clicks.

## Outlook email and calendar

These tools use **classic Outlook**, which must have a configured mail profile. This laptop currently has no classic profile. Open **Outlook (classic)** and complete account setup manually before using these features. New Outlook does not provide the COM automation interface used here; its app shortcut still works.

- “Find emails from [name] in my inbox.”
- “Read that email and summarize it.”
- “Draft an email to name@example.com, subject …, saying …”
- “Draft a reply to that email saying …”
- “Send that email.”
- “What is on my calendar tomorrow?”
- “Create a calendar event tomorrow from 9 to 10 called Planning.”
- “Move that event to Friday at 10.”
- “Delete that calendar event.”

Search checks subject/sender in the most recent 200 inbox items and returns up to 20 matches. Read returns bounded body text so the LLM can summarize it. Drafts are saved in Outlook. Sending requires a reviewed draft ID, unchanged recipients/content and spoken confirmation. Attachments require manual review/sending. Calendar tools handle personal non-recurring appointments; recurring events and attendee meetings require Outlook. All calendar changes require confirmation. Dates default to `Africa/Johannesburg`; calendar listing spans at most 90 days.

## Spotify

- “Search Spotify for [artist/song].”
- “Resume Spotify.”
- “Pause Spotify.”
- “Next track.”
- “Previous track.”
- “What is playing on Spotify?”

Search opens Spotify's native search results. Select a track in Spotify to establish its Windows media session. Play/resume, pause, next/previous and status target only that Spotify session. Search does not automatically select/play a named result. Spotify must be installed, signed in and expose a unique media session; no Spotify web API credentials or Premium API integration are configured.

## Confirmation and verification

For a confirmation prompt, say **“confirm”**, **“yes”**, **“yes please”** or **“go ahead”**. Other phrases and silence cancel. Confirmations are obtained from the microphone, not from model arguments or page/email content. No real messages or calendar writes are used during automated tests.

```powershell
.\.venv-local\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv-local\Scripts\python.exe -B verify_automation.py
```

The second check uses headless Edge and a local-only test form to verify inspection, filling, cancellation and submission. It then checks Windows Spotify-session access without changing playback. Account-dependent WhatsApp/Outlook behavior is covered by simulated cancellation/change/send tests but still needs a live check after your manual account setup.
