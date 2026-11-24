from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from evaluation.prime_candidate_policy_gate import candidate_is_authorized
from evaluation.teacher_qualification_gates import (
    DEFAULT_WAIVER_PATH,
    load_waivers,
    evaluate_candidate,
    evaluate_cohort,
)
from evaluation.tests.test_teacher_qualification_gates import valid_manifest

HUMAN_GATES = (
    "license_review",
    "grading",
    "safety_review",
    "holdout",
    "corpus_integrity",
    "training_output_permission",
)


def manifest_without_human_gates(candidate_id="candidate-a"):
    manifest = valid_manifest(candidate_id)
    for name in HUMAN_GATES:
        manifest["gates"].pop(name)
    manifest["gates"]["grading"] = {"status": "not_reviewed"}
    return manifest


class OwnerWaiverTests(unittest.TestCase):
    def test_repository_waiver_file_is_valid(self):
        waivers = load_waivers()
        self.assertEqual(sorted(waivers), sorted(HUMAN_GATES))
        for name, entry in waivers.items():
            self.assertEqual(entry["status"], "waived_by_owner")
            self.assertTrue(entry["owner_id"])
            self.assertTrue(entry["reason"])

    def test_strict_evaluation_still_fails_closed(self):
        result = evaluate_candidate(manifest_without_human_gates())
        self.assertEqual(result["qualification_status"], "not_qualified")
        self.assertEqual(result["waived_gates"], [])
        self.assertEqual(result["review_basis"], "independent_review")
        self.assertTrue(any(f.startswith("grading:") for f in result["failed_gates"]))

    def test_waivers_clear_human_gates_and_are_reported_as_waived(self):
        result = evaluate_candidate(manifest_without_human_gates(), load_waivers())
        self.assertEqual(result["qualification_status"], "qualified")
        self.assertEqual(result["failed_gates"], [])
        self.assertEqual(sorted(result["waived_gates"]), sorted(HUMAN_GATES))
        self.assertEqual(result["review_basis"], "owner_waiver")
        self.assertFalse(result["training_started"])

    def test_waivers_never_clear_mechanical_gates(self):
        cases = {
            "snapshot": lambda m: m["gates"]["snapshot"].update(status="pending"),
            "loader_compatibility": lambda m: m["gates"]["loader_compatibility"].update(tested_revision="c" * 40),
            "real_inference": lambda m: m["gates"]["real_inference"].update(response_count=179),
            "resource_measurement": lambda m: m["gates"]["resource_measurement"].update(free_compute_verified=False),
        }
        for gate, breaker in cases.items():
            with self.subTest(gate=gate):
                manifest = manifest_without_human_gates()
                breaker(manifest)
                result = evaluate_candidate(manifest, load_waivers())
                self.assertEqual(result["qualification_status"], "not_qualified")
                self.assertTrue(any(f.startswith(f"{gate}:") for f in result["failed_gates"]))

    def test_waiver_file_rejects_non_waivable_gate(self):
        payload = json.loads(Path(DEFAULT_WAIVER_PATH).read_text(encoding="utf-8"))
        payload = copy.deepcopy(payload)
        payload["waived_gates"].append({"gate": "snapshot", "status": "waived_by_owner", "reason": "nope"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "waivers.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_waivers(path)

    def test_cohort_qualifies_four_teachers_under_waiver(self):
        manifests = [manifest_without_human_gates(f"candidate-{index}") for index in range(4)]
        strict = evaluate_cohort(manifests, 4)
        self.assertEqual(strict["cohort_gate"], "blocked")
        waived = evaluate_cohort(manifests, 4, load_waivers())
        self.assertEqual(waived["cohort_gate"], "passed")
        self.assertEqual(waived["qualified_teacher_count"], 4)

    def test_policy_gate_requires_valid_revision_even_when_waived(self):
        candidate = {
            "candidate_id": "qwen3.5-2b",
            "revision": "not-a-revision",
            "license_review": "pending_human_legal_review",
            "local_inference_authorized": False,
        }
        self.assertFalse(candidate_is_authorized(candidate, load_waivers()))

    def test_policy_gate_waives_review_but_not_revision_binding(self):
        candidate = {
            "candidate_id": "qwen3.5-2b",
            "revision": "1" * 40,
            "license_review": "pending_human_legal_review",
            "local_inference_authorized": False,
        }
        self.assertFalse(candidate_is_authorized(candidate))
        self.assertTrue(candidate_is_authorized(candidate, load_waivers()))


if __name__ == "__main__":
    unittest.main()
