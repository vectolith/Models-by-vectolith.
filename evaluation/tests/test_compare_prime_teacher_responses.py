from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from evaluation.compare_prime_teacher_responses import main, load_artifact, normalized_completion_status

class PrimeTeacherComparisonTests(unittest.TestCase):
    def _artifact(self, root, candidate, text):
        path=root/f"{candidate}.json"
        record={"candidate_id":candidate,"repo_id":f"org/{candidate}","immutable_revision":"a"*40,"run_id":candidate+"-run","case_count":2}
        rows=[
          {"case_id":"case-1","candidate_id":candidate,"model_revision":"a"*40,"run_id":candidate+"-run","prompt_sha256":"b"*64,"completion_status":"eos_completed","response_text":text},
          {"case_id":"case-2","candidate_id":candidate,"model_revision":"a"*40,"run_id":candidate+"-run","prompt_sha256":"c"*64,"completion_status":"token_cap_truncated","response_text":"partial"},
        ]
        path.write_text(json.dumps(record),encoding="utf-8")
        path.with_suffix(".jsonl").write_text("".join(json.dumps(x)+"\n" for x in rows),encoding="utf-8")
        return path
    def test_integrity_and_disagreement_report_never_ranks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); a=self._artifact(root,"teacher-a","alpha"); b=self._artifact(root,"teacher-b","beta")
            out=root/"report.json"
            import sys
            from unittest.mock import patch
            with patch.object(sys,"argv",["compare", "--artifact",str(a),"--artifact",str(b),"--output",str(out)]):
                self.assertEqual(main(),0)
            report=json.loads(out.read_text())
            self.assertEqual(len(report["pairwise_disagreement"]),1)
            self.assertEqual(report["pairwise_disagreement"][0]["common_case_count"],2)
            self.assertEqual(report["ranking"],"not_performed")
            self.assertFalse(report["responses_discarded"])
    def test_legacy_completion_statuses_are_normalized_without_rewriting_rows(self):
        self.assertEqual(normalized_completion_status({
            "generation_status":"token_limit_reached","generation_cap_reached":True,
            "response_text":"partial","error":None
        }),"token_cap_truncated")
        self.assertEqual(normalized_completion_status({
            "generation_status":"eos_or_early_stop","generation_cap_reached":False,
            "response_text":"complete answer","error":None
        }),"completed_without_token_cap")
        self.assertEqual(normalized_completion_status({
            "generation_status":"error","response_text":None,"error":"RuntimeError"
        }),"error")
    def test_revision_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); a=self._artifact(root,"teacher-a","alpha")
            rows=[json.loads(x) for x in a.with_suffix(".jsonl").read_text().splitlines()]
            rows[0]["model_revision"]="b"*40
            a.with_suffix(".jsonl").write_text("".join(json.dumps(x)+"\n" for x in rows))
            with self.assertRaisesRegex(ValueError,"revision provenance mismatch"):
                load_artifact(a)

if __name__=="__main__": unittest.main()
