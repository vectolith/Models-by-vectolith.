from __future__ import annotations
import unittest
from evaluation.protected_holdout_manifest import SCHEMA, validate_manifest

def valid_manifest():
    d="a"*64
    return {"schema_version":SCHEMA,"dataset_version":"holdout-v1","dataset_sha256":d,"case_count":100,
      "custody":{"storage_uri":"vault://restricted/core-prime/holdout-v1","access_boundary":"dedicated_vault",
        "encryption_at_rest":True,"key_custody_separate":True,"custodian_id":"custodian-1","evaluator_operator_id":"operator-1"},
      "execution":{"evaluator_service_id":"prime-eval-prod","deployment_image_sha256":d,
        "pull_request_code_denied":True,"candidate_network_egress_denied":True,
        "dataset_mount_read_only":True,"result_channel_separated":True},
      "audit":{"access_log_sha256":d,"leakage_audit_sha256":d,"provenance_report_sha256":d,
        "public_fixture_overlap_checked":True,"unauthorized_access_count":0,"reviewed_by":"independent-auditor"}}

class ProtectedHoldoutManifestTests(unittest.TestCase):
    def test_complete_manifest_passes(self):
        self.assertEqual(validate_manifest(valid_manifest()),[])
    def test_public_fixtures_shared_operator_and_pr_access_block(self):
        m=valid_manifest()
        m["custody"]["storage_uri"]="https://github.com/org/repo/fixtures.jsonl"
        m["custody"]["evaluator_operator_id"]=m["custody"]["custodian_id"]
        m["execution"]["pull_request_code_denied"]=False
        m["audit"]["public_fixture_overlap_checked"]=False
        errors=validate_manifest(m)
        for expected in ("restricted_storage_uri_required","independent_evaluator_operator_required",
                         "execution_control_missing:pull_request_code_denied","public_fixture_overlap_audit_required"):
            self.assertIn(expected,errors)
    def test_missing_audit_digest_blocks(self):
        m=valid_manifest(); m["audit"]["leakage_audit_sha256"]=""
        self.assertIn("audit_digest_invalid:leakage_audit_sha256",validate_manifest(m))
if __name__=="__main__": unittest.main()
