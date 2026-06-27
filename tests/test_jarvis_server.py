"""Unit tests for the J.A.R.V.I.S. backend.

These use only the standard library (``unittest``), so they run with:

    python -m unittest discover -s tests        # no extra deps
    python -m pytest tests                        # if pytest is installed

The network / subprocess boundary (OpenClaw) is always mocked — the tests never
spawn a real model call, so they are fast and deterministic.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# Make the project root importable regardless of where the tests are run from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import jarvis_server as js  # noqa: E402


class TestStripPreamble(unittest.TestCase):
    def test_drops_metadata_lines(self):
        raw = ("provider: anthropic\nmodel: claude-opus-4-8\noutputs: 1\n"
               "Good evening, Sir.")
        self.assertEqual(js._strip_preamble(raw), "Good evening, Sir.")

    def test_keeps_body_without_preamble(self):
        self.assertEqual(js._strip_preamble("Hello, Sir."), "Hello, Sir.")

    def test_all_preamble_falls_back_to_original(self):
        # If stripping leaves nothing, return the original rather than "".
        raw = "provider: anthropic\nmodel: x\n"
        self.assertEqual(js._strip_preamble(raw), raw)


class TestExtractText(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(js._extract_text(""), "")
        self.assertEqual(js._extract_text(None), "")

    def test_plain_text_with_preamble(self):
        self.assertEqual(
            js._extract_text("model: x\nAt your service, Sir."),
            "At your service, Sir.")

    def test_json_outputs_string(self):
        self.assertEqual(
            js._extract_text(json.dumps({"outputs": "Indeed, Sir."})),
            "Indeed, Sir.")

    def test_json_content_blocks(self):
        blob = json.dumps({"content": [{"text": "Part one. "}, {"text": "Part two."}]})
        self.assertEqual(js._extract_text(blob), "Part one. Part two.")

    def test_json_embedded_in_preamble(self):
        raw = 'transport: local\n{"reply": "Embedded reply, Sir."}'
        self.assertEqual(js._extract_text(raw), "Embedded reply, Sir.")

    def test_json_fallback_longest_string(self):
        blob = json.dumps({"meta": {"a": "x", "deep": "the actual long answer here"}})
        self.assertEqual(js._extract_text(blob), "the actual long answer here")


class TestBuildPrompt(unittest.TestCase):
    def setUp(self):
        # Isolate global history for each test.
        self._saved = list(js._history)
        js._history.clear()

    def tearDown(self):
        js._history[:] = self._saved

    def test_includes_persona_and_user(self):
        p = js._build_prompt("What's the time?")
        self.assertIn(js.JARVIS_PERSONA, p)
        self.assertIn("Sir: What's the time?", p)
        self.assertTrue(p.rstrip().endswith("JARVIS:"))

    def test_includes_recent_history(self):
        js._history.append(("Sir", "Hello"))
        js._history.append(("JARVIS", "Good day, Sir."))
        p = js._build_prompt("And now?")
        self.assertIn("Conversation so far:", p)
        self.assertIn("JARVIS: Good day, Sir.", p)

    def test_history_window_capped(self):
        for i in range(40):
            js._history.append(("Sir", f"msg {i}"))
        p = js._build_prompt("latest")
        self.assertNotIn("msg 0", p)      # oldest dropped
        self.assertIn("msg 39", p)        # newest kept


class TestAttempt(unittest.TestCase):
    def test_first_model_ok_short_circuits(self):
        calls = []

        def fake_run(model, prompt):
            calls.append(model)
            return ("Hello, Sir.", "blob", None)

        with mock.patch.object(js, "MODELS", ["m1", "m2"]), \
                mock.patch.object(js, "_run_model", side_effect=fake_run):
            kind, payload = js._attempt("prompt")
        self.assertEqual(kind, "ok")
        self.assertEqual(payload, "Hello, Sir.")
        self.assertEqual(calls, ["m1"])  # second model not tried

    def test_fatal_returns_immediately(self):
        with mock.patch.object(js, "MODELS", ["m1", "m2"]), \
                mock.patch.object(js, "_run_model",
                                  return_value=("", "", "fatal message")):
            kind, payload = js._attempt("prompt")
        self.assertEqual(kind, "fatal")
        self.assertEqual(payload, "fatal message")

    def test_auth_detected_across_models(self):
        with mock.patch.object(js, "MODELS", ["m1", "m2"]), \
                mock.patch.object(js, "_run_model",
                                  return_value=("", "authentication_error 401", None)):
            kind, payload = js._attempt("prompt")
        self.assertEqual(kind, "auth")

    def test_plain_failure(self):
        with mock.patch.object(js, "MODELS", ["m1"]), \
                mock.patch.object(js, "_run_model",
                                  return_value=("", "some other noise", None)):
            kind, _ = js._attempt("prompt")
        self.assertEqual(kind, "fail")


class TestAskClaude(unittest.TestCase):
    def setUp(self):
        self._saved = list(js._history)
        js._history.clear()

    def tearDown(self):
        js._history[:] = self._saved

    def test_ok_records_history(self):
        with mock.patch.object(js, "_attempt", return_value=("ok", "Certainly, Sir.")):
            res = js.ask_claude("Do the thing")
        self.assertTrue(res["ok"])
        self.assertEqual(res["reply"], "Certainly, Sir.")
        self.assertEqual(js._history[-2], ("Sir", "Do the thing"))
        self.assertEqual(js._history[-1], ("JARVIS", "Certainly, Sir."))

    def test_auth_triggers_refresh_then_retry_success(self):
        attempts = [("auth", "blob"), ("ok", "Recovered, Sir.")]

        with mock.patch.object(js, "_attempt", side_effect=attempts), \
                mock.patch.object(js, "_refresh_token", return_value=True) as refresh:
            res = js.ask_claude("hello")
        self.assertTrue(res["ok"])
        self.assertEqual(res["reply"], "Recovered, Sir.")
        refresh.assert_called_once()

    def test_auth_refresh_fails_returns_auth_message(self):
        with mock.patch.object(js, "_attempt", return_value=("auth", "blob")), \
                mock.patch.object(js, "_refresh_token", return_value=False):
            res = js.ask_claude("hello")
        self.assertFalse(res["ok"])
        self.assertIn("authenticate", res["reply"].lower())

    def test_failure_returns_last_line_snippet(self):
        with mock.patch.object(js, "_attempt",
                               return_value=("fail", "line one\nfinal error line")):
            res = js.ask_claude("hello")
        self.assertFalse(res["ok"])
        self.assertIn("final error line", res["reply"])

    def test_failure_no_history_recorded(self):
        before = len(js._history)
        with mock.patch.object(js, "_attempt", return_value=("fail", "nope")):
            js.ask_claude("hello")
        self.assertEqual(len(js._history), before)


class TestGetStats(unittest.TestCase):
    def test_shape_and_ranges(self):
        s = js.get_stats()
        for key in ("cpu", "mem", "real", "model", "cores"):
            self.assertIn(key, s)
        self.assertGreaterEqual(s["cpu"], 0)
        self.assertLessEqual(s["cpu"], 100)
        self.assertGreaterEqual(s["mem"], 0)
        self.assertLessEqual(s["mem"], 100)
        self.assertIsInstance(s["real"], bool)


class TestLoggingSetup(unittest.TestCase):
    def test_idempotent(self):
        js.setup_logging()
        n = len(js.log.handlers)
        js.setup_logging()  # second call must not duplicate handlers
        self.assertEqual(len(js.log.handlers), n)


class TestChromeBinaryLookup(unittest.TestCase):
    def test_returns_none_or_existing_path(self):
        # Whatever this environment has, the result must be None or a real file.
        result = js._chrome_app_binary()
        if result is not None:
            self.assertTrue(os.path.exists(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
