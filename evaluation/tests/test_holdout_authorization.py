from __future__ import annotations
import base64, hashlib, hmac, json, os, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from evaluation.holdout_authorization import verify_authorization, claim_and_audit_run

def signed_token(path, secret, payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
    enc=base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig=hmac.new(secret.encode(),raw,hashlib.sha256).digest()
    path.write_text(enc+"."+base64.urlsafe_b64encode(sig).decode().rstrip("="))
    if os.name=="posix": path.chmod(0o600)

class HoldoutAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        if os.name=="posix": self.root.chmod(0o700)
        self.secret="test-only-secret"
        now=datetime.now(timezone.utc)
        self.payload={"dataset_version":"holdout-v1","dataset_sha256":"a"*64,
            "candidate_id":"candidate-a","model_revision":"b"*40,"role":"ash_prime",
            "principal_id":"custodian-approved-runner","run_id":"run-001",
            "issued_at":now.isoformat(),"expires_at":(now+timedelta(minutes=10)).isoformat()}
        self.token=self.root/"authorization.token"; signed_token(self.token,self.secret,self.payload)
        self.expected={k:self.payload[k] for k in ("dataset_version","dataset_sha256","candidate_id","model_revision","role","principal_id")}

    def tearDown(self): self.tmp.cleanup()

    def test_valid_signed_authorization_is_bound_to_exact_run(self):
        result=verify_authorization(self.token,self.secret,expected=self.expected)
        self.assertEqual(result["run_id"],"run-001")
        self.assertEqual(len(result["token_sha256"]),64)

    def test_tampered_signature_is_rejected(self):
        self.token.write_text(self.token.read_text().rsplit(".",1)[0]+".invalid")
        with self.assertRaisesRegex(ValueError,"signature"):
            verify_authorization(self.token,self.secret,expected=self.expected)

    def test_candidate_revision_or_principal_mismatch_is_rejected(self):
        expected=dict(self.expected,candidate_id="candidate-b")
        with self.assertRaisesRegex(ValueError,"candidate_id"):
            verify_authorization(self.token,self.secret,expected=expected)

    def test_expired_authorization_is_rejected(self):
        expired=dict(self.payload,expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        signed_token(self.token,self.secret,expired)
        with self.assertRaisesRegex(ValueError,"not currently valid"):
            verify_authorization(self.token,self.secret,expected=self.expected)

    def test_run_claim_is_single_use_and_audited(self):
        authorization=verify_authorization(self.token,self.secret,expected=self.expected)
        audit=self.root/"audit"
        marker=claim_and_audit_run(audit,authorization,candidate_id="candidate-a",
            revision="b"*40,dataset_version="holdout-v1",dataset_sha256="a"*64)
        self.assertTrue(marker.exists())
        event=json.loads(marker.read_text())
        self.assertEqual(event["principal_id"],"custodian-approved-runner")
        self.assertEqual(event["dataset_sha256"],"a"*64)
        with self.assertRaisesRegex(ValueError,"already been used"):
            claim_and_audit_run(audit,authorization,candidate_id="candidate-a",
                revision="b"*40,dataset_version="holdout-v1",dataset_sha256="a"*64)

if __name__=="__main__": unittest.main()
