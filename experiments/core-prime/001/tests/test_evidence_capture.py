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

 def test_snapshot_capture_rejects_empty(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"snapshot").mkdir();record=root/"candidate.json";record.write_text(json.dumps({"model_snapshot_path":"snapshot"}))
   with self.assertRaisesRegex(ValueError,"empty"):snapshot.capture(record)
if __name__=="__main__":unittest.main()
