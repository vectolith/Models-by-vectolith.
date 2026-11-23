"""Guards for the sequential additive-teacher qualification workflow."""

import unittest
from pathlib import Path

import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "expanded-qualification-inference.yml"
)


class ExpandedQualificationWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")
        self.jobs = yaml.safe_load(self.text)["jobs"]

    def test_chain_is_a_strict_sequence_of_six_teachers(self):
        self.assertEqual(
            list(self.jobs),
            ["granite31", "granite42", "minicpm5", "smollm3", "lfm25", "phi4mini"],
        )
        self.assertIsNone(self.jobs["granite31"].get("needs"))
        for previous, current in zip(list(self.jobs), list(self.jobs)[1:]):
            self.assertEqual(self.jobs[current]["needs"], previous)

    def test_every_job_requires_explicit_authorization(self):
        for name, job in self.jobs.items():
            self.assertIn("inputs.run_qualification == true", job["if"], name)

    def test_smollm3_runs_on_explicit_tag_only_licence_evidence(self):
        job = self.jobs["smollm3"]
        steps = " ".join(str(step.get("run", "")) for step in job["steps"])
        self.assertIn("--accept-model-card-tag-evidence", steps)
        self.assertIn("--candidate-id smollm3-3b", steps)
        self.assertIn("smollm3-3b-license-caveat.txt", self.text)

    def test_smollm3_gate_is_scoped_to_its_own_candidate(self):
        from evaluation import snapshot_additional_teacher as snapshot

        self.assertIn("smollm3-3b", snapshot.TAG_ONLY_LICENSE_EVIDENCE_CANDIDATES)
        self.assertEqual(
            snapshot.TAG_ONLY_LICENSE_EVIDENCE_CANDIDATES, frozenset({"smollm3-3b"})
        )


if __name__ == "__main__":
    unittest.main()
