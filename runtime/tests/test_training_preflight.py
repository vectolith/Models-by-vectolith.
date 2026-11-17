from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from vectolith_runtime.training_preflight import (
    validate_foundation_selection, validate_teacher_manifest, validate_training_preflight,
)

SHA="a"*64
REV="b"*40

def teacher_manifest(name):
    return {
        "schema_version":"vectolith-teacher-qualification-candidate/1.0",
        "candidate_id":name,"immutable_revision":REV,
        "gates":{
            "snapshot":{"status":"verified","immutable_revision":REV,"manifest_sha256":SHA},
            "license_review":{"status":"approved","license_text_sha256":SHA,"legal_reviewer_id":"legal-1","reviewed_at":"2026-11-17T00:00:00Z","evidence_uri":"vault://legal"},
            "loader_compatibility":{"status":"passed","tested_revision":REV,"model_class":"AutoModel","runtime_versions":{"torch":"2.8"},"remote_code":{"status":"disabled"}},
            "real_inference":{"status":"completed","tested_revision":REV,"workflow_run_id":"run-1","internal_run_id":"internal-1","expected_response_count":10,"response_count":10,"error_count":0,"artifact_sha256":SHA},
            "resource_measurement":{"status":"recorded","runner_type":"runner","device":"cpu","peak_rss_bytes":1024,"mean_latency_seconds":1.0,"compute_record_sha256":SHA},
            "human_review":{"status":"passed","independent_reviewer_ids":["r1","r2"],"independence_attested":True,"adjudication_complete":True,"expected_response_count":10,"graded_response_count":10,"grade_report_sha256":SHA,"adjudication_sha256":SHA},
            "safety_review":{"status":"passed","reviewer_id":"safety-1","report_sha256":SHA},
            "holdout":{"status":"passed","case_count":20,"leakage_audit_passed":True,"audit_sha256":SHA},
            "corpus_integrity":{"status":"passed","corpus_sha256":SHA,"duplicate_count":0,"provenance_verified":True},
            "training_output_permission":{"status":"granted","document_sha256":SHA,"authorized_by":"rights-holder","authorized_at":"2026-11-17T00:00:00Z"},
        }
    }

def foundation_manifest():
    return {"schema_version":"vectolith-foundation-selection/1.0","decision_status":"approved",
        "selected_model_id":"publisher/model","immutable_revision":REV,
        "comparison_report_sha256":SHA,"approved_by":"approver","approved_at":"2026-11-17T00:00:00Z",
        "evaluation_evidence":[{"kind":"protected-holdout-report","sha256":SHA}]}

class TrainingPreflightTests(unittest.TestCase):
    def test_teacher_requires_all_ten_gates(self):
        manifest=teacher_manifest("teacher-a")
        self.assertEqual(validate_teacher_manifest(manifest,"teacher-a",REV),[])
        del manifest["gates"]["holdout"]
        self.assertTrue(any("holdout" in item for item in validate_teacher_manifest(manifest,"teacher-a",REV)))

    def test_foundation_must_be_explicitly_approved_and_exact(self):
        manifest=foundation_manifest()
        self.assertEqual(validate_foundation_selection(manifest,"publisher/model",REV),[])
        manifest["decision_status"]="pending"
        self.assertTrue(validate_foundation_selection(manifest,"publisher/model",REV))

    def test_training_preflight_requires_four_qualified_revision_matched_teachers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"teachers").mkdir()
            for i in range(4):
                (root/"teachers"/f"teacher-{i}.json").write_text(json.dumps(teacher_manifest(f"teacher-{i}")))
            selection=root/"foundation.json"; selection.write_text(json.dumps(foundation_manifest()))
            rows=[]
            for i in range(4):
                prompt=f"prompt-{i}"; response=f"response-{i}"
                rows.append({"accepted":True,"teacher_id":f"teacher-{i}","teacher_revision":REV,
                    "prompt":prompt,"response":response,
                    "content_sha256":hashlib.sha256((prompt+"\0"+response).encode()).hexdigest()})
            dataset=root/"data.jsonl"; dataset.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            validated, report=validate_training_preflight(dataset_path=dataset,foundation_model="publisher/model",
                foundation_revision=REV,foundation_selection_path=selection,teacher_manifest_dir=root/"teachers")
            self.assertEqual(len(validated),4)
            self.assertEqual(report["status"],"passed")
            self.assertEqual(len(report["teacher_manifest_sha256"]),4)

    def test_dataset_teacher_revision_mismatch_blocks_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"teachers").mkdir()
            for i in range(4):
                (root/"teachers"/f"teacher-{i}.json").write_text(json.dumps(teacher_manifest(f"teacher-{i}")))
            selection=root/"foundation.json"; selection.write_text(json.dumps(foundation_manifest()))
            rows=[]
            for i in range(4):
                prompt=f"p{i}"; response=f"r{i}"
                rows.append({"accepted":True,"teacher_id":f"teacher-{i}","teacher_revision":"c"*40,
                    "prompt":prompt,"response":response,"content_sha256":hashlib.sha256((prompt+"\0"+response).encode()).hexdigest()})
            dataset=root/"data.jsonl"; dataset.write_text("\n".join(json.dumps(x) for x in rows))
            with self.assertRaisesRegex(ValueError,"revision does not match"):
                validate_training_preflight(dataset_path=dataset,foundation_model="publisher/model",
                    foundation_revision=REV,foundation_selection_path=selection,teacher_manifest_dir=root/"teachers")

if __name__=="__main__": unittest.main()
