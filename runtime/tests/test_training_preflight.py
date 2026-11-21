from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from vectolith_runtime.protected_holdout import DEPLOYMENT_SCHEMA, RESULT_SCHEMA, canonical_digest
from vectolith_runtime.training_preflight import (
    validate_foundation_selection, validate_teacher_manifest, validate_training_preflight, validate_training_execution_manifest,
)

SHA="a"*64
REV="b"*40
CODE_REV="d"*40
TRAIN_CONFIG={"max_seq_length":4096,"epochs":1.0,"learning_rate":2e-5,
    "per_device_batch_size":1,"gradient_accumulation_steps":8,
    "validation_fraction":0.1,"seed":42,"use_lora":True}

def teacher_manifest(name, deployment_sha=SHA, result_sha=SHA):
    return {
        "schema_version":"vectolith-teacher-qualification-candidate/1.0",
        "candidate_id":name,"immutable_revision":REV,
        "gates":{
            "snapshot":{"status":"verified","immutable_revision":REV,"manifest_sha256":SHA},
            "license_review":{"status":"approved","license_text_sha256":SHA,"legal_reviewer_id":"legal-1","reviewed_at":"2026-11-17T00:00:00Z","evidence_uri":"vault://legal"},
            "loader_compatibility":{"status":"passed","tested_revision":REV,"model_class":"AutoModel","runtime_versions":{"torch":"2.8"},"remote_code":{"status":"disabled"}},
            "real_inference":{"status":"completed","tested_revision":REV,"workflow_run_id":"run-1","internal_run_id":"internal-1","expected_response_count":10,"response_count":10,"error_count":0,"artifact_sha256":SHA},
            "resource_measurement":{"status":"recorded","runner_type":"runner","device":"cpu","peak_rss_bytes":1024,"mean_latency_seconds":1.0,"compute_record_sha256":SHA},
            "grading":{"status":"passed","expected_response_count":10,"graded_response_count":10,"grade_report_sha256":SHA,"rubric_version":"prime-rubric-v1",
                "review_method":"independent_human","independent_reviewer_ids":["human-1","human-2"],
                "independence_attestation_sha256":SHA,"agreement_report_sha256":SHA,"adjudication_report_sha256":SHA},
            "safety_review":{"status":"passed","reviewer_id":"safety-1","report_sha256":SHA},
            "holdout":{"status":"passed","case_count":100,"leakage_audit_passed":True,"audit_sha256":SHA,"deployment_manifest_sha256":deployment_sha,"evaluation_report_sha256":result_sha},
            "corpus_integrity":{"status":"passed","corpus_sha256":SHA,"duplicate_count":0,"provenance_verified":True},
            "training_output_permission":{"status":"granted","document_sha256":SHA,"authorized_by":"rights-holder","authorized_at":"2026-11-17T00:00:00Z"},
        }
    }

def foundation_manifest():
    return {"schema_version":"vectolith-foundation-selection/1.0","decision_status":"approved",
        "selected_model_id":"publisher/model","immutable_revision":REV,
        "comparison_report_sha256":SHA,"approved_by":"approver","approved_at":"2026-11-17T00:00:00Z",
        "evaluation_evidence":[
            {"kind":kind,"sha256":SHA,"model_id":"publisher/model","immutable_revision":REV}
            for kind in ("candidate_metadata","license_review","training_output_permission",
                "loader_compatibility","resource_measurement","capability_evaluation",
                "protected_holdout","baseline_comparison")
        ]}

