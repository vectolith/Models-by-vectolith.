"""Tests for the runtime command-line entry point."""
import io
import json
import unittest
from contextlib import redirect_stdout

from vectolith_runtime.cli import main, selfcheck


class SelfcheckTests(unittest.TestCase):
    def test_selfcheck_passes_on_this_repository(self):
        report = selfcheck()
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual(report["problems"], [])
        self.assertGreater(report["fixture_records"], 0)
        self.assertEqual(report["ash_prime_capabilities"], 24)

    def test_every_check_has_a_reason(self):
        report = selfcheck()
        for check in report["checks"]:
            self.assertTrue(check["detail"].strip(), check["name"])
            self.assertIsInstance(check["ok"], bool)

    def test_schema_check_covers_both_copies(self):
        names = {check["name"] for check in selfcheck()["checks"] if check["name"].startswith("schema.")}
        self.assertIn("schema.infrastructure-contribution-v1.schema.json", names)
        self.assertIn("schema.infrastructure-provider-v1.schema.json", names)


class CommandTests(unittest.TestCase):
    def run_cli(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(argv)
        return code, out.getvalue()

    def test_selfcheck_command_exits_zero_and_prints_json(self):
        code, out = self.run_cli(["selfcheck"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])

    def test_preflight_command_requires_arguments(self):
        with self.assertRaises(SystemExit):
            main(["preflight"])

    def test_unknown_command_is_rejected(self):
        with self.assertRaises(SystemExit):
            main(["nonsense"])


if __name__ == "__main__":
    unittest.main()
