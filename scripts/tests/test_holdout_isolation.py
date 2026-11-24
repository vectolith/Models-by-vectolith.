#!/usr/bin/env python3
"""Split-isolation tests for the ASH PRIME protected holdout v2."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_ash_prime_holdout import (  # noqa: E402
    HOLDOUT_DIR,
    MANIFEST,
    HoldoutError,
    check_leaks,
    load_holdout,
)


def _copy_tree(destination: Path) -> None:
    shutil.copytree(ROOT / HOLDOUT_DIR, destination / HOLDOUT_DIR)


class HoldoutIsolationTests(unittest.TestCase):
    def test_repository_holdout_matches_manifest_and_has_no_leaks(self):
        manifest, records = load_holdout()
        self.assertEqual(manifest["record_count"], len(records))
        self.assertTrue(all(r["split"] == "holdout" for r in records))
        raw = (ROOT / manifest["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest["sha256"])
        check_leaks()

    def test_leaked_prompt_text_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_tree(root)
            _copy_manifest_only(root)
            _, records = load_holdout(root)
            (root / "docs").mkdir()
            (root / "docs" / "leak.md").write_text(
                "Example prompt: " + records[0]["prompt"] + "\n", encoding="utf-8"
            )
            with self.assertRaises(HoldoutError) as ctx:
                check_leaks(root)
            self.assertIn("docs/leak.md", str(ctx.exception))

    def test_leaked_record_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_tree(root)
            _copy_manifest_only(root)
            (root / "evaluation").mkdir()
            _manifest, records = load_holdout(root)
            leaked_id = records[3]["id"]
            (root / "evaluation" / "notes.md").write_text(f"holds {leaked_id} for later\n", encoding="utf-8")
            with self.assertRaises(HoldoutError) as ctx:
                check_leaks(root)
            self.assertIn(leaked_id, str(ctx.exception))

    def test_tampered_holdout_bytes_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_tree(root)
            _copy_manifest_only(root)
            manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
            target = root / manifest["path"]
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(HoldoutError) as ctx:
                load_holdout(root)
            self.assertIn("digest mismatch", str(ctx.exception))


def _copy_manifest_only(root: Path) -> None:
    manifest = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
    manifest["path"] = str(HOLDOUT_DIR / Path(manifest["path"]).name)
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
