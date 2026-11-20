import importlib.util, tempfile, hashlib, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_verifier",ROOT/"verify_release_bundle.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class ReleaseVerifierTests(unittest.TestCase):
 def test_complete_integrity_bundle(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);artifact=root/"artifact.bin";artifact.write_bytes(b"real test fixture bytes")
   gates={}
   for name in v.REQUIRED_GATES:
    path=root/(name+".txt");path.write_bytes(("evidence "+name).encode());digest=hashlib.sha256(path.read_bytes()).hexdigest()
    gates[name]={"status":"approved","evidence_path":path.name,"sha256":digest}
   manifest={"model_name":"Core Prime","release_version":"0.1.0","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"artifact.bin","sha256":hashlib.sha256(artifact.read_bytes()).hexdigest()}],"gates":gates}
   self.assertEqual(v.verify(root,manifest),[])
 def test_missing_gate_rejected(self):
  m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"a","sha256":"0"*64}],"gates":{}}
  self.assertTrue(any("legal_review" in e for e in v.verify(Path("."),m)))
 def test_holdout_artifact_forbidden(self):
  m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"holdout-results.json","sha256":"0"*64}],"gates":{}}
  self.assertTrue(any("holdout artifact forbidden" in e for e in v.verify(Path("."),m)))
 def test_holdout_gate_evidence_path_rejected(self):
  m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"a","sha256":"0"*64}],"gates":{k:{"status":"approved","evidence_path":"holdout-proof.json","sha256":"0"*64} for k in v.REQUIRED_GATES}}
  self.assertTrue(any("holdout evidence forbidden" in e for e in v.verify(Path("."),m)))
 def test_path_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root.parent/"outside-cp-release-test";outside.write_bytes(b"test")
   try:
    with self.assertRaises(ValueError):v.verify_file(root,"../outside-cp-release-test",hashlib.sha256(b"test").hexdigest())
   finally:outside.unlink(missing_ok=True)
 def test_gate_path_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root.parent/"outside-gate-cp-test";outside.write_bytes(b"test")
   try:
    with self.assertRaises(ValueError):v.verify_file(root,"../outside-gate-cp-test",hashlib.sha256(b"test").hexdigest())
   finally:outside.unlink(missing_ok=True)
 def test_duplicate_gate_evidence_path_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);gate=root/"gate.txt";gate.write_text("evidence");digest=hashlib.sha256(gate.read_bytes()).hexdigest()
   m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"gate.txt","sha256":digest}],"gates":{k:{"status":"approved","evidence_path":"gate.txt","sha256":digest} for k in v.REQUIRED_GATES}}
   self.assertTrue(any("duplicate gate evidence file" in e for e in v.verify(root,m)))
 def test_duplicate_gate_evidence_alias_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"sub").mkdir();gate=root/"gate.txt";gate.write_text("evidence");digest=hashlib.sha256(gate.read_bytes()).hexdigest()
   gates={k:{"status":"approved","evidence_path":"gate.txt","sha256":digest} for k in v.REQUIRED_GATES}
   gates["data_provenance"]["evidence_path"]="sub/../gate.txt"
   m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"gate.txt","sha256":digest}],"gates":gates}
   self.assertTrue(any("duplicate gate evidence file" in e for e in v.verify(root,m)))
 def test_duplicate_artifact_alias_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"sub").mkdir();artifact=root/"artifact.bin";artifact.write_bytes(b"artifact");digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
   gates={}
   for name in v.REQUIRED_GATES:
    p=root/(name+".txt");p.write_text(name);gates[name]={"status":"approved","evidence_path":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
   m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"artifact.bin","sha256":digest},{"path":"sub/../artifact.bin","sha256":digest}],"gates":gates}
   self.assertTrue(any("duplicate artifact file" in e for e in v.verify(root,m)))
 def test_hash_mismatch(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"x").write_text("actual")
   with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):v.verify_file(root,"x","0"*64)
if __name__=="__main__":unittest.main()
