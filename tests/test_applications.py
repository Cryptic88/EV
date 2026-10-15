import unittest
from unittest.mock import Mock, patch
from tools.app_catalog import AppCatalog
from tools.applications import ApplicationTools
from ai.prompts import get_system_prompt


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = AppCatalog()
        self.tools = ApplicationTools.__new__(ApplicationTools)
        self.tools.app_catalog = self.catalog
        self.tools.state = Mock()
        self.tools.listener = Mock()
        self.tools.transcriber = Mock()
        self.tools.speaker = Mock()
        self.tools.transcriber.transcribe.return_value = "yes"

    def test_spoken_and_executable_aliases_resolve_to_the_right_app(self):
        cases = {'V.S. Code': 'Visual Studio Code', 'vs': 'Visual Studio',
                 'Code.exe': 'Visual Studio Code', 'Whats App': 'WhatsApp',
                 'WhatsApp.exe': 'WhatsApp', 'out look': 'Outlook',
                 'classic outlook': 'Outlook (classic)', 'outlook.exe': 'Outlook (classic)',
                 'arduino': 'Arduino IDE', 'ssms': 'SQL Server Management Studio'}
        for alias, expected in cases.items():
            with self.subTest(alias=alias):
                self.assertEqual(self.catalog.resolve(alias)['name'], expected)
        self.assertIsNone(self.catalog.resolve('my ide'))

    def test_store_app_opens_through_registered_windows_entry(self):
        with patch('tools.applications.os.startfile') as launch:
            result = self.tools.open_program('whats app')
        launch.assert_called_once_with('shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App')
        self.assertEqual(result, 'Opening WhatsApp.')

    def test_failed_launch_reports_failure(self):
        with patch('tools.applications.os.startfile', side_effect=FileNotFoundError):
            result = self.tools.open_program('nonexistent-app.exe')
        self.assertIn("Couldn't open", result)

    def processes(self, *names):
        return [Mock(info={'name': name, 'pid': index + 100}) for index, name in enumerate(names)]

    def test_close_vs_code_uses_executable_and_preserves_other_apps(self):
        processes = self.processes('Code.exe', 'Discord.exe', 'CodeHelper.exe', 'devenv.exe')
        with patch('tools.applications.psutil.process_iter', return_value=processes), \
                patch('tools.applications.CONFIRM_BEFORE_CLOSING', True):
            result = self.tools.close_program('vs code')
        processes[0].terminate.assert_called_once()
        for process in processes[1:]:
            process.terminate.assert_not_called()
        self.tools.speaker.speak.assert_called_once()
        self.assertIn('Code.exe', result)

    def test_declining_whatsapp_confirmation_keeps_it_running(self):
        processes = self.processes('WhatsApp.Root.exe')
        self.tools.transcriber.transcribe.return_value = 'no'
        with patch('tools.applications.psutil.process_iter', return_value=processes), \
                patch('tools.applications.CONFIRM_BEFORE_CLOSING', True):
            result = self.tools.close_program('whatsapp')
        processes[0].terminate.assert_not_called()
        self.assertIn('left it running', result)

    def test_new_and_classic_outlook_close_separately(self):
        for alias, expected_index in [('outlook', 0), ('classic outlook', 1)]:
            with self.subTest(alias=alias):
                processes = self.processes('olk.exe', 'OUTLOOK.EXE')
                with patch('tools.applications.psutil.process_iter', return_value=processes), \
                        patch('tools.applications.CONFIRM_BEFORE_CLOSING', True):
                    self.tools.close_program(alias)
                processes[expected_index].terminate.assert_called_once()
                processes[1 - expected_index].terminate.assert_not_called()

    def test_empty_app_name_does_not_launch_or_close_anything(self):
        with patch('tools.applications.psutil.process_iter') as processes, \
                patch('tools.applications.os.startfile') as launch:
            self.tools.close_program('  ')
            self.tools.open_program('  ')
        processes.assert_not_called()
        launch.assert_not_called()

    def test_assistant_knows_the_new_shortcuts(self):
        prompt = get_system_prompt()
        for name in ['WhatsApp', 'Outlook (classic)', 'Visual Studio Code', 'Android Studio']:
            self.assertIn(name, prompt)


if __name__ == '__main__':
    unittest.main()
