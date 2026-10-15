import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np
from ai.streaming import SentenceBuffer
from ai.groq_client import GroqClient
from core.state import AssistantState
from speech.speaker import Speaker, PreparedSpeech
from core.assistant import EVAssistant
from speech.wake import WakeDetector
from speech.vad import VoiceActivityDetector
from speech.listener import MicrophoneListener
from config import settings


class PipelineTests(unittest.TestCase):
    def state(self):
        state = AssistantState()
        state.log_callback = lambda *args: None
        return state

    def client(self, events):
        client = GroqClient.__new__(GroqClient)
        client.state = self.state()
        client.conversation = []
        client.tool_registry = Mock()
        client.tool_registry.execute.return_value = "done"
        client.before_tool = Mock()
        client._events = Mock(side_effect=[iter_events(round_) for round_ in events])
        return client

    def test_sentence_stream_preserves_initials_and_decimal(self):
        buffer = SentenceBuffer()
        output = []
        for chunk in ["Hello E.", "V. Your value is 3.", "14. Next ", "sentence!", " Tail"]:
            output.extend(buffer.feed(chunk))
        output.extend(buffer.finish())
        self.assertEqual(output, ["Hello E.V. Your value is 3.14.", "Next sentence!", "Tail"])

    def test_first_sentence_arrives_before_stream_completes(self):
        client = self.client([[('First sentence. ', []), ('Second sentence.', [])]])
        response = client.ask_stream("hello")
        self.assertEqual(next(response), "First sentence.")
        self.assertEqual(len(client.conversation), 1)
        self.assertEqual(list(response), ["Second sentence."])
        self.assertEqual(client.conversation[-1]["content"], "First sentence. Second sentence.")

    def test_fragmented_tool_arguments_execute_once_then_reply(self):
        client = self.client([[
            ("", [{"index": 0, "id": "x", "function": {"name": "set_volume", "arguments": '{"lev'}}]),
            ("", [{"index": 0, "function": {"arguments": 'el": 20}'}}]),
        ], [("Volume adjusted.", [])]])
        self.assertEqual(list(client.ask_stream("volume 20")), ["Volume adjusted."])
        client.before_tool.assert_called_once()
        client.tool_registry.execute.assert_called_once_with("set_volume", {"level": 20})
        self.assertEqual(client.conversation[2]["tool_call_id"], "x")

    def test_malformed_tool_json_never_executes(self):
        client = self.client([[("", [{"index": 0, "function": {"name": "close_program", "arguments": "[bad"}}])],
                              [("Please repeat.", [])]])
        list(client.ask_stream("close"))
        client.tool_registry.execute.assert_not_called()
        self.assertIn("failed", client.conversation[2]["content"])

    def test_ollama_init_does_not_need_groq_key(self):
        with patch.object(settings, "LLM_BACKEND", "ollama"), patch.object(settings, "GROQ_API_KEY", None):
            client = GroqClient(self.state(), Mock())
        self.assertEqual(client.backend, "ollama")

    def test_worker_preserves_order_and_drains_before_tools(self):
        state = self.state()
        speaker = Speaker(state)
        heard = []
        ai = SimpleNamespace(before_tool=lambda: None)
        speaker._prepare = lambda sentence: PreparedSpeech(sentence)
        speaker._play_prepared = lambda prepared: heard.append(prepared.text)
        def sentences():
            yield "One."
            ai.before_tool()
            self.assertEqual(heard, ["One."])
            yield "Two."
        speaker.speak_stream(sentences(), ai=ai)
        self.assertEqual(heard, ["One.", "Two."])

    def test_playback_error_is_reported_without_worker_deadlock(self):
        speaker = Speaker(self.state())
        speaker._prepare = lambda sentence: PreparedSpeech(sentence)
        speaker._play_prepared = Mock(side_effect=RuntimeError("audio unavailable"))
        with self.assertRaisesRegex(RuntimeError, "audio unavailable"):
            speaker.speak_stream(iter(["Hello."] * 20))

    def test_cloud_fallback_is_opt_in(self):
        speaker = Speaker(self.state())
        speaker._prepare_local = Mock(side_effect=RuntimeError("missing model"))
        speaker._prepare_edge = Mock()
        with patch.object(settings, "TTS_BACKEND", "kokoro"), patch.object(settings, "TTS_ALLOW_EDGE_FALLBACK", False):
            with self.assertRaises(RuntimeError):
                speaker.speak("Private text")
        speaker._prepare_edge.assert_not_called()

    def test_sentence_pauses_are_in_audio_including_multi_sentence_greeting(self):
        speaker = Speaker(self.state())
        speaker.kokoro = Mock()
        speaker.kokoro.create.return_value = (np.ones(8, dtype=np.float32), 10)
        with patch.object(settings, 'SENTENCE_PAUSE_SECONDS', 0.7), patch.object(settings, 'KOKORO_SPEED', 0.9):
            audio = speaker._prepare_local("Hi, I'm here. What's on your mind?")
        self.assertEqual([call.args[0] for call in speaker.kokoro.create.call_args_list],
                         ["Hi, I'm here.", "What's on your mind?"])
        self.assertTrue(all(call.kwargs['speed'] == 0.9 for call in speaker.kokoro.create.call_args_list))
        expected = np.concatenate([np.ones(8), np.zeros(7), np.ones(8), np.zeros(7)])
        np.testing.assert_array_equal(audio.samples, expected)

    def test_speech_pauses_do_not_split_initials_or_decimals(self):
        speaker = Speaker(self.state())
        speaker.kokoro = Mock()
        speaker.kokoro.create.return_value = (np.ones(8, dtype=np.float32), 10)
        speaker._prepare_local("E.V. has version 3.14. It's ready.")
        self.assertEqual([call.args[0] for call in speaker.kokoro.create.call_args_list],
                         ["E.V. has version 3.14.", "It's ready."])

    def test_partial_stream_chunks_do_not_get_sentence_pauses(self):
        speaker = Speaker(self.state())
        speaker.kokoro = Mock()
        speaker.kokoro.create.return_value = (np.ones(8, dtype=np.float32), 10)
        audio = speaker._prepare_local("This sentence continues")
        np.testing.assert_array_equal(audio.samples, np.ones(8))

    def test_vad_windowing_context_and_reset(self):
        vad = VoiceActivityDetector.__new__(VoiceActivityDetector)
        vad.session = Mock()
        vad.session.run.return_value = (np.array([[0.9]], dtype=np.float32), np.ones((2, 1, 128), dtype=np.float32))
        vad.reset()
        self.assertFalse(vad.is_speech(np.ones(256)))
        self.assertTrue(vad.is_speech(np.ones(256)))
        inputs = vad.session.run.call_args.args[1]
        self.assertEqual(inputs["input"].shape, (1, 576))
        self.assertTrue(np.all(inputs["input"][:, :64] == 0))
        vad.reset()
        self.assertFalse(vad.state.any())
        self.assertEqual(vad.pending.size, 0)

    def test_wake_phrase_does_not_match_single_letters_or_prefixes(self):
        for text in ["e", "v", "even", "hey everyone"]:
            self.assertFalse(WakeDetector.matches(text))
        for text in ["E.V.", "hey ev", "okay e v open calculator"]:
            self.assertTrue(WakeDetector.matches(text))

    def test_openwakeword_buffers_80ms_frames(self):
        wake = WakeDetector.__new__(WakeDetector)
        wake.backend = "openwakeword"
        wake.model = Mock()
        wake.model.predict.return_value = {"hey_ev": 0.9}
        wake.reset()
        self.assertFalse(wake.detected(np.zeros(512, dtype=np.int16)))
        self.assertFalse(wake.detected(np.zeros(512, dtype=np.int16)))
        self.assertTrue(wake.detected(np.zeros(512, dtype=np.int16)))
        self.assertEqual(wake.model.predict.call_args.args[0].size, 1280)

    def record_fake(self, speech, wake=False, start_timeout=None):
        listener = MicrophoneListener.__new__(MicrophoneListener)
        listener.state = self.state()
        listener.vad = Mock()
        listener.vad.is_speech.side_effect = speech
        listener.wake = Mock()
        listener.wake.detected.return_value = True
        stream = Mock()
        stream.read.return_value = ((np.ones(512, dtype=np.int16) * 16384).tobytes(), False)
        ticks = iter(np.arange(0, 100, 0.032))
        with patch('speech.listener.sd.RawInputStream') as factory, \
                patch('speech.listener.time.monotonic', side_effect=lambda: next(ticks)), \
                patch.object(settings, 'SILENCE_DURATION', 0.06), \
                patch.object(settings, 'COMMAND_START_TIMEOUT', 0.1), \
                patch.object(settings, 'MAX_RECORD_SECONDS', 0.3):
            factory.return_value.__enter__.return_value = stream
            return listener._record(wait_for_wake=wake, start_timeout=start_timeout)

    def test_listener_normalizes_pcm_and_keeps_wake_pre_roll(self):
        audio = self.record_fake([True, False, False, False], wake=True)
        self.assertEqual(audio.dtype, np.float32)
        self.assertTrue(np.all(audio == 0.5))
        self.assertGreaterEqual(len(audio), 4 * 512)

    def test_listener_does_not_transcribe_silence(self):
        self.assertIsNone(self.record_fake([False] * 20))

    def test_listener_caps_continuous_speech(self):
        audio = self.record_fake([True] * 20)
        self.assertLessEqual(len(audio), 11 * 512)

    def test_next_sentence_is_synthesized_during_current_playback(self):
        speaker = Speaker(self.state())
        first_playing = threading.Event()
        second_prepared = threading.Event()
        heard = []
        def prepare(text):
            if text == "Two.":
                self.assertTrue(first_playing.wait(2), "Playback never started")
                second_prepared.set()
            return PreparedSpeech(text)
        def play(prepared):
            if prepared.text == "One.":
                first_playing.set()
                self.assertTrue(second_prepared.wait(2), "No synthesis during playback")
            heard.append(prepared.text)
        speaker._prepare = prepare
        speaker._play_prepared = play
        speaker.speak_stream(iter(["One.", "Two."]))
        self.assertEqual(heard, ["One.", "Two."])

    def test_synthesis_failure_is_reported_and_workers_exit(self):
        speaker = Speaker(self.state())
        speaker._prepare = Mock(side_effect=RuntimeError("synthesis failed"))
        with self.assertRaisesRegex(RuntimeError, "synthesis failed"):
            speaker.speak_stream(iter(["Hello."] * 20))

    def test_stopping_discards_queued_audio(self):
        speaker = Speaker(self.state())
        prepared = []
        discarded = []
        def prepare(text):
            prepared.append(text)
            return PreparedSpeech(text)
        def play(audio):
            speaker.state.stop()
        speaker._prepare = prepare
        speaker._play_prepared = play
        speaker._discard = lambda audio: discarded.append(audio.text)
        speaker.speak_stream(iter(["One.", "Two.", "Three."]))
        self.assertCountEqual(prepared, discarded)

    def test_delayed_followup_gets_a_full_command_budget(self):
        audio = self.record_fake([False] * 6 + [True] * 20, start_timeout=0.25)
        # Waiting for speech must not eat the maximum command duration.
        self.assertGreaterEqual(len(audio), 16 * 512)

    def test_conversation_followups_expire_back_to_wake_word(self):
        assistant = EVAssistant.__new__(EVAssistant)
        assistant.state = self.state()
        assistant.listener = Mock()
        assistant.transcriber = Mock()
        assistant.speaker = Mock()
        assistant.ai = Mock()
        audio = np.ones(512, dtype=np.float32)
        wake_calls = []
        def wake():
            wake_calls.append(True)
            if len(wake_calls) == 1:
                return audio
            assistant.state.stop()
            return None
        assistant.listener.record_until_wake_then_silence.side_effect = wake
        # The greeting invites a direct reply, then idle falls back to wake mode.
        assistant.listener.record_followup.side_effect = [None, audio, None]
        assistant.transcriber.transcribe.side_effect = ["hello", "tell me more"]
        with patch.object(settings, 'FOLLOW_UP_SECONDS', 8), patch.object(settings, 'REPLY_TAIL_SECONDS', 0):
            assistant.run()
        self.assertEqual(len(wake_calls), 2)
        self.assertEqual(assistant.listener.record_followup.call_count, 3)
        self.assertEqual(assistant.speaker.speak_stream.call_count, 2)

    def test_ollama_transport_parses_ndjson_and_tool_history(self):
        client = self.client([])
        client.backend = 'ollama'
        client.tool_registry.get_tools.return_value = []
        client.conversation = [
            {'role': 'assistant', 'content': '', 'tool_calls': [
                {'id': 'x', 'type': 'function', 'function': {'name': 'set_volume', 'arguments': '{"level":20}'}}]},
            {'role': 'tool', 'tool_call_id': 'x', 'tool_name': 'set_volume', 'content': 'done'}]
        response = Mock()
        response.iter_lines.return_value = [json.dumps({'message': {'content': 'Hello.'}, 'done': True}).encode()]
        with patch('requests.post') as post:
            post.return_value.__enter__.return_value = response
            result = list(GroqClient._events(client))
        self.assertEqual(result, [('Hello.', [])])
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['messages'][0]['tool_calls'][0]['function']['arguments'], {'level': 20})
        self.assertNotIn('tool_call_id', payload['messages'][1])


def iter_events(events):
    yield from events


if __name__ == "__main__":
    unittest.main()
