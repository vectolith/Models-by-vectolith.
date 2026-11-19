import importlib.util,tempfile,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_verifier",ROOT/"verify_release_bundle.py");v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class ReleaseVerifierTests(unittest.TestCase):
 def test_complete_integrity_bundle(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);files=[]
   for name in ("artifact.bin","gate.txt"):
    p=root/name;p.write_bytes(b"real test fixture bytes");files.append(hashlib.sha256(p.read_bytes()).hexdigest())
   manifest={"model_name":"Core Prime","release_version":"0.1.0","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"artifact.bin","sha256":files[0]}],"gates":{k:{"status":"approved","evidence_path":"gate.txt","sha256":files[1]} for k in v.REQUIRED_GATES}}
   self.assertEqual(v.verify(root,manifest),[])
 def test_missing_gate_rejected(self):
  m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"a","sha256":"0"*64}],"gates":{}}
  errors=v.verify(Path("."),m);self.assertTrue(any("legal_review" in e for e in errors))
 def test_holdout_artifact_forbidden(self):
  m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"holdout-results.json","sha256":"0"*64}],"gates":{}}
  self.assertTrue(any("holdout artifact forbidden" in e for e in v.verify(Path("."),m)))
 def test_holdout_gate_evidence_path_rejected(self):\n  m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"a","sha256":"0"*64}],"gates":{k:{"status":"approved","evidence_path":"holdout-proof.json","sha256":"0"*64} for k in v.REQUIRED_GATES}}\n  self.assertTrue(any("holdout evidence forbidden" in e for e in v.verify(Path("."),m)))\n def test_path_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root.parent/"outside-cp-release-test";outside.write_bytes(b"test")
   try:
    with self.assertRaises(ValueError):v.verify_file(root,"../outside-cp-release-test",hashlib.sha256(b"test").hexdigest())
   finally:outside.unlink(missing_ok=True)
 def test_hash_mismatch(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"x").write_text("actual")
   with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):v.verify_file(root,"x","0"*64)
if __name__=="__main__":unittest.main()