def write_holdout_evidence(root, teacher_ids):
    deployment = {
        "schema_version": DEPLOYMENT_SCHEMA, "dataset_version": "holdout-v1",
        "dataset_sha256": SHA, "case_count": 100, "minimum_required_pass_rate": 0.8,
        "custody": {"storage_uri": "vault://restricted/prime/holdout-v1",
            "access_boundary": "dedicated_vault", "encryption_at_rest": True,
            "key_custody_separate": True, "custodian_id": "custodian-1",
            "evaluator_operator_id": "operator-1"},
        "execution": {"evaluator_service_id": "prime-evaluator",
            "deployment_image_sha256": SHA, "pull_request_code_denied": True,
            "candidate_network_egress_denied": True, "dataset_mount_read_only": True,
            "result_channel_separated": True},
        "audit": {"access_log_sha256": SHA, "leakage_audit_sha256": SHA,
            "provenance_report_sha256": SHA, "public_fixture_overlap_checked": True,
            "unauthorized_access_count": 0, "reviewed_by": "independent-auditor"},
    }
    deployment_path = root / "holdout-deployment.json"
    deployment_path.write_text(json.dumps(deployment))
    deployment_sha = canonical_digest(deployment)
    results_dir = root / "holdout-results"
    results_dir.mkdir()
    result_hashes = {}
    for teacher_id in teacher_ids:
        report = {
            "schema_version": RESULT_SCHEMA, "deployment_manifest_sha256": deployment_sha,
            "candidate_id": teacher_id, "candidate_revision": REV,
            "evaluator_id": "operator-1", "evaluator_image_sha256": SHA,
            "case_count": 100, "verified_pass_count": 90, "verified_fail_count": 10,
            "unscored_count": 0, "pass_rate": 0.9, "minimum_required_pass_rate": 0.8,
            "status": "passed", "evaluation_suite_version": "prime-holdout-v1",
            "evaluated_at": "2026-11-17T00:00:00Z", "evaluator_run_id": "run-" + teacher_id,
        }
        path = results_dir / f"{teacher_id}.json"
        path.write_text(json.dumps(report))
        result_hashes[teacher_id] = hashlib.sha256(path.read_bytes()).hexdigest()
    return deployment_path, results_dir, deployment_sha, result_hashes


def write_execution_approval(root, dataset_path):
    manifest = {
        "schema_version": "vectolith-training-execution-approval/1.0",
        "status": "approved", "run_id": "core-prime-test-run-001",
        "student_model_id": "core-prime", "foundation_model": "publisher/model",
        "foundation_revision": REV,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "training_code_revision": CODE_REV,
        "approved_by": "training-approver", "approved_at": "2026-11-17T00:00:00Z",
        "approval_reference": "approval://core-prime/test-run-001",
        "approval_document_sha256": SHA,
        "approved_configuration": TRAIN_CONFIG,
        "compute": {"provider": "test-provider", "account_or_project": "test-project",
            "region": "local", "runner_type": "isolated-test-runner",
            "accelerator_type": "test-gpu", "accelerator_count": 1,
            "runtime_image": "vectolith/core-prime-trainer:test",
            "runtime_image_sha256": SHA,
            "execution_environment_reference": "environment://core-prime/test-run-001",
            "maximum_runtime_seconds": 3600,
            "environment_approval_sha256": SHA,
            "software_versions": {"python": "3.11", "torch": "2.8",
                "transformers": "4.55", "datasets": "3.0", "peft": "0.13", "accelerate": "1.0"}},
        "capacity": {"available_vram_bytes": 1000, "available_ram_bytes": 10000,
            "available_storage_bytes": 100000, "estimated_peak_vram_bytes": 800,
            "estimated_peak_ram_bytes": 8000, "estimated_storage_bytes": 50000,
            "resource_probe_sha256": SHA},
    }
    path = root / "training-execution-approval.json"
    path.write_text(json.dumps(manifest))
    return path

