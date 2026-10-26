"""
Unit tests for the Brain: sentence streaming, Ollama client (against a fake local server), and conversation history.
"""

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Add src to python path for testing
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from sinmate.brain.llm_engine import Brain, LLMError, OllamaEngine, OllamaUnavailableError, iter_sentences
from sinmate.brain.personas import PersonaManager, PersonaRole

TRAIN_JSONL = Path(__file__).resolve().parent.parent / "data" / "train.jsonl"


def ndjson(chunks):
    """Ollama-style streaming body: one JSON object per chunk, then a final done=true object."""
    events = [{"message": {"role": "assistant", "content": c}, "done": False} for c in chunks]
    events.append({"message": {"role": "assistant", "content": ""}, "done": True})
    return [json.dumps(e, ensure_ascii=False) for e in events]


class FakeOllama:
    """Tiny in-process stand-in for the Ollama HTTP API."""

    def __init__(self):
        self.requests = []  # decoded JSON bodies sent to /api/chat
        self.chat_lines = ndjson(["ok"])
        self.chat_status = 200
        self.chat_error_body = None
        self.models = ["gemma3:1b-it-qat:latest"]
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body: bytes):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/api/tags":
                    self._send(200, json.dumps({"models": [{"name": m} for m in fake.models]}).encode())
                else:
                    self._send(404, b'{"error": "not found"}')

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                fake.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
                if fake.chat_status != 200:
                    self._send(fake.chat_status, json.dumps({"error": fake.chat_error_body}).encode())
                    return
                self._send(200, ("\n".join(fake.chat_lines) + "\n").encode("utf-8"))

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    @property
    def host(self):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class TestIterSentences(unittest.TestCase):
    def test_splits_on_terminators_across_chunks(self):
        chunks = ["හරි හරි.", " ආ ඇත්තද?", " ඉතින් කියන්නකෝ."]
        self.assertEqual(list(iter_sentences(chunks)), ["හරි හරි.", "ආ ඇත්තද?", "ඉතින් කියන්නකෝ."])

    def test_ellipsis_is_a_pause_not_a_boundary(self):
        self.assertEqual(list(iter_sentences(["හ්ම්ම්... ඇත්තද? හරි."])), ["හ්ම්ම්... ඇත්තද?", "හරි."])

    def test_decimal_point_is_not_a_boundary(self):
        self.assertEqual(list(iter_sentences(["වයස 3.5 යි. හරි"])), ["වයස 3.5 යි.", "හරි"])

    def test_short_fragments_merge_into_next_sentence(self):
        self.assertEqual(list(iter_sentences(["හරි. ආ ඇත්තද? හොඳයි."], min_chars=6)), ["හරි. ආ ඇත්තද?", "හොඳයි."])

    def test_newline_is_a_boundary(self):
        self.assertEqual(list(iter_sentences(["මේක ගොඩක් හොඳයි\nඊළඟ එක"])), ["මේක ගොඩක් හොඳයි", "ඊළඟ එක"])

    def test_empty_stream_yields_nothing(self):
        self.assertEqual(list(iter_sentences([])), [])
        self.assertEqual(list(iter_sentences(["  ", "\n"])), [])

    def test_closing_the_generator_closes_the_source(self):
        closed = []

        def source():
            try:
                yield "පළමු වාක්‍යය. දෙවන වාක්‍යය."
                yield " තුන්වන"
            finally:
                closed.append(True)

        sentences = iter_sentences(source())
        self.assertEqual(next(sentences), "පළමු වාක්‍යය.")
        sentences.close()
        self.assertEqual(closed, [True])


class TestOllamaEngine(unittest.TestCase):
    def setUp(self):
        self.fake = FakeOllama()
        self.addCleanup(self.fake.close)
        self.engine = OllamaEngine(model="sinmate-test", host=self.fake.host, timeout=5)

    def test_stream_chat_sends_expected_payload_and_yields_chunks(self):
        self.fake.chat_lines = ndjson(["හරි ", "මචං."])
        messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
        self.assertEqual(list(self.engine.stream_chat(messages)), ["හරි ", "මචං."])
        sent = self.fake.requests[0]
        self.assertEqual(sent["model"], "sinmate-test")
        self.assertTrue(sent["stream"])
        self.assertEqual(sent["messages"], messages)
        self.assertEqual(sent["options"]["num_predict"], 128)

    def test_chat_normalizes_to_nfc(self):
        decomposed = "කො"  # ක + ෙ + ා, canonically equal to the single code point ො
        self.fake.chat_lines = ndjson([decomposed])
        self.assertEqual(self.engine.chat([{"role": "user", "content": "x"}]), "කො")

    def test_stream_sentences_yields_normalized_sentences(self):
        self.fake.chat_lines = ndjson(["හරි හරි.", " ආ ඇත්තද?"])
        self.assertEqual(list(self.engine.stream_sentences([{"role": "user", "content": "x"}])), ["හරි හරි.", "ආ ඇත්තද?"])

    def test_list_models_and_availability(self):
        self.assertEqual(self.engine.list_models(), ["gemma3:1b-it-qat:latest"])
        self.assertTrue(self.engine.is_available())

    def test_unreachable_server_raises_unavailable(self):
        dead = FakeOllama()
        host = dead.host
        dead.close()
        engine = OllamaEngine(host=host, timeout=2)
        self.assertFalse(engine.is_available())
        with self.assertRaises(OllamaUnavailableError):
            engine.chat([{"role": "user", "content": "x"}])

    def test_missing_model_raises_with_server_message(self):
        self.fake.chat_status = 404
        self.fake.chat_error_body = "model 'sinmate-test' not found"
        with self.assertRaises(LLMError) as ctx:
            self.engine.chat([{"role": "user", "content": "x"}])
        self.assertIn("not found", str(ctx.exception))
        self.assertNotIsInstance(ctx.exception, OllamaUnavailableError)

    def test_error_event_mid_stream_raises(self):
        self.fake.chat_lines = [
            json.dumps({"message": {"role": "assistant", "content": "හරි"}, "done": False}),
            json.dumps({"error": "out of memory"}),
        ]
        with self.assertRaises(LLMError) as ctx:
            self.engine.chat([{"role": "user", "content": "x"}])
        self.assertIn("out of memory", str(ctx.exception))

    def test_host_without_scheme_is_accepted(self):
        engine = OllamaEngine(host="localhost:11434/")
        self.assertEqual(engine.host, "http://localhost:11434")


