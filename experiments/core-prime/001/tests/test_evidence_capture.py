import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
env=load("capture_environment",ROOT/"capture_environment.py")
snapshot=load("capture_snapshot_inventory",ROOT/"capture_snapshot_inventory.py")
class CaptureTests(unittest.TestCase):
 def test_environment_capture_has_git_and_package_hash(self):
  data=env.capture()
  self.assertEqual(data["git_head"],env.evaluation_gate.git_head())
  self.assertEqual(data["package_inventory_sha256"],env.evaluation_gate.sha256_serialized(data["package_inventory"]))
  self.assertIn("no ML runtime imports",data["scope"])
 def test_snapshot_capture_hashes_real_files(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);snap=root/"snapshot";snap.mkdir();(snap/"config.json").write_text("{}");(snap/"weights.bin").write_bytes(b"weights")
   record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"snapshot"}))
   result=snapshot.capture(record)
   self.assertEqual(len(result["inventory"]),2)
   self.assertEqual(result["inventory_sha256"],snapshot.evaluation_gate.sha256_serialized(result["inventory"]))
   self.assertTrue(all(len(item["sha256"])==64 for item in result["inventory"]))
 def test_snapshot_inventory_hash_binds_candidate_bytes_parsed(self):
  from unittest.mock import patch
  import hashlib
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);snap=root/"snapshot";snap.mkdir();(snap/"config.json").write_text("{}")
   record=root/"candidate.json";original=json.dumps({"model_snapshot_path":"snapshot"}).encode("utf-8");record.write_bytes(original)
   original_hash=hashlib.sha256(original).hexdigest();real_hash=snapshot.evaluation_gate.sha256_file;changed=False
   def mutate_after_parse(path):
    nonlocal changed
    if not changed:
     changed=True;record.write_text(json.dumps({"model_snapshot_path":"changed-path"}),encoding="utf-8")
    return real_hash(path)
   with patch.object(snapshot.evaluation_gate,"sha256_file",side_effect=mutate_after_parse):
    result=snapshot.capture(record)
   self.assertTrue(changed)
   self.assertEqual(result["candidate_record_sha256"],original_hash)
 def test_snapshot_capture_rejects_path_escape(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"../outside"}))
   with self.assertRaisesRegex(ValueError,"relative and confined"):snapshot.capture(record)

 def test_snapshot_capture_rejects_snapshot_root_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root/"outside";outside.mkdir();(outside/"weights.bin").write_bytes(b"weights")
   link=root/"snapshot-link";link.symlink_to(outside,target_is_directory=True)
   record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"snapshot-link"}))
   with self.assertRaisesRegex(ValueError,"symlink components"):snapshot.capture(record)

 def test_environment_evidence_atomic_cli_output(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/"environment.json"
   with patch.object(sys,"argv",["capture_environment.py","--output",str(out)]):env.main()
   parsed=json.loads(out.read_text(encoding="utf-8"))
   self.assertEqual(parsed["package_inventory_sha256"],env.evaluation_gate.sha256_serialized(parsed["package_inventory"]))
   self.assertEqual(list(out.parent.glob(out.name+".*.tmp")),[])
 def test_snapshot_inventory_atomic_cli_output(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);snap=root/"snapshot";snap.mkdir();(snap/"config.json").write_text("{}")
   record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"snapshot"}))
   out=root/"inventory.json"
   with patch.object(sys,"argv",["capture_snapshot_inventory.py","--candidate-record",str(record),"--output",str(out)]):snapshot.main()
   parsed=json.loads(out.read_text(encoding="utf-8"))
   self.assertEqual(parsed["inventory_sha256"],snapshot.evaluation_gate.sha256_serialized(parsed["inventory"]))
   self.assertEqual(list(out.parent.glob(out.name+".*.tmp")),[])

 def test_directory_fsync_uses_directory_descriptor(self):
  import os,stat
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   def verify_fd(fd):self.assertTrue(stat.S_ISDIR(os.fstat(fd).st_mode))
   with patch.object(env.evaluation_gate.os,"fsync",side_effect=verify_fd) as sync:
    env.evaluation_gate.fsync_directory(Path(d))
   sync.assert_called_once()
 def test_capture_writers_sync_parent_directory_after_replace(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=root/"env.json"
   with patch.object(env.evaluation_gate,"fsync_directory",wraps=env.evaluation_gate.fsync_directory) as sync:
    env.atomic_write_json(out,{"captured":True})
   sync.assert_called_once_with(out.parent)
   snapshot_dir=root/"snapshot";snapshot_dir.mkdir();(snapshot_dir/"config.json").write_text("{}")
   record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"snapshot"}))
   inventory=root/"inventory.json"
   with patch.object(snapshot.evaluation_gate,"fsync_directory",wraps=snapshot.evaluation_gate.fsync_directory) as sync:
    snapshot.atomic_write_json(inventory,snapshot.capture(record))
   sync.assert_called_once_with(inventory.parent)

 def test_snapshot_capture_rejects_file_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);snap=root/"snapshot";snap.mkdir();outside=root/"outside.bin";outside.write_bytes(b"weights");link=snap/"weights.bin";link.symlink_to(outside)
   record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"snapshot"}),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"snapshot contains symlinks"):snapshot.capture(record)
 def test_snapshot_capture_rejects_empty(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"snapshot").mkdir();record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"snapshot"}))
   with self.assertRaisesRegex(ValueError,"empty"):snapshot.capture(record)
if __name__=="__main__":unittest.main()