class TrainingPreflightTests(unittest.TestCase):
    def test_teacher_requires_all_ten_gates(self):
        manifest=teacher_manifest("teacher-a")
        self.assertEqual(validate_teacher_manifest(manifest,"teacher-a",REV),[])
        manifest=teacher_manifest("teacher-a")
        manifest["gates"]["grading"]["independent_reviewer_ids"]=["human-1"]
        self.assertIn("grading independent human review, agreement, or adjudication gate failed", validate_teacher_manifest(manifest,"teacher-a",REV))
        manifest=teacher_manifest("teacher-a")
        manifest["gates"]["grading"]["review_method"]="ai"
        self.assertIn("grading independent human review, agreement, or adjudication gate failed", validate_teacher_manifest(manifest,"teacher-a",REV))
        manifest=teacher_manifest("teacher-a")
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
            teacher_ids=[f"teacher-{i}" for i in range(4)]
            deployment_path, results_dir, deployment_sha, result_hashes = write_holdout_evidence(root, teacher_ids)
            for teacher_id in teacher_ids:
                (root/"teachers"/f"{teacher_id}.json").write_text(json.dumps(teacher_manifest(teacher_id,deployment_sha,result_hashes[teacher_id])))
            selection=root/"foundation.json"; selection.write_text(json.dumps(foundation_manifest()))
            rows=[]
            for i in range(4):
                prompt=f"prompt-{i}"; response=f"response-{i}"
                rows.append({"schema_version":"1.0","student_model_id":"core-prime","run_id":"corpus-run-001",
                    "task_id":f"task-{i}","competency":"reasoning","accepted":True,
                    "teacher_id":f"teacher-{i}","teacher_revision":REV,"reviewer_id":f"teacher-{(i+1)%4}",
                    "review":{"score":0.9,"verdict":"accept","issues":[]},
                    "human_review":{"status":"approved","independent_reviewer_ids":["human-1","human-2"],
                        "adjudication_complete":True,"adjudication_id":f"adj-{i}",
                        "review_report_sha256":SHA,"adjudication_sha256":SHA},
                    "prompt":prompt,"response":response,
                    "content_sha256":hashlib.sha256((prompt+"\0"+response).encode()).hexdigest()})
            dataset=root/"data.jsonl"; dataset.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            execution_path=write_execution_approval(root,dataset)
            validated, report=validate_training_preflight(dataset_path=dataset,foundation_model="publisher/model",
                foundation_revision=REV,foundation_selection_path=selection,teacher_manifest_dir=root/"teachers",holdout_deployment_manifest_path=deployment_path,holdout_evaluation_results_dir=results_dir,training_execution_manifest_path=execution_path,training_code_revision=CODE_REV,training_config=TRAIN_CONFIG)
            self.assertEqual(len(validated),4)
            self.assertEqual(report["status"],"passed")
            self.assertEqual(len(report["teacher_manifest_sha256"]),4)
            teacher0_path=root/"teachers"/"teacher-0.json"
            teacher0=json.loads(teacher0_path.read_text())
            teacher0["gates"]["grading"]["independent_reviewer_ids"]=["teacher-1","human-2"]
            teacher0_path.write_text(json.dumps(teacher0))
            with self.assertRaisesRegex(ValueError,"grading reviewers must be outside the qualified teacher cohort"):
                validate_training_preflight(dataset_path=dataset,foundation_model="publisher/model",
                    foundation_revision=REV,foundation_selection_path=selection,teacher_manifest_dir=root/"teachers",
                    holdout_deployment_manifest_path=deployment_path,holdout_evaluation_results_dir=results_dir,
                    training_execution_manifest_path=execution_path,training_code_revision=CODE_REV,training_config=TRAIN_CONFIG)

    def test_dataset_teacher_revision_mismatch_blocks_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"teachers").mkdir()
            teacher_ids=[f"teacher-{i}" for i in range(4)]
            deployment_path, results_dir, deployment_sha, result_hashes = write_holdout_evidence(root, teacher_ids)
            for teacher_id in teacher_ids:
                (root/"teachers"/f"{teacher_id}.json").write_text(json.dumps(teacher_manifest(teacher_id,deployment_sha,result_hashes[teacher_id])))
            selection=root/"foundation.json"; selection.write_text(json.dumps(foundation_manifest()))
            rows=[]
            for i in range(4):
                prompt=f"p{i}"; response=f"r{i}"
                rows.append({"schema_version":"1.0","student_model_id":"core-prime","run_id":"corpus-run-001",
                    "task_id":f"task-{i}","competency":"reasoning","accepted":True,
                    "teacher_id":f"teacher-{i}","teacher_revision":"c"*40,"reviewer_id":f"teacher-{(i+1)%4}",
                    "review":{"score":0.9,"verdict":"accept","issues":[]},
                    "human_review":{"status":"approved","independent_reviewer_ids":["human-1","human-2"],
                        "adjudication_complete":True,"adjudication_id":f"adj-{i}",
                        "review_report_sha256":SHA,"adjudication_sha256":SHA},
                    "prompt":prompt,"response":response,
                    "content_sha256":hashlib.sha256((prompt+"\0"+response).encode()).hexdigest()})
            dataset=root/"data.jsonl"; dataset.write_text("\n".join(json.dumps(x) for x in rows))
            execution_path=write_execution_approval(root,dataset)
            with self.assertRaisesRegex(ValueError,"revision does not match"):
                validate_training_preflight(dataset_path=dataset,foundation_model="publisher/model",
                    foundation_revision=REV,foundation_selection_path=selection,teacher_manifest_dir=root/"teachers",
                    holdout_deployment_manifest_path=deployment_path,holdout_evaluation_results_dir=results_dir,training_execution_manifest_path=execution_path,training_code_revision=CODE_REV,training_config=TRAIN_CONFIG)

    def test_training_preflight_rejects_unscored_holdout_cases_even_with_updated_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"teachers").mkdir()
            teacher_ids=[f"teacher-{i}" for i in range(4)]
            deployment_path, results_dir, deployment_sha, result_hashes = write_holdout_evidence(root, teacher_ids)
            report_path=results_dir/"teacher-0.json"
            report=json.loads(report_path.read_text())
            report["verified_pass_count"]=89
            report["unscored_count"]=1
            report["pass_rate"]=0.89
            report_path.write_text(json.dumps(report))
            result_hashes["teacher-0"]=hashlib.sha256(report_path.read_bytes()).hexdigest()
            for teacher_id in teacher_ids:
                (root/"teachers"/f"{teacher_id}.json").write_text(json.dumps(
                    teacher_manifest(teacher_id,deployment_sha,result_hashes[teacher_id])))
            selection=root/"foundation.json"; selection.write_text(json.dumps(foundation_manifest()))
            rows=[]
            for i in range(4):
                prompt=f"p{i}"; response=f"r{i}"
                rows.append({"accepted":True,"teacher_id":f"teacher-{i}","teacher_revision":REV,
                    "prompt":prompt,"response":response,
                    "content_sha256":hashlib.sha256((prompt+"\0"+response).encode()).hexdigest()})
            dataset=root/"data.jsonl"; dataset.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            execution_path=write_execution_approval(root,dataset)
            with self.assertRaisesRegex(ValueError,"unscored"):
                validate_training_preflight(dataset_path=dataset,foundation_model="publisher/model",
                    foundation_revision=REV,foundation_selection_path=selection,teacher_manifest_dir=root/"teachers",
                    holdout_deployment_manifest_path=deployment_path,holdout_evaluation_results_dir=results_dir,
                    training_execution_manifest_path=execution_path,training_code_revision=CODE_REV,training_config=TRAIN_CONFIG)


    def test_dataset_rows_require_core_prime_peer_review_and_human_adjudication(self):
        from vectolith_runtime.training_preflight import validate_training_dataset_rows
        base = {"schema_version":"1.0","student_model_id":"core-prime","run_id":"run-1",
            "task_id":"task-1","competency":"reasoning","accepted":True,
            "teacher_id":"teacher-a","teacher_revision":REV,"reviewer_id":"teacher-b",
            "review":{"score":0.9,"verdict":"accept","issues":[]},
            "human_review":{"status":"approved","independent_reviewer_ids":["human-1","human-2"],
                "adjudication_complete":True,"adjudication_id":"adj-1",
                "review_report_sha256":SHA,"adjudication_sha256":SHA},
            "prompt":"Explain a proof","response":"A valid explanation",
            "content_sha256":hashlib.sha256(("Explain a proof"+"\0"+"A valid explanation").encode()).hexdigest()}
        self.assertEqual(validate_training_dataset_rows([base], {"teacher-a":REV,"teacher-b":REV}), [])
        cases = [
            ("student_model_id","core-prima","student_model_id"),
            ("task_id","","task_id"),
            ("reviewer_id","teacher-a","peer reviewer"),
            ("review",{"score":0.99,"verdict":"reject"},"peer review"),
            ("human_review",None,"human review"),
            ("content_sha256","0"*64,"content digest"),
        ]
        for field, value, expected in cases:
            row = dict(base)
            row[field] = value
            errors = validate_training_dataset_rows([row], {"teacher-a":REV,"teacher-b":REV})
            self.assertTrue(any(expected in error for error in errors), (field, errors))

    def test_dataset_rows_reject_duplicate_task_teacher_pairs(self):
        from vectolith_runtime.training_preflight import validate_training_dataset_rows
        row = {"schema_version":"1.0","student_model_id":"core-prime","run_id":"run-1",
            "task_id":"task-1","competency":"reasoning","accepted":True,
            "teacher_id":"teacher-a","teacher_revision":REV,"reviewer_id":"teacher-b",
            "review":{"score":0.9,"verdict":"accept","issues":[]},
            "human_review":{"status":"approved","independent_reviewer_ids":["human-1","human-2"],
                "adjudication_complete":True,"adjudication_id":"adj-1",
                "review_report_sha256":SHA,"adjudication_sha256":SHA},
            "prompt":"Explain a proof","response":"A valid explanation",
            "content_sha256":hashlib.sha256(("Explain a proof"+"\0"+"A valid explanation").encode()).hexdigest()}
        errors = validate_training_dataset_rows([row, dict(row)], {"teacher-a":REV,"teacher-b":REV})
        self.assertTrue(any("duplicate task_id/teacher_id" in error for error in errors))

    def test_training_execution_approval_binds_exact_config_and_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dataset=root/"dataset.jsonl"
            dataset.write_text('{"accepted":true}\n')
            approval_path=write_execution_approval(root,dataset)
            manifest=json.loads(approval_path.read_text())
            kwargs={"foundation_model":"publisher/model","foundation_revision":REV,
                "dataset_sha256":hashlib.sha256(dataset.read_bytes()).hexdigest(),
                "training_code_revision":CODE_REV,"training_config":TRAIN_CONFIG}
            self.assertEqual(validate_training_execution_manifest(manifest,**kwargs),[])
            manifest["capacity"]["estimated_peak_vram_bytes"]=1001
            errors=validate_training_execution_manifest(manifest,**kwargs)
            self.assertIn("training resource estimate exceeds measured capacity",errors)
            manifest["capacity"]["estimated_peak_vram_bytes"]=800
            manifest["approved_configuration"]["learning_rate"]=1e-4
            errors=validate_training_execution_manifest(manifest,**kwargs)
            self.assertIn("training configuration differs from approved configuration",errors)


    def test_training_execution_requires_revision_bound_environment_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dataset=root/"dataset.jsonl"
            dataset.write_text('{"accepted":true}\\n')
            approval_path=write_execution_approval(root,dataset)
            manifest=json.loads(approval_path.read_text())
            manifest["compute"]["environment_approval_sha256"]="not-a-sha256"
            manifest["compute"]["execution_environment_reference"]=""
            manifest["compute"]["maximum_runtime_seconds"]=0
            kwargs={"foundation_model":"publisher/model","foundation_revision":REV,
                "dataset_sha256":hashlib.sha256(dataset.read_bytes()).hexdigest(),
                "training_code_revision":CODE_REV,"training_config":TRAIN_CONFIG}
            errors=validate_training_execution_manifest(manifest,**kwargs)
            self.assertIn("training execution environment approval digest missing",errors)
            self.assertIn("training compute field missing:execution_environment_reference",errors)
            self.assertIn("training maximum_runtime_seconds is missing or invalid",errors)

    def test_approval_timestamps_must_include_timezone(self):
        manifest=teacher_manifest("teacher-a")
        manifest["gates"]["license_review"]["reviewed_at"]="2026-11-17T00:00:00"
        self.assertTrue(any("license review gate failed" in item for item in validate_teacher_manifest(manifest,"teacher-a",REV)))
        foundation=foundation_manifest()
        foundation["approved_at"]="2026-11-17T00:00:00"
        self.assertTrue(any("approval provenance" in item for item in validate_foundation_selection(foundation,"publisher/model",REV)))

if __name__=="__main__": unittest.main()
