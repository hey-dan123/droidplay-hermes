import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from droidplay_adapter import (  # noqa: E402
    AdapterError,
    build_prompt,
    normalize_status,
    parse_adapter_result,
    run_hermes,
    validate_action,
)


class DroidPlayAdapterTests(unittest.TestCase):
    def test_normalize_status_keeps_unknown_on_missing_fields(self):
        result = normalize_status({})
        self.assertEqual(result["status"], "unknown")
        self.assertFalse(result["healthy"])
        self.assertEqual(result["errors"], ["adapter returned no status fields"])

    def test_normalize_status_accepts_ready_state(self):
        result = normalize_status({"status": "ready", "service": "running", "receiver": "Living Room"})
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["service"], "running")
        self.assertEqual(result["receiver"], "Living Room")
        self.assertTrue(result["healthy"])

    def test_normalize_status_preserves_adapter_error(self):
        result = normalize_status({"status": "error", "error": "device offline"})
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["healthy"])
        self.assertIn("device offline", result["errors"])

    def test_parse_adapter_result_rejects_malformed_json(self):
        with self.assertRaises(AdapterError):
            parse_adapter_result("not json")

    def test_parse_adapter_result_rejects_extra_output(self):
        with self.assertRaises(AdapterError):
            parse_adapter_result('{"status":"ready"}\n{"status":"error"}')

    def test_build_prompt_is_json_envelope(self):
        prompt = build_prompt({"status": "ready"}, "What should I watch next?")
        self.assertIn("DroidPlay strategy assistant", prompt)
        self.assertIn("What should I watch next?", prompt)
        self.assertIn('"status": "ready"', prompt)

    def test_build_prompt_preserves_shell_like_text(self):
        question = 'show $(whoami) `id` and "quotes"'
        prompt = build_prompt({"status": "ready"}, question)
        envelope = prompt.split("Input JSON:\n", 1)[1]
        payload = json.loads(envelope)
        self.assertEqual(payload["question"], question)

    def test_validate_action_rejects_unknown_action(self):
        with self.assertRaises(AdapterError):
            validate_action("launch_missiles")

    def test_validate_action_rejects_empty_media(self):
        with self.assertRaises(AdapterError):
            validate_action("play", media="")

    def test_run_hermes_uses_query_file_and_returns_stdout(self):
        prompt = build_prompt({"status": "ready"}, "hello")
        fake = "import sys; print(open(sys.argv[sys.argv.index('--query-file') + 1]).read())"
        with tempfile.TemporaryDirectory() as directory:
            result = run_hermes(
                prompt=prompt,
                cwd=directory,
                command_override=["python3", "-c", fake, "unused"],
            )
        self.assertIn("hello", result)


if __name__ == "__main__":
    unittest.main()
