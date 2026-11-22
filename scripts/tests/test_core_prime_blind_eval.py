import sys
import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_core_prime_blind_eval as ev


def case():
    return {"id": "x", "prompt": "p", "context": "", "test": "t", "dimension": "judgment"}


def scored_row(cid="x", label="candidate_1", score=3, reviewer="r1", dimension="judgment", flags=None):
    return {"case_id": cid, "blind_label": label, "dimension": dimension, "score": score, "reviewer_id": reviewer, "gate_flags": flags or []}


class EvalHarnessTests(unittest.TestCase):
    def test_summary_and_validation(self):
        rows = [scored_row("x", "candidate_1", 4), scored_row("y", "candidate_2", 2, flags=["capability_regression"]), scored_row("z", "candidate_1", None, dimension="repair")]
        result = ev.summarize(rows)
        self.assertEqual(result["dimension_means"]["judgment"], 3.0)
        self.assertEqual(result["dimension_counts"]["repair"], 0)
        self.assertEqual(result["gate_flags"], ["capability_regression"])
        with self.assertRaises(ValueError): ev.summarize([scored_row(score=6)])
        with self.assertRaises(ValueError): ev.summarize([scored_row(flags=["badflag"])])
        with self.assertRaises(ValueError): ev.summarize([{"dimension": "judgment", "score": 2}])
        with self.assertRaises(ValueError): ev.summarize([scored_row(), scored_row()])

    def test_blinding_mapping_is_separate_and_deterministic(self):
        outputs = {"x": {"base": "response A", "character_prompt": "response B"}}
        a, mapping = ev.make_sheet([case()], outputs, 7)
        b, mapping_b = ev.make_sheet([case()], outputs, 7)
        self.assertEqual(a, b)
        self.assertEqual(mapping, mapping_b)
        self.assertNotIn("mapping", a[0])
        self.assertEqual(set(mapping["x"].values()), {"base", "character_prompt"})
        self.assertEqual({r["blind_label"] for r in a[0]["responses"]}, {"candidate_1", "candidate_2"})

    def test_case_and_output_validation(self):
        with self.assertRaises(ValueError): ev.validate_cases([case(), case()])
        with self.assertRaises(ValueError): ev.make_sheet([case()], {}, 1)
        with self.assertRaises(ValueError): ev.make_sheet([case()], {"x": {"base": "A", "other": "B"}}, 1)
        with self.assertRaises(ValueError): ev.make_sheet([case()], {"x": {"base": "A", "character_prompt": ""}}, 1)
        with self.assertRaises(ValueError): ev.make_sheet([case()], {"x": {"base": "A", "character_prompt": "B"}, "extra": {}}, 1)

    def test_jsonl_writer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.jsonl"
            path.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError): ev.write_jsonl(path, [{"x": 2}])
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")

    def test_jsonl_writer_real_newlines(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.jsonl"
            ev.write_jsonl(path, [{"x": 1}, {"x": 2}])
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)

    def test_mapping_writer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            map_dir = Path(td) / "restricted"
            map_dir.mkdir()
            map_file = map_dir / "blind-label-map.json"
            map_file.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError): ev.write_restricted_mapping(map_dir, {"x": {"candidate_1": "base"}})
            self.assertEqual(map_file.read_text(encoding="utf-8"), "preserve")

    @unittest.skipUnless(os.name == "posix", "POSIX file modes required")
    def test_mapping_writer_rejects_symlink_and_preserves_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            map_dir = root / "restricted"
            map_dir.mkdir(mode=0o700)
            target = root / "target.json"
            target.write_text("preserve", encoding="utf-8")
            link = map_dir / "blind-label-map.json"
            link.symlink_to(target)
            with self.assertRaises(FileExistsError):
                ev.write_restricted_mapping(map_dir, {"x": {"candidate_1": "base"}})
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve")
            self.assertTrue(link.is_symlink())

    @unittest.skipUnless(os.name == "posix", "POSIX file modes required")
    def test_mapping_writer_creates_file_restrictively(self):
        with tempfile.TemporaryDirectory() as td:
            map_dir = Path(td) / "restricted"
            previous_umask = os.umask(0)
            try:
                ev.write_restricted_mapping(map_dir, {"x": {"candidate_1": "base"}})
            finally:
                os.umask(previous_umask)
            map_file = map_dir / "blind-label-map.json"
            self.assertEqual(map_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual(map_file.stat().st_mode & 0o777, 0o600)

    def test_default_shuffle_uses_system_random(self):
        class ReverseShuffle:
            def shuffle(self, values):
                values.reverse()
        outputs = {"x": {"base": "A", "character_prompt": "B"}}
        with patch.object(ev.random, "SystemRandom", return_value=ReverseShuffle()):
            _, mapping = ev.make_sheet([case()], outputs)
        self.assertEqual(mapping["x"], {"candidate_1": "character_prompt", "candidate_2": "base"})
    def test_cli_rejects_fixed_seed_option(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "sheet"
            args = ["run_core_prime_blind_eval.py", "--output", str(output), "--seed", "20261121"]
            with patch.object(sys, "argv", args):
                with self.assertRaises(SystemExit):
                    ev.main()
            self.assertFalse(output.exists())


    @unittest.skipUnless(os.name == "posix", "POSIX exclusive temp creation required")
    def test_mapping_writer_does_not_delete_colliding_temp_file(self):
        with tempfile.TemporaryDirectory() as td:
            map_dir = Path(td) / "restricted"
            map_dir.mkdir(mode=0o700)
            collision = map_dir / ".blind-label-map.json.tmp-collision"
            collision.write_text("preserve", encoding="utf-8")
            with patch.object(ev.secrets, "token_hex", return_value="collision"):
                with self.assertRaises(FileExistsError):
                    ev.write_restricted_mapping(map_dir, {"x": {"candidate_1": "base"}})
            self.assertEqual(collision.read_text(encoding="utf-8"), "preserve")
            self.assertFalse((map_dir / "blind-label-map.json").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX no-follow path traversal required")
    def test_mapping_writer_rejects_intermediate_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.mkdir(mode=0o700)
            link = root / "parent-link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(OSError):
                ev.write_restricted_mapping(link / "restricted", {"x": {"candidate_1": "base"}})
            self.assertFalse((target / "restricted" / "blind-label-map.json").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX atomic write semantics required")
    def test_mapping_writer_rolls_back_publication_after_directory_fsync_failure(self):
        with tempfile.TemporaryDirectory() as td:
            map_dir = Path(td) / "restricted"
            real_fsync = os.fsync
            calls = 0
            def fail_second_fsync(fd):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated directory fsync failure")
                return real_fsync(fd)
            with patch.object(ev.os, "fsync", side_effect=fail_second_fsync):
                with self.assertRaises(OSError):
                    ev.write_restricted_mapping(map_dir, {"x": {"candidate_1": "base"}})
            self.assertFalse((map_dir / "blind-label-map.json").exists())
            self.assertEqual(list(map_dir.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "POSIX atomic write semantics required")
    def test_mapping_writer_cleans_temp_file_after_fsync_failure(self):
        with tempfile.TemporaryDirectory() as td:
            map_dir = Path(td) / "restricted"
            with patch.object(ev.os, "fsync", side_effect=OSError("simulated fsync failure")):
                with self.assertRaises(OSError):
                    ev.write_restricted_mapping(map_dir, {"x": {"candidate_1": "base"}})
            self.assertFalse((map_dir / "blind-label-map.json").exists())
            self.assertEqual(list(map_dir.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "POSIX symlink semantics required")
    def test_mapping_directory_symlink_is_rejected_before_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.mkdir()
            link = root / "restricted-link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                ev.validate_output_directories(root / "sheet", link)
            with self.assertRaises(ValueError):
                ev.write_restricted_mapping(link, {"x": {"candidate_1": "base"}})
            self.assertFalse((target / "blind-label-map.json").exists())

    def test_directories_must_be_disjoint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError): ev.validate_output_directories(root / "sheet", root / "sheet" / "nested")
            with self.assertRaises(ValueError): ev.validate_output_directories(root / "sheet" / "nested", root / "sheet")
            self.assertEqual(ev.validate_output_directories(root / "sheet", root / "map")[0], (root / "sheet").resolve())

    def test_score_ids_labels_dimensions_and_reviewers_are_bound_to_cases(self):
        rows = [scored_row()]
        self.assertEqual(ev.validate_scores(rows, [case()]), rows)
        with self.assertRaises(ValueError): ev.validate_scores([scored_row("unknown")], [case()])
        with self.assertRaises(ValueError): ev.validate_scores([scored_row(dimension="repair")], [case()])
        with self.assertRaises(ValueError): ev.validate_scores([scored_row(label="base")], [case()])
        with self.assertRaises(ValueError): ev.validate_scores([scored_row(reviewer="")], [case()])
        with self.assertRaises(ValueError): ev.validate_scores([rows[0], rows[0]], [case()])
        missing_score = dict(rows[0])
        missing_score.pop("score")
        with self.assertRaises(ValueError): ev.validate_scores([missing_score], [case()])

    def test_cli_refuses_to_overwrite_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases_path = root / "cases.jsonl"
            scores_path = root / "scores.jsonl"
            output = root / "summary-output"
            cases_path.write_text(json.dumps(case()) + "\n", encoding="utf-8")
            scores_path.write_text(json.dumps(scored_row(score=4)) + "\n", encoding="utf-8")
            args = ["run_core_prime_blind_eval.py", "--cases", str(cases_path), "--scores", str(scores_path), "--output", str(output)]
            with patch.object(sys, "argv", args):
                ev.main()
            summary = output / "summary.json"
            original = summary.read_text(encoding="utf-8")
            with patch.object(sys, "argv", args):
                with self.assertRaises(SystemExit):
                    ev.main()
            self.assertEqual(summary.read_text(encoding="utf-8"), original)

    def test_cli_keeps_mapping_out_of_evaluator_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases_path = root / "cases.jsonl"
            outputs_path = root / "outputs.json"
            sheet_dir = root / "score-sheets"
            map_dir = root / "restricted"
            cases_path.write_text(json.dumps(case()) + "\n", encoding="utf-8")
            outputs_path.write_text(json.dumps({"x": {"base": "A", "character_prompt": "B"}}), encoding="utf-8")
            with patch.object(sys, "argv", ["run_core_prime_blind_eval.py", "--cases", str(cases_path), "--outputs", str(outputs_path), "--output", str(sheet_dir), "--map-output", str(map_dir)]):
                ev.main()
            self.assertTrue((sheet_dir / "blind-score-sheet.jsonl").exists())
            self.assertTrue((map_dir / "blind-label-map.json").exists())
            self.assertFalse((sheet_dir / "blind-label-map.json").exists())
            if os.name == "posix":
                self.assertEqual(map_dir.stat().st_mode & 0o777, 0o700)
                self.assertEqual((map_dir / "blind-label-map.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
