"""Repo hygiene gates, so CI enforces them through test discovery (no workflow edits needed)."""
import subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

import repo_audit


class RepoHygieneTest(unittest.TestCase):
    def test_no_broken_relative_markdown_links(self):
        problems = repo_audit.broken_relative_links()
        self.assertEqual(problems, [], 'broken relative links: ' + ', '.join(problems))

    def test_no_tracked_build_artifacts(self):
        self.assertEqual(repo_audit.tracked_artifacts(), [])

    def test_markdown_files_are_discoverable(self):
        self.assertGreater(len(repo_audit.markdown_files()), 10)

    def test_cli_selfcheck_passes(self):
        proc = subprocess.run(
            [sys.executable, '-m', 'vectolith_runtime.cli', 'selfcheck'],
            cwd=str(ROOT / 'runtime'), capture_output=True, text=True, timeout=120
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main()
