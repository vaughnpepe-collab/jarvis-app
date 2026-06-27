"""Unit tests for the J.A.R.V.I.S. backend.

These use only the standard library (``unittest``), so they run with:

    python -m unittest discover -s tests        # no extra deps
    python -m pytest tests                        # if pytest is installed

The network / subprocess boundary (OpenClaw) is always mocked — the tests never
spawn a real model call, so they are fast and deterministic.
"""

import io
import json
import os
import sys
import unittest
import urllib.error
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

        def fake_run(model, prompt, timeout=None):
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


class TestActiveBrain(unittest.TestCase):
    def test_anthropic_wins_when_key_present(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "sk-test"), \
                mock.patch.object(js, "OPENCLAW_AVAILABLE", True):
            self.assertEqual(js.active_brain(), "anthropic")
            self.assertEqual(js.active_model_label(), js.ANTHROPIC_MODEL)

    def test_openclaw_when_no_key(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", ""), \
                mock.patch.object(js, "OPENCLAW_AVAILABLE", True):
            self.assertEqual(js.active_brain(), "openclaw")
            self.assertEqual(js.active_model_label(), js.MODEL)

    def test_demo_when_nothing_configured(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", ""), \
                mock.patch.object(js, "OPENCLAW_AVAILABLE", False):
            self.assertEqual(js.active_brain(), "demo")
            self.assertIn("demo", js.active_model_label().lower())


class TestBuildMessages(unittest.TestCase):
    def setUp(self):
        self._saved = list(js._history)
        js._history.clear()

    def tearDown(self):
        js._history[:] = self._saved

    def test_roles_mapped_and_current_appended(self):
        js._history.append(("Sir", "first"))
        js._history.append(("JARVIS", "reply"))
        msgs = js._build_messages("now")
        self.assertEqual(msgs[0], {"role": "user", "content": "first"})
        self.assertEqual(msgs[1], {"role": "assistant", "content": "reply"})
        self.assertEqual(msgs[-1], {"role": "user", "content": "now"})


class TestAskAnthropic(unittest.TestCase):
    """The HTTP boundary (urllib.request.urlopen) is always mocked."""

    def setUp(self):
        self._saved = list(js._history)
        js._history.clear()

    def tearDown(self):
        js._history[:] = self._saved

    def _fake_response(self, payload):
        cm = mock.MagicMock()
        cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return cm

    def test_success_extracts_text(self):
        payload = {"content": [{"type": "text", "text": "At your service, Sir."}],
                   "stop_reason": "end_turn"}
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "sk-test"), \
                mock.patch("urllib.request.urlopen",
                           return_value=self._fake_response(payload)):
            ok, reply = js._ask_anthropic("hello")
        self.assertTrue(ok)
        self.assertEqual(reply, "At your service, Sir.")

    def test_refusal_is_declined(self):
        payload = {"content": [], "stop_reason": "refusal"}
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "sk-test"), \
                mock.patch("urllib.request.urlopen",
                           return_value=self._fake_response(payload)):
            ok, reply = js._ask_anthropic("hello")
        self.assertFalse(ok)
        self.assertIn("decline", reply.lower())

    def test_http_401_reports_credentials(self):
        err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b"{}"))
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "sk-bad"), \
                mock.patch("urllib.request.urlopen", side_effect=err):
            ok, reply = js._ask_anthropic("hello")
        self.assertFalse(ok)
        self.assertIn("ANTHROPIC_API_KEY", reply)

    def test_network_error_is_graceful(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "sk-test"), \
                mock.patch("urllib.request.urlopen",
                           side_effect=urllib.error.URLError("down")):
            ok, reply = js._ask_anthropic("hello")
        self.assertFalse(ok)
        self.assertIn("can't reach", reply.lower())


def _fake_resp(payload):
    cm = mock.MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return cm


