import os
import sys
import tempfile
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_core_prime_blind_eval as blind
import unblind_core_prime_scores as unblind


def case(cid="x"):
    return {"id": cid, "prompt": "p", "context": "", "test": "t", "dimension": "judgment"}


def scores():
    return [
        {"case_id": "x", "blind_label": "candidate_1", "dimension": "judgment", "score": 4, "reviewer_id": "r1", "gate_flags": []},
        {"case_id": "x", "blind_label": "candidate_2", "dimension": "judgment", "score": 2, "reviewer_id": "r1", "gate_flags": []},
        {"case_id": "y", "blind_label": "candidate_1", "dimension": "judgment", "score": 3, "reviewer_id": "r1", "gate_flags": []},
        {"case_id": "y", "blind_label": "candidate_2", "dimension": "judgment", "score": 5, "reviewer_id": "r1", "gate_flags": []},
    ]


class BlindScoreContractTests(unittest.TestCase):
    def test_scores_require_blind_label_and_reviewer_and_validate_pairs(self):
        cases = [case(), case("y")]
        self.assertEqual(blind.validate_scores(scores(), cases), scores())
        for bad in (dict(scores()[0], blind_label="base"), dict(scores()[0], reviewer_id=""), dict(scores()[0], score=6)):
            with self.assertRaises(ValueError):
                blind.validate_scores([bad], cases)
        with self.assertRaises(ValueError):
            blind.validate_scores([scores()[0], scores()[0]], cases)

    def test_blind_summary_pools_scores_without_condition_names(self):
        result = blind.summarize(scores())
        self.assertEqual(result["dimension_means"]["judgment"], 3.5)
        self.assertEqual(result["dimension_counts"]["judgment"], 4)
        self.assertEqual(result["complete_reviewer_case_pairs"], 2)
        self.assertNotIn("base", result)
        self.assertNotIn("character_prompt", result)

    def test_mapping_requires_exact_cases_and_conditions(self):
        cases = [case(), case("y")]
        mapping = {"x": {"candidate_1": "character_prompt", "candidate_2": "base"}, "y": {"candidate_1": "base", "candidate_2": "character_prompt"}}
        self.assertEqual(unblind.validate_mapping(mapping, cases), mapping)
        with self.assertRaises(ValueError):
            unblind.validate_mapping({"x": mapping["x"]}, cases)
        with self.assertRaises(ValueError):
            unblind.validate_mapping({"x": {"candidate_1": "base", "candidate_2": "base"}, "y": mapping["y"]}, cases)

    def test_unblind_rejects_missing_score_field(self):
        row = scores()[0]
        row.pop("score")
        mapping = {"x": {"candidate_1": "base", "candidate_2": "character_prompt"}}
        with self.assertRaises(ValueError):
            unblind.build_summary([row], [case()], mapping)

    def test_unblind_aggregates_condition_means_and_paired_difference(self):
        cases = [case(), case("y")]
        mapping = {"x": {"candidate_1": "character_prompt", "candidate_2": "base"}, "y": {"candidate_1": "base", "candidate_2": "character_prompt"}}
        result = unblind.build_summary(scores(), cases, mapping)
        self.assertEqual(result["condition_dimension_means"]["character_prompt"]["judgment"], 4.5)
        self.assertEqual(result["condition_dimension_means"]["base"]["judgment"], 2.5)
        self.assertEqual(result["paired_difference_means_character_minus_base"]["judgment"], 2.0)
        self.assertEqual(result["paired_difference_counts"]["judgment"], 2)
        self.assertNotIn("case_id", result)
        self.assertNotIn("candidate_1", result)

    def test_unblinded_summary_requires_map_directory_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            restricted = Path(td) / "restricted"
            restricted.mkdir(mode=0o700)
            map_path = restricted / "blind-label-map.json"
            map_path.write_text("{}", encoding="utf-8")
            output = restricted / "unblinded-summary.json"
            summary = unblind.build_summary(scores(), [case(), case("y")], {"x": {"candidate_1": "character_prompt", "candidate_2": "base"}, "y": {"candidate_1": "base", "candidate_2": "character_prompt"}})
            unblind.write_restricted_summary(output, map_path, summary)
            self.assertEqual(output.read_text(encoding="utf-8"), json.dumps(summary, indent=2) + "\n")
            if os.name == "posix":
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                unblind.write_restricted_summary(output, map_path, summary)
            with self.assertRaises(ValueError):
                unblind.write_restricted_summary(Path(td) / "public-summary.json", map_path, summary)

    @unittest.skipUnless(os.name == "posix", "POSIX symlink semantics required")
    def test_map_symlink_or_loose_permissions_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            private = root / "private"
            private.mkdir(mode=0o700)
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = private / "map.json"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                unblind.load_restricted_mapping(link)
            link.unlink()
            map_path = private / "map.json"
            map_path.write_text("{}", encoding="utf-8")
            map_path.chmod(0o644)
            with self.assertRaises(PermissionError):
                unblind.load_restricted_mapping(map_path)


if __name__ == "__main__":
    unittest.main()
