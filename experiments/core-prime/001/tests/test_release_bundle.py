import importlib.util, tempfile, hashlib, unittest, os, tracemalloc
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
   m={"model_name":"Core Prime","release_version":"x","release_status":"qualified","holdout_included":False,"artifacts":[{"path":"artifact.bin","sha256":digest},{"path":"artifact.bin","sha256":digest}],"gates":gates}
   self.assertTrue(any("duplicate artifact file" in e for e in v.verify(root,m)))

 def test_symlink_evidence_path_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root/"outside.txt";outside.write_text("evidence");link=root/"link.txt";link.symlink_to(outside)
   with self.assertRaisesRegex(ValueError,"symlink components"):v.verify_file(root,"link.txt",hashlib.sha256(b"evidence").hexdigest())


 def test_symlink_parent_component_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root/"outside";outside.mkdir();(outside/"evidence.txt").write_text("evidence")
   link=root/"linked-dir";link.symlink_to(outside,target_is_directory=True)
   with self.assertRaisesRegex(ValueError,"symlink components"):v.verify_file(root,"linked-dir/evidence.txt",hashlib.sha256(b"evidence").hexdigest())
 def test_directory_as_evidence_file_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"dir").mkdir()
   with self.assertRaisesRegex(ValueError,"not regular"):v.verify_file(root,"dir",hashlib.sha256(b"").hexdigest())

 def test_duplicate_manifest_keys_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);manifest=root/"release.json";manifest.write_text('{"model_name":"Core Prime","model_name":"Other"}')
   with self.assertRaisesRegex(ValueError,"duplicate JSON object key"):v.evaluation_gate.strict_json_loads(manifest.read_text())
 def test_large_evidence_hashing_has_bounded_memory(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/"large.bin";chunk=b"x"*(1024*1024);expected=hashlib.sha256()
   with path.open("wb") as f:
    for _ in range(16):
     f.write(chunk);expected.update(chunk)
   tracemalloc.start()
   try:
    v.verify_file(root,path.name,expected.hexdigest())
    _,peak=tracemalloc.get_traced_memory()
   finally:
    tracemalloc.stop()
   self.assertLess(peak,8*1024*1024,"release verifier retained whole-file data in memory")

 @unittest.skipUnless(hasattr(os,"mkfifo"),"FIFO tests require POSIX")
 def test_fifo_evidence_is_rejected_without_blocking(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);fifo=root/"evidence.fifo";os.mkfifo(fifo)
   with self.assertRaisesRegex(ValueError,"not regular"):
    v.verify_file(root,fifo.name,hashlib.sha256(b"").hexdigest())

 def test_verified_path_return_is_rooted_without_re_resolving(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/"evidence.txt";path.write_bytes(b"verified")
   result=v.verify_file(root,path.name,hashlib.sha256(b"verified").hexdigest())
   self.assertEqual(result,root.resolve()/path.name)
 def test_hash_mismatch(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"x").write_text("actual")
   with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):v.verify_file(root,"x","0"*64)
if __name__=="__main__":unittest.main()