class TestAskOpenAI(unittest.TestCase):
    def test_success(self):
        payload = {"choices": [{"message": {"content": "Quite so, Sir."}}]}
        with mock.patch.object(js, "OPENAI_API_KEY", "sk-test"), \
                mock.patch("urllib.request.urlopen", return_value=_fake_resp(payload)):
            ok, reply = js._ask_openai("hi")
        self.assertTrue(ok)
        self.assertEqual(reply, "Quite so, Sir.")

    def test_bad_key(self):
        err = urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b"{}"))
        with mock.patch.object(js, "OPENAI_API_KEY", "sk-bad"), \
                mock.patch("urllib.request.urlopen", side_effect=err):
            ok, reply = js._ask_openai("hi")
        self.assertFalse(ok)
        self.assertIn("rejected", reply.lower())

    def test_empty(self):
        with mock.patch.object(js, "OPENAI_API_KEY", "sk-test"), \
                mock.patch("urllib.request.urlopen", return_value=_fake_resp({"choices": []})):
            ok, reply = js._ask_openai("hi")
        self.assertFalse(ok)
        self.assertIn("empty reply", reply.lower())


class TestAskGemini(unittest.TestCase):
    def test_success(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "Indeed, Sir."}]}}]}
        with mock.patch.object(js, "GEMINI_API_KEY", "g-test"), \
                mock.patch("urllib.request.urlopen", return_value=_fake_resp(payload)):
            ok, reply = js._ask_gemini("hi")
        self.assertTrue(ok)
        self.assertEqual(reply, "Indeed, Sir.")

    def test_safety_is_declined(self):
        payload = {"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]}
        with mock.patch.object(js, "GEMINI_API_KEY", "g-test"), \
                mock.patch("urllib.request.urlopen", return_value=_fake_resp(payload)):
            ok, reply = js._ask_gemini("hi")
        self.assertFalse(ok)
        self.assertIn("decline", reply.lower())

    def test_network_error(self):
        with mock.patch.object(js, "GEMINI_API_KEY", "g-test"), \
                mock.patch("urllib.request.urlopen",
                           side_effect=urllib.error.URLError("down")):
            ok, reply = js._ask_gemini("hi")
        self.assertFalse(ok)
        self.assertIn("can't reach", reply.lower())


class TestBrainSelection(unittest.TestCase):
    def setUp(self):
        js._selected_brain = None

    def tearDown(self):
        js._selected_brain = None

    def test_available_brains_order_and_demo_last(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "a"), \
                mock.patch.object(js, "OPENAI_API_KEY", "o"), \
                mock.patch.object(js, "GEMINI_API_KEY", ""), \
                mock.patch.object(js, "OPENCLAW_AVAILABLE", False), \
                mock.patch.object(js, "DEFAULT_BRAIN", ""):
            self.assertEqual(js.available_brains(), ["anthropic", "openai", "demo"])

    def test_select_pins_active(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "a"), \
                mock.patch.object(js, "OPENAI_API_KEY", "o"), \
                mock.patch.object(js, "DEFAULT_BRAIN", ""):
            self.assertTrue(js.select_brain("openai"))
            self.assertEqual(js.active_brain(), "openai")  # not anthropic, despite order

    def test_select_unavailable_rejected(self):
        with mock.patch.object(js, "GEMINI_API_KEY", ""):
            self.assertFalse(js.select_brain("gemini"))

    def test_auto_resets_selection(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "a"), \
                mock.patch.object(js, "OPENAI_API_KEY", "o"), \
                mock.patch.object(js, "DEFAULT_BRAIN", ""):
            js.select_brain("openai")
            self.assertTrue(js.select_brain("auto"))
            self.assertEqual(js.active_brain(), "anthropic")  # back to order preference

    def test_default_brain_env_respected(self):
        with mock.patch.object(js, "ANTHROPIC_API_KEY", "a"), \
                mock.patch.object(js, "OPENAI_API_KEY", "o"), \
                mock.patch.object(js, "DEFAULT_BRAIN", "openai"):
            self.assertEqual(js.active_brain(), "openai")


class TestTestBrains(unittest.TestCase):
    def test_reports_per_brain_status(self):
        with mock.patch.object(js, "available_brains",
                               return_value=["anthropic", "openai", "demo"]), \
                mock.patch.object(js, "_ask_anthropic", return_value=(True, "online")), \
                mock.patch.object(js, "_ask_openai", return_value=(False, "key rejected")):
            out = js.test_brains()
        by_id = {r["id"]: r for r in out["results"]}
        self.assertTrue(by_id["anthropic"]["ok"])
        self.assertFalse(by_id["openai"]["ok"])
        self.assertIn("key rejected", by_id["openai"]["detail"])
        self.assertTrue(by_id["demo"]["ok"])          # demo always passes
        self.assertIn("active", out)

    def test_probe_exception_is_caught(self):
        with mock.patch.object(js, "available_brains", return_value=["gemini", "demo"]), \
                mock.patch.object(js, "_ask_gemini", side_effect=RuntimeError("boom")):
            out = js.test_brains()
        by_id = {r["id"]: r for r in out["results"]}
        self.assertFalse(by_id["gemini"]["ok"])
        self.assertIn("boom", by_id["gemini"]["detail"])

    def test_only_demo_when_nothing_configured(self):
        with mock.patch.object(js, "available_brains", return_value=["demo"]):
            out = js.test_brains()
        self.assertEqual([r["id"] for r in out["results"]], ["demo"])
        self.assertTrue(out["results"][0]["ok"])


class TestAskOpenclaw(unittest.TestCase):
    def test_ok(self):
        with mock.patch.object(js, "_attempt", return_value=("ok", "Certainly, Sir.")):
            ok, reply = js._ask_openclaw("do it")
        self.assertTrue(ok)
        self.assertEqual(reply, "Certainly, Sir.")

    def test_auth_triggers_refresh_then_retry(self):
        with mock.patch.object(js, "_attempt",
                               side_effect=[("auth", "b"), ("ok", "Recovered, Sir.")]), \
                mock.patch.object(js, "_refresh_token", return_value=True) as refresh:
            ok, reply = js._ask_openclaw("hi")
        self.assertTrue(ok)
        self.assertEqual(reply, "Recovered, Sir.")
        refresh.assert_called_once()

    def test_auth_refresh_fails(self):
        with mock.patch.object(js, "_attempt", return_value=("auth", "b")), \
                mock.patch.object(js, "_refresh_token", return_value=False):
            ok, reply = js._ask_openclaw("hi")
        self.assertFalse(ok)
        self.assertIn("authenticate", reply.lower())

    def test_failure_snippet(self):
        with mock.patch.object(js, "_attempt",
                               return_value=("fail", "line one\nfinal error line")):
            ok, reply = js._ask_openclaw("hi")
        self.assertFalse(ok)
        self.assertIn("final error line", reply)


class TestDemoReply(unittest.TestCase):
    def test_greeting(self):
        self.assertIn("demo mode", js._demo_reply("hello there").lower())

    def test_identity(self):
        self.assertIn("jarvis", js._demo_reply("who are you?").lower())

    def test_generic_mentions_api_key(self):
        self.assertIn("ANTHROPIC_API_KEY", js._demo_reply("what's the stock price"))


class TestAskClaudeDispatch(unittest.TestCase):
    def setUp(self):
        self._saved = list(js._history)
        js._history.clear()

    def tearDown(self):
        js._history[:] = self._saved

    def test_dispatches_to_openclaw_and_records_history(self):
        with mock.patch.object(js, "active_brain", return_value="openclaw"), \
                mock.patch.object(js, "_ask_openclaw",
                                  return_value=(True, "Certainly, Sir.")):
            res = js.ask_claude("Do the thing")
        self.assertTrue(res["ok"])
        self.assertEqual(res["brain"], "openclaw")
        self.assertEqual(js._history[-2], ("Sir", "Do the thing"))
        self.assertEqual(js._history[-1], ("JARVIS", "Certainly, Sir."))

    def test_failure_records_no_history(self):
        before = len(js._history)
        with mock.patch.object(js, "active_brain", return_value="openclaw"), \
                mock.patch.object(js, "_ask_openclaw", return_value=(False, "nope")):
            res = js.ask_claude("hello")
        self.assertFalse(res["ok"])
        self.assertEqual(len(js._history), before)

    def test_demo_brain_always_ok(self):
        with mock.patch.object(js, "active_brain", return_value="demo"):
            res = js.ask_claude("hello")
        self.assertTrue(res["ok"])
        self.assertEqual(res["brain"], "demo")


class TestGetStats(unittest.TestCase):
    def test_shape_and_ranges(self):
        s = js.get_stats()
        for key in ("cpu", "mem", "real", "model", "brain", "cores"):
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
