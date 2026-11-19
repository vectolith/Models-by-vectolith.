import json,subprocess,sys,tempfile,unittest,hashlib
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
EVALUATOR=ROOT/"evaluate.py"
spec=importlib.util.spec_from_file_location("evaluator",EVALUATOR);evaluator=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluator)
class HoldoutTests(unittest.TestCase):
 def test_frozen_manifest_exact_match_and_hash(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"tasks.jsonl";tasks.write_text('{"task_id":"a","prompt":"p","category":"c","split":"development"}'+chr(10),encoding="utf-8")
   manifest=Path(tmp)/"freeze.json";values={"model":"m","revision":"r","tasks_sha256":evaluator.sha256_file(tasks),"seed":7,"max_new_tokens":20,"temperature":0.0,"trust_remote_code":False,"qwen3_thinking":False,"limit":1,"selected_task_count":1,"selected_task_ids_sha256":evaluator.sha256_serialized(["a"]),"candidate_record_sha256":"c"*64,"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"max_wall_seconds":30}
   manifest.write_text(json.dumps(values),encoding="utf-8")
   digest=evaluator.verify_frozen_config(manifest,"m","r",tasks,7,20,0.0,False,False,1,["a"],"c"*64,"d"*40,"e"*64,30)
   self.assertEqual(digest,evaluator.sha256_file(manifest))
   with self.assertRaisesRegex(ValueError,"revision"):evaluator.verify_frozen_config(manifest,"m","other",tasks,7,20,0.0,False,False,1,["a"],"c"*64,"d"*40,"e"*64,30)
   with self.assertRaisesRegex(ValueError,"limit"):evaluator.verify_frozen_config(manifest,"m","r",tasks,7,20,0.0,False,False,0,["a"],"c"*64,"d"*40,"e"*64,30)
 def test_fallback_prompt_tokenization_matches_training_template(self):
  source=EVALUATOR.read_text(encoding="utf-8")
  self.assertIn('encoded=f"User:\n{prompt}\nAssistant:\n"',source)
  self.assertIn("add_special_tokens=False",source)
 def fixture_candidate(self,root):
  snapshot=root/"snapshot";snapshot.mkdir()
  files={"config.json":b"{}","chat_template.txt":b"template","weights.bin":b"weights"}
  inventory=[]
  for name,data in files.items():
   (snapshot/name).write_bytes(data);inventory.append({"path":"snapshot/"+name,"sha256":hashlib.sha256(data).hexdigest()})
  candidate={"record_version":"1","candidate_id":"test","repository_id":"m","revision":"a"*40,"status":"verified","license_identifier":"Apache-2.0","license_evidence_path":"license.txt","license_evidence_sha256":hashlib.sha256(b"license").hexdigest(),"output_training_permission":"verified","output_training_permission_evidence_path":"permission.txt","output_training_permission_evidence_sha256":hashlib.sha256(b"permission").hexdigest(),"human_legal_review":"approved","human_legal_review_evidence_path":"review.txt","human_legal_review_evidence_sha256":hashlib.sha256(b"review").hexdigest(),"model_config_evidence_path":"snapshot/config.json","model_config_sha256":hashlib.sha256(files["config.json"]).hexdigest(),"tokenizer_revision":"a"*40,"chat_template_evidence_path":"snapshot/chat_template.txt","chat_template_sha256":hashlib.sha256(files["chat_template.txt"]).hexdigest(),"model_snapshot_path":"snapshot","weight_inventory":inventory,"compatibility_status":"compatible"}
  for name,data in (("license.txt",b"license"),("permission.txt",b"permission"),("review.txt",b"review")):(root/name).write_bytes(data)
  path=root/"candidate.json";path.write_text(json.dumps(candidate),encoding="utf-8")
  return path,candidate
 def test_candidate_snapshot_integrity_and_permission(self):
  with tempfile.TemporaryDirectory() as tmp:
   path,candidate=self.fixture_candidate(Path(tmp))
   record,digest,snapshot=evaluator.evaluation_gate.verify_candidate_record(path,"m","a"*40)
   self.assertEqual(record,candidate);self.assertEqual(digest,evaluator.evaluation_gate.sha256_file(path));self.assertTrue(snapshot.is_dir())
   candidate["output_training_permission"]="pending";path.write_text(json.dumps(candidate))
   with self.assertRaisesRegex(ValueError,"permission gate"):evaluator.evaluation_gate.verify_candidate_record(path,"m","a"*40)
 def test_candidate_snapshot_inventory_mismatch(self):
  with tempfile.TemporaryDirectory() as tmp:
   path,candidate=self.fixture_candidate(Path(tmp));(Path(tmp)/"snapshot"/"extra.bin").write_bytes(b"extra")
   with self.assertRaisesRegex(ValueError,"inventory incomplete"):evaluator.evaluation_gate.verify_candidate_record(path,"m","a"*40)
 def test_evaluation_authorization_binds_freeze_and_environment(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tasks=root/"tasks.jsonl";tasks.write_text('{"task_id":"a","prompt":"p","category":"c","split":"development"}'+chr(10),encoding="utf-8")
   freeze=root/"freeze.json";freeze.write_text("freeze",encoding="utf-8")
   compute=root/"compute.json";compute.write_text("free",encoding="utf-8")
   auth={"approval":"approved","candidate_record_sha256":"c"*64,"candidate_revision":"a"*40,"tasks_sha256":evaluator.sha256_file(tasks),"freeze_manifest_sha256":evaluator.sha256_file(freeze),"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"hardware":{"verified_free_budget":True,"provider":"free","session_id":"s","evidence_path":"compute.json","evidence_sha256":evaluator.sha256_file(compute)},"budget":{"max_task_count":1,"max_new_tokens":20,"max_wall_seconds":30},"holdout_access":"sealed"}
   authpath=root/"auth.json";authpath.write_text(json.dumps(auth),encoding="utf-8")
   result,digest=evaluator.evaluation_gate.verify_evaluation_authorization(authpath,"c"*64,tasks,freeze,"d"*40,"e"*64,1,20)
   self.assertEqual(result,auth);self.assertEqual(digest,evaluator.evaluation_gate.sha256_file(authpath))
   auth["approval"]="pending";authpath.write_text(json.dumps(auth))
   with self.assertRaisesRegex(ValueError,"not approved"):evaluator.evaluation_gate.verify_evaluation_authorization(authpath,"c"*64,tasks,freeze,"d"*40,"e"*64,1,20)
 def test_authorized_budget_overflow_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tasks=root/"tasks";tasks.write_text("task",encoding="utf-8");freeze=root/"freeze";freeze.write_text("freeze")
   compute=root/"compute";compute.write_text("free")
   auth={"approval":"approved","candidate_record_sha256":"c"*64,"candidate_revision":"a"*40,"tasks_sha256":evaluator.evaluation_gate.sha256_file(tasks),"freeze_manifest_sha256":evaluator.evaluation_gate.sha256_file(freeze),"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"hardware":{"verified_free_budget":True,"provider":"free","session_id":"s","evidence_path":"compute","evidence_sha256":evaluator.evaluation_gate.sha256_file(compute)},"budget":{"max_task_count":1,"max_new_tokens":20,"max_wall_seconds":30},"holdout_access":"sealed"}
   path=root/"auth";path.write_text(json.dumps(auth))
   with self.assertRaisesRegex(ValueError,"selected tasks exceed"):evaluator.evaluation_gate.verify_evaluation_authorization(path,"c"*64,tasks,freeze,"d"*40,"e"*64,2,20)
 def test_holdout_rejected_even_with_deprecated_flag(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"holdout.jsonl";tasks.write_text(json.dumps({"task_id":"h1","prompt":"private","category":"test","split":"holdout"})+chr(10),encoding="utf-8")
   code=evaluator.evaluation_gate.git_head()
   result=subprocess.run([sys.executable,str(EVALUATOR),"--model","unused","--revision","unused","--tasks",str(tasks),"--output",str(Path(tmp)/"out"),"--freeze-manifest",str(Path(tmp)/"freeze.json"),"--candidate-record",str(Path(tmp)/"candidate.json"),"--authorization",str(Path(tmp)/"auth.json"),"--code-commit",code,"--allow-holdout"],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn("holdout inference blocked",result.stderr);self.assertFalse((Path(tmp)/"out").exists())
 def test_train_split_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"train.jsonl";tasks.write_text(json.dumps({"task_id":"t","prompt":"p","category":"c","split":"train"})+chr(10),encoding="utf-8")
   code=evaluator.evaluation_gate.git_head()
   result=subprocess.run([sys.executable,str(EVALUATOR),"--model","unused","--revision","unused","--tasks",str(tasks),"--output",str(Path(tmp)/"out"),"--freeze-manifest",str(Path(tmp)/"freeze.json"),"--candidate-record",str(Path(tmp)/"candidate.json"),"--authorization",str(Path(tmp)/"auth.json"),"--code-commit",code],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn("development-only",result.stderr);self.assertFalse((Path(tmp)/"out").exists())
if __name__=="__main__":unittest.main()
