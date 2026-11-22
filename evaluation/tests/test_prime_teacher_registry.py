from __future__ import annotations
import json, unittest, tempfile, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class PrimeTeacherRegistryTests(unittest.TestCase):
    def test_new_candidates_are_registered_as_independent_additive_contributors(self):
        data=json.loads((ROOT/"prime_teacher_candidate_registry.json").read_text())
        rows={x["candidate_id"]:x for x in data["contributors"]}
        self.assertEqual(set(rows),{"qwen3.5-2b","gemma-4-e2b-it","nemotron-3-nano-4b","lfm2.5-2.6b"})
        self.assertEqual(data["role"],"ash_prime")
        for row in rows.values():
            self.assertFalse(row["local_inference_authorized"])
            self.assertEqual(row["license_review"],"pending_human_legal_review")
            self.assertEqual(row["training_output_permission"],"not_verified")
            self.assertEqual(row["teacher_qualification"],"not_qualified")
    def test_candidate_loader_contract_matches_model_architectures(self):
        data=json.loads((ROOT/"prime_teacher_candidate_registry.json").read_text())
        rows={x["candidate_id"]:x for x in data["contributors"]}
        self.assertEqual(rows["qwen3.5-2b"]["loader"],"multimodal")
        self.assertEqual(rows["gemma-4-e2b-it"]["loader"],"AutoModelForMultimodalLM")
        self.assertEqual(rows["nemotron-3-nano-4b"]["loader"],"AutoModelForCausalLM")
        self.assertEqual(rows["lfm2.5-2.6b"]["loader"],"causal")
        self.assertEqual(rows["lfm2.5-2.6b"]["expected_model_type"],"lfm2")
        self.assertEqual(rows["lfm2.5-2.6b"]["expected_architecture"],"Lfm2ForCausalLM")
        self.assertEqual(rows["lfm2.5-2.6b"]["license_tag"],"lfm1.0")
        self.assertEqual(rows["lfm2.5-2.6b"]["revision"], "7141b56cd4650af95c7c7b86983443aed050c96a")
        self.assertFalse(rows["lfm2.5-2.6b"]["local_inference_authorized"])
        workflow=(ROOT.parent/".github"/"workflows"/"ash-prime-independent-candidate-inference.yml").read_text()
        self.assertIn("candidate_id: qwen3.5-2b",workflow)
        self.assertIn("candidate_id: lfm2.5-2.6b",workflow)
        self.assertIn("artifact: prime-teacher-lfm2.5-2.6b",workflow)
        self.assertIn("loader: multimodal",workflow)
    def test_pinned_revisions_are_full_commit_shas(self):
        data=json.loads((ROOT/"prime_teacher_candidate_registry.json").read_text())
        for row in data["contributors"]:
            revision=row.get("revision")
            if revision is not None:
                self.assertEqual(len(revision),40)
                self.assertRegex(revision,r"^[0-9a-f]{40}$")
    def test_independent_workflow_is_fail_closed_and_covers_v1_to_v4(self):
        workflow=(ROOT.parent/".github"/"workflows"/"ash-prime-independent-candidate-inference.yml").read_text()
        self.assertIn("fail-fast: false",workflow)
        self.assertIn("runs-on: ubuntu-24.04",workflow)
        self.assertIn("Verify public-repository runner policy",workflow)
        self.assertIn("GITHUB_REPOSITORY",workflow)
        self.assertNotIn("self-hosted",workflow)
        self.assertIn("prime_benchmark_v1.jsonl",workflow)
        for version in ("v2","v3","v4"): self.assertIn(f"prime_qualification_{version}.jsonl",workflow)
        self.assertIn("if: always()",workflow)
        self.assertIn("prime-teacher-comparison-report",workflow)
    def test_historical_only_mode_skips_candidate_matrix_and_reuses_same_comparator(self):
        workflow=(ROOT.parent/".github"/"workflows"/"ash-prime-independent-candidate-inference.yml").read_text()
        self.assertIn("historical_only:",workflow)
        self.assertIn("if: ${{ inputs.run_candidates == true }}",workflow)
        self.assertIn("inputs.run_candidates == true || inputs.historical_only == true",workflow)
        self.assertIn('if: ${{ inputs.run_candidates == true }}',workflow)
        self.assertIn('HISTORICAL_ONLY: ${{ inputs.historical_only }}',workflow)
        self.assertIn('OUT=artifacts/reports/historical-prime-teacher-integrity.json',workflow)
        self.assertIn('OUT=artifacts/reports/prime-teacher-disagreement.json',workflow)
        self.assertIn('find artifacts/prime-teachers',workflow)
        self.assertIn('refusing to emit an empty report',workflow)
        self.assertIn('name: prime-teacher-comparison-report',workflow)
        self.assertIn("expected four independently completed candidate response JSON files",workflow)
        self.assertIn('"$candidate_count" -ne 4',workflow)
    def test_historical_teacher_artifacts_are_required_per_preserved_run(self):
        workflow=(ROOT.parent/".github"/"workflows"/"ash-prime-independent-candidate-inference.yml").read_text()
        for run_id in ("43796213917","43820188813","43821046671"):
            self.assertIn(run_id,workflow)
        for artifact in (
            "prime-teacher-granite-3.1-3b-a800m",
            "prime-teacher-granite-4.2-3b",
            "prime-teacher-minicpm5-2b",
            "prime-teacher-lfm2.5-2.6b",
            "prime-teacher-phi-4-mini-instruct",
        ):
            self.assertIn(artifact,workflow)
        self.assertIn("Verify all preserved historical teacher artifacts exist",workflow)
        self.assertIn("set -euo pipefail",workflow)
        historical=workflow.split("Download historical Prime run")
        self.assertEqual(len(historical),4)
        for block in historical[1:]:
            self.assertNotIn("continue-on-error: true",block.split("      - name:",1)[0])
    def test_historical_ash_prime_jsonl_schema_is_accepted_without_rewriting(self):
        sys.path.insert(0,str(ROOT))
        from compare_prime_teacher_responses import load_artifact
        revision="a"*40
        row={
            "case_id":"historical-case-001","candidate_id":"granite-3.1-3b-a800m",
            "model_revision":revision,"run_id":"historical-run-40",
            "prompt_sha256":"b"*64,"response_text":"historical response",
            "completion_status":"complete"
        }
        record={
            "schema_version":"vectolith-real-candidate-evaluation/1.2",
            "candidate_id":"granite-3.1-3b-a800m",
            "repo_id":"ibm-granite/granite-3.1-3b-a800m-instruct",
            "immutable_revision":revision,"run_id":"historical-run-40",
            "case_count":1,"results":[row]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"granite-3.1-3b-a800m-ash_prime.json"
            path.write_text(json.dumps(record),encoding="utf-8")
            path.with_suffix(".jsonl").write_text(json.dumps(row)+chr(10),encoding="utf-8")
            loaded,rows=load_artifact(path)
            self.assertEqual(loaded["candidate_id"],record["candidate_id"])
            self.assertEqual(rows["historical-case-001"]["response_text"],"historical response")
            self.assertEqual(path.name,"granite-3.1-3b-a800m-ash_prime.json")
    def test_comparator_rejects_json_jsonl_response_mismatch(self):
        sys.path.insert(0,str(ROOT))
        from compare_prime_teacher_responses import load_artifact
        revision="a"*40
        row={"case_id":"case-1","candidate_id":"teacher-a","model_revision":revision,
             "run_id":"run-1","prompt_sha256":"b"*64,"completion_status":"complete",
             "response_text":"raw response"}
        record={"candidate_id":"teacher-a","repo_id":"org/model","immutable_revision":revision,
                "run_id":"run-1","case_count":1,"results":[dict(row,response_text="different summary")]}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"teacher-ash_prime.json"
            path.write_text(json.dumps(record),encoding="utf-8")
            path.with_suffix(".jsonl").write_text(json.dumps(row)+chr(10),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"embedded JSON/JSONL mismatch"):
                load_artifact(path)
    def test_comparator_rejects_invalid_prompt_hash(self):
        sys.path.insert(0,str(ROOT))
        from compare_prime_teacher_responses import load_artifact
        revision="a"*40
        row={"case_id":"case-1","candidate_id":"teacher-a","model_revision":revision,
             "run_id":"run-1","prompt_sha256":"not-a-sha256","completion_status":"complete",
             "response_text":"raw response"}
        record={"candidate_id":"teacher-a","repo_id":"org/model","immutable_revision":revision,
                "run_id":"run-1","case_count":1}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"teacher-ash_prime.json"
            path.write_text(json.dumps(record),encoding="utf-8")
            path.with_suffix(".jsonl").write_text(json.dumps(row)+chr(10),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"invalid or missing prompt_sha256"):
                load_artifact(path)
    def test_nemotron_35_candidates_are_present_with_separate_runtime_and_permission_gates(self):
        panel=json.loads((ROOT/"nemotron_3_5_candidate_panel.json").read_text())
        rows={x["candidate_id"]:x for x in panel["candidates"]}
        self.assertEqual(set(rows),{"nemotron-3.5-lightning-30b-a3b","nemotron-3.5-super-vl-120b-a12b","nemotron-3.5-bolt-e4b"})
        self.assertEqual(set(panel["target_panels"]),{"ash_prime","fyr_prima"})
        self.assertEqual(panel["fyr_prima_execution_status"],"paused")
        for row in rows.values():
            self.assertFalse(row["local_inference_authorized"])
            self.assertEqual(row["license_review"],"pending_human_legal_review")
            self.assertEqual(row["training_output_permission"],"not_verified")
            self.assertEqual(row["teacher_qualification"],"not_qualified")
        self.assertIn("blocked_no_compatible_gpu_runner",rows["nemotron-3.5-lightning-30b-a3b"]["execution_availability_status"])
        self.assertIn("blocked_no_compatible_gpu_runner",rows["nemotron-3.5-super-vl-120b-a12b"]["execution_availability_status"])
        self.assertEqual(rows["nemotron-3.5-bolt-e4b"]["runtime"],"llama.cpp (GGUF Q4_K_M)")
        self.assertIn("6.18 GB",rows["nemotron-3.5-bolt-e4b"]["notes"])
        self.assertIn("runtime_adapter",rows["nemotron-3.5-bolt-e4b"]["execution_availability_status"])
    def test_model_card_named_custom_license_precedes_generic_other_tag(self):
        sys.path.insert(0,str(ROOT))
        from snapshot_prime_teacher import model_card_license_tag
        self.assertEqual(model_card_license_tag({"license":"other","license_name":"lfm1.0"}),"lfm1.0")
        self.assertEqual(model_card_license_tag({"license":"apache-2.0"}),"apache-2.0")
    def test_new_scripts_compile(self):
        for name in ("snapshot_prime_teacher.py","prime_candidate_policy_gate.py","verify_prime_teacher_loader.py","compare_prime_teacher_responses.py"):
            path=ROOT/name
            compile(path.read_text(encoding="utf-8"),str(path),"exec")

    def test_inference_gate_requires_revision_bound_human_evidence(self):
        sys.path.insert(0, str(ROOT))
        from prime_candidate_policy_gate import candidate_is_authorized

        registry = json.loads((ROOT / "prime_teacher_candidate_registry.json").read_text())
        candidate = dict(registry["contributors"][0])
        self.assertFalse(candidate_is_authorized(candidate))

        revision = candidate["revision"]
        evidence = {
            "status": "approved",
            "model_revision": revision,
            "license_text_sha256": "a" * 64,
            "review_document_sha256": "b" * 64,
            "reviewer_id": "authorized-legal-reviewer",
            "reviewed_at": "2026-11-18T12:00:00+00:00",
            "evidence_uri": "https://evidence.example/legal-review",
        }
        authorization = {
            "status": "approved",
            "model_revision": revision,
            "document_sha256": "c" * 64,
            "authorized_by": "model-rights-holder",
            "authorized_at": "2026-11-18T12:05:00+00:00",
            "evidence_uri": "https://evidence.example/inference-authorization",
        }
        candidate.update({
            "license_review": "approved_for_local_inference",
            "local_inference_authorized": True,
            "license_review_evidence": evidence,
            "local_inference_authorization": authorization,
        })
        self.assertTrue(candidate_is_authorized(candidate))

        candidate["local_inference_authorization"] = {
            **authorization,
            "model_revision": "d" * 40,
        }
        self.assertFalse(candidate_is_authorized(candidate))

        candidate["local_inference_authorization"] = authorization
        candidate["license_evidence_conflict"] = {
            "status": "unresolved",
            "resolution": None,
        }
        self.assertFalse(candidate_is_authorized(candidate))

        candidate.pop("license_evidence_conflict")
        candidate["license_review_evidence"] = {
            **evidence,
            "reviewed_at": "2026-11-18T12:00:00",
        }
        self.assertFalse(candidate_is_authorized(candidate))

if __name__=="__main__": unittest.main()