class TestBrain(unittest.TestCase):
    def setUp(self):
        self.fake = FakeOllama()
        self.addCleanup(self.fake.close)
        self.fake.chat_lines = ndjson(["හරි හරි.", " ආ ඇත්තද?", " ඉතින් කියන්නකෝ."])
        self.brain = Brain(OllamaEngine(host=self.fake.host, timeout=5))

    def test_respond_returns_full_reply_and_records_history(self):
        reply = self.brain.respond("අද මහන්සියි")
        self.assertEqual(reply, "හරි හරි. ආ ඇත්තද? ඉතින් කියන්නකෝ.")
        self.brain.respond("තව කියන්න")
        second_request = self.fake.requests[1]["messages"]
        self.assertEqual([m["role"] for m in second_request], ["system", "user", "assistant", "user"])
        self.assertEqual(second_request[1]["content"], "අද මහන්සියි")
        self.assertEqual(second_request[2]["content"], reply)

    def test_uses_compact_training_style_prompt_by_default(self):
        self.brain.respond("hi")
        system = self.fake.requests[0]["messages"][0]["content"]
        self.assertEqual(system, PersonaManager(PersonaRole.BEST_FRIEND).get_system_prompt(style="compact"))

    def test_set_persona_and_memory_context_reach_the_prompt(self):
        self.brain.set_persona(PersonaRole.MOTHER_FIGURE)
        self.brain.respond("hi", memory_context="User's name is Kasun.")
        system = self.fake.requests[0]["messages"][0]["content"]
        self.assertIn("[ROLE: MOTHER_FIGURE]", system)
        self.assertIn("User's name is Kasun.", system)
        self.brain.respond("hi again")  # memory context is per-turn, not sticky
        self.assertNotIn("Kasun", self.fake.requests[1]["messages"][0]["content"])

    def test_user_text_is_nfc_normalized(self):
        self.brain.respond("කො")
        self.assertEqual(self.fake.requests[0]["messages"][-1]["content"], "කො")

    def test_barge_in_keeps_only_spoken_sentences(self):
        stream = self.brain.respond_stream("අද මහන්සියි")
        self.assertEqual(next(stream), "හරි හරි.")
        stream.close()  # user interrupted after the first sentence
        self.brain.respond("මම කිව්වේ")
        history_in_next_request = self.fake.requests[1]["messages"]
        self.assertEqual(history_in_next_request[2], {"role": "assistant", "content": "හරි හරි."})

    def test_interrupted_before_any_sentence_leaves_history_untouched(self):
        stream = self.brain.respond_stream("hi")
        stream.close()
        self.assertEqual(self.brain.build_messages("x")[1:], [{"role": "user", "content": "x"}])

    def test_history_is_trimmed_and_starts_with_a_user_turn(self):
        brain = Brain(OllamaEngine(host=self.fake.host, timeout=5), max_history_messages=3)
        for _ in range(3):
            brain.respond("hi")
        roles = [m["role"] for m in brain.build_messages("next")[1:-1]]
        self.assertEqual(roles[0], "user")
        self.assertLessEqual(len(roles), 3)

    def test_empty_input_is_ignored(self):
        self.assertEqual(self.brain.respond("   "), "")
        self.assertEqual(self.fake.requests, [])

    def test_reset_history(self):
        self.brain.respond("hi")
        self.brain.reset_history()
        self.assertEqual(len(self.brain.build_messages("x")), 2)


class TestCompactPrompts(unittest.TestCase):
    def test_unknown_style_raises(self):
        with self.assertRaises(ValueError):
            PersonaManager().get_system_prompt(style="nope")

    def test_full_style_is_still_the_default(self):
        prompt = PersonaManager().get_system_prompt()
        self.assertIn("CRITICAL BEHAVIOR RULES", prompt)

    @unittest.skipUnless(TRAIN_JSONL.exists(), "data/train.jsonl not present")
    def test_compact_prompts_match_the_sft_training_data(self):
        """If the dataset is regenerated with different system prompts, the runtime prompt must be re-synced."""
        trained = set()
        with open(TRAIN_JSONL, encoding="utf-8") as f:
            for line in f:
                trained.add(json.loads(line)["messages"][0]["content"])
        for role in PersonaRole:
            prompt = PersonaManager(role).get_system_prompt(style="compact")
            self.assertIn(prompt, trained, f"compact prompt for {role.value} is not in data/train.jsonl")


if __name__ == "__main__":
    unittest.main()
