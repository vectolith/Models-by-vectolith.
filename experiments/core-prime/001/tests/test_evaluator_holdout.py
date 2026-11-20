import json,subprocess,sys,tempfile,unittest,hashlib
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def task_record(task_id,prompt,category="c",split="development"):
 return {"task_id":task_id,"prompt":prompt,"category":category,"split":split,"rubric_id":"fixture-rubric","provenance":"fixture task record"}
sys.path.insert(0,str(ROOT))
EVALUATOR=ROOT/"evaluate.py"
spec=importlib.util.spec_from_file_location("evaluator",EVALUATOR);evaluator=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluator)
class HoldoutTests(unittest.TestCase):
 def test_frozen_manifest_exact_match_and_hash(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"tasks.jsonl";tasks.write_text(json.dumps(task_record("a","p"))+chr(10),encoding="utf-8")
   manifest=Path(tmp)/"freeze.json";tasks_sha=evaluator.sha256_file(tasks);values={"model":"m","revision":"r","tasks_sha256":tasks_sha,"seed":7,"max_new_tokens":20,"temperature":0.0,"trust_remote_code":False,"qwen3_thinking":False,"limit":1,"selected_task_count":1,"selected_task_ids_sha256":evaluator.sha256_serialized(["a"]),"candidate_record_sha256":"c"*64,"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"max_wall_seconds":30}
   manifest.write_text(json.dumps(values),encoding="utf-8")
   digest=evaluator.verify_frozen_config(manifest,"m","r",tasks_sha,7,20,0.0,False,False,1,["a"],"c"*64,"d"*40,"e"*64,30)
   self.assertEqual(digest,evaluator.sha256_file(manifest))
   with self.assertRaisesRegex(ValueError,"revision"):evaluator.verify_frozen_config(manifest,"m","other",tasks_sha,7,20,0.0,False,False,1,["a"],"c"*64,"d"*40,"e"*64,30)
   with self.assertRaisesRegex(ValueError,"limit"):evaluator.verify_frozen_config(manifest,"m","r",tasks_sha,7,20,0.0,False,False,0,["a"],"c"*64,"d"*40,"e"*64,30)
 def test_freeze_manifest_snapshot_hash_remains_bound_after_file_change(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks_sha="f"*64;manifest=Path(tmp)/"freeze.json"
   values={"model":"m","revision":"r","tasks_sha256":tasks_sha,"seed":7,"max_new_tokens":20,"temperature":0.0,"trust_remote_code":False,"qwen3_thinking":False,"limit":1,"selected_task_count":1,"selected_task_ids_sha256":evaluator.sha256_serialized(["a"]),"candidate_record_sha256":"c"*64,"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"max_wall_seconds":30}
   original=json.dumps(values,sort_keys=True).encode("utf-8");manifest.write_bytes(original)
   parsed,digest=evaluator.evaluation_gate.load_json_snapshot(manifest,"freeze manifest")
   manifest.write_text(json.dumps({"changed":True}),encoding="utf-8")
   result=evaluator.verify_frozen_config(manifest,"m","r",tasks_sha,7,20,0.0,False,False,1,["a"],"c"*64,"d"*40,"e"*64,30,parsed,digest)
   self.assertEqual(result,hashlib.sha256(original).hexdigest())
 def test_task_snapshot_hash_is_bound_to_bytes_read(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"tasks.jsonl";original=json.dumps(task_record("a","p"))+chr(10);path.write_text(original,encoding="utf-8")
   rows,digest=evaluator.load_jsonl_snapshot(path)
   self.assertEqual(rows[0]["task_id"],"a")
   self.assertEqual(digest,hashlib.sha256(original.encode("utf-8")).hexdigest())
   path.write_text('{"task_id":"b","prompt":"changed","category":"c","split":"development"}'+chr(10),encoding="utf-8")
   self.assertEqual(digest,hashlib.sha256(original.encode("utf-8")).hexdigest())

 def test_task_schema_requires_provenance_and_rubric(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"tasks.jsonl";row=task_record("x","p");row.pop("provenance");path.write_text(json.dumps(row)+chr(10),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"invalid provenance"):evaluator.load_jsonl_snapshot(path)
   row=task_record("x","p");row.pop("rubric_id");path.write_text(json.dumps(row)+chr(10),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"invalid rubric_id"):evaluator.load_jsonl_snapshot(path)
 def test_task_schema_rejects_unknown_fields(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"tasks.jsonl";row=task_record("x","p");row["unreviewed"]="value";path.write_text(json.dumps(row)+chr(10),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"unexpected task fields"):evaluator.load_jsonl_snapshot(path)
 def test_prompt_hash_validated_when_present(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"tasks.jsonl";row=task_record("x","p");row["content_sha256"]=hashlib.sha256(b"p").hexdigest();path.write_text(json.dumps(row)+chr(10),encoding="utf-8")
   evaluator.load_jsonl_snapshot(path)
   row["content_sha256"]="0"*64;path.write_text(json.dumps(row)+chr(10),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"content_sha256 mismatch"):evaluator.load_jsonl_snapshot(path)
   row["content_sha256"]="invalid";path.write_text(json.dumps(row)+chr(10),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"lowercase SHA-256"):evaluator.load_jsonl_snapshot(path)
 def test_fallback_prompt_tokenization_matches_training_template(self):
  source=EVALUATOR.read_text(encoding="utf-8")
  self.assertIn('encoded=f"User:\\n{prompt}\\nAssistant:\\n"',source)
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

 def test_candidate_snapshot_root_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);outside=root/"outside";outside.mkdir()
   (outside/"config.json").write_bytes(b"{}")
   candidate={"model_snapshot_path":"snapshot-link","weight_inventory":[{"path":"snapshot-link/config.json","sha256":hashlib.sha256(b"{}").hexdigest()}]}
   link=root/"snapshot-link";link.symlink_to(outside,target_is_directory=True)
   record_path=root/"candidate.json";record_path.write_text(json.dumps(candidate),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"symlink components"):evaluator.evaluation_gate.verify_model_snapshot(candidate,record_path)

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
 def test_candidate_snapshot_duplicate_inventory_path_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   path,candidate=self.fixture_candidate(Path(tmp));candidate["weight_inventory"].append(candidate["weight_inventory"][0]);path.write_text(json.dumps(candidate))
   with self.assertRaisesRegex(ValueError,"duplicate path"):evaluator.evaluation_gate.verify_candidate_record(path,"m","a"*40)
 def test_evaluation_authorization_binds_freeze_and_environment(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tasks=root/"tasks.jsonl";tasks.write_text('{"task_id":"a","prompt":"p","category":"c","split":"development"}'+chr(10),encoding="utf-8")
   freeze=root/"freeze.json";freeze.write_text("freeze",encoding="utf-8")
   compute=root/"compute.json";compute.write_text("free",encoding="utf-8")
   provenance=root/"provenance.json";provenance.write_text("reviewed dev dataset provenance",encoding="utf-8")
   auth={"approval":"approved","candidate_record_sha256":"c"*64,"candidate_revision":"a"*40,"tasks_sha256":evaluator.sha256_file(tasks),"freeze_manifest_sha256":evaluator.sha256_file(freeze),"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"dataset_provenance":{"status":"reviewed","evidence_path":"provenance.json","evidence_sha256":evaluator.sha256_file(provenance)},"hardware":{"verified_free_budget":True,"provider":"free","session_id":"s","evidence_path":"compute.json","evidence_sha256":evaluator.sha256_file(compute)},"budget":{"max_task_count":1,"max_new_tokens":20,"max_wall_seconds":30},"holdout_access":"sealed"}
   authpath=root/"auth.json";authpath.write_text(json.dumps(auth),encoding="utf-8")
   result,digest=evaluator.evaluation_gate.verify_evaluation_authorization(authpath,"c"*64,evaluator.sha256_file(tasks),freeze,"d"*40,"e"*64,1,20)
   self.assertEqual(result,auth);self.assertEqual(digest,evaluator.evaluation_gate.sha256_file(authpath))
   auth["approval"]="pending";authpath.write_text(json.dumps(auth))
   with self.assertRaisesRegex(ValueError,"not approved"):evaluator.evaluation_gate.verify_evaluation_authorization(authpath,"c"*64,evaluator.sha256_file(tasks),freeze,"d"*40,"e"*64,1,20)
 def test_authorized_budget_overflow_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tasks=root/"tasks";tasks.write_text("task",encoding="utf-8");freeze=root/"freeze";freeze.write_text("freeze")
   compute=root/"compute";compute.write_text("free")
   provenance=root/"provenance";provenance.write_text("reviewed")
   auth={"approval":"approved","candidate_record_sha256":"c"*64,"candidate_revision":"a"*40,"tasks_sha256":evaluator.evaluation_gate.sha256_file(tasks),"freeze_manifest_sha256":evaluator.evaluation_gate.sha256_file(freeze),"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"dataset_provenance":{"status":"reviewed","evidence_path":"provenance","evidence_sha256":evaluator.sha256_file(provenance)},"hardware":{"verified_free_budget":True,"provider":"free","session_id":"s","evidence_path":"compute","evidence_sha256":evaluator.evaluation_gate.sha256_file(compute)},"budget":{"max_task_count":1,"max_new_tokens":20,"max_wall_seconds":30},"holdout_access":"sealed"}
   path=root/"auth";path.write_text(json.dumps(auth))
   with self.assertRaisesRegex(ValueError,"selected tasks exceed"):evaluator.evaluation_gate.verify_evaluation_authorization(path,"c"*64,evaluator.sha256_file(tasks),freeze,"d"*40,"e"*64,2,20)


 def test_evaluation_authorization_template_includes_pending_provenance_evidence(self):
  template=json.loads((ROOT/"evaluation-authorization.template.json").read_text(encoding="utf-8"))
  self.assertEqual(template["dataset_provenance"]["status"],"pending")
  self.assertIsNone(template["dataset_provenance"]["evidence_path"])
  self.assertIsNone(template["dataset_provenance"]["evidence_sha256"])
 def test_dataset_provenance_gate_requires_review_and_hash(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tasks=root/"tasks";tasks.write_text("tasks",encoding="utf-8");freeze=root/"freeze";freeze.write_text("freeze",encoding="utf-8")
   compute=root/"compute";compute.write_text("free",encoding="utf-8");provenance=root/"provenance";provenance.write_text("reviewed",encoding="utf-8")
   auth={"approval":"approved","candidate_record_sha256":"c"*64,"candidate_revision":"a"*40,"tasks_sha256":evaluator.sha256_file(tasks),"freeze_manifest_sha256":evaluator.sha256_file(freeze),"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"dataset_provenance":{"status":"pending","evidence_path":"provenance","evidence_sha256":evaluator.sha256_file(provenance)},"hardware":{"verified_free_budget":True,"provider":"free","session_id":"s","evidence_path":"compute","evidence_sha256":evaluator.sha256_file(compute)},"budget":{"max_task_count":1,"max_new_tokens":20,"max_wall_seconds":30},"holdout_access":"sealed"}
   path=root/"auth.json";path.write_text(json.dumps(auth),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"dataset provenance must be independently reviewed"):evaluator.evaluation_gate.verify_evaluation_authorization(path,"c"*64,evaluator.sha256_file(tasks),freeze,"d"*40,"e"*64,1,20)
   auth["dataset_provenance"]["status"]="reviewed";auth["dataset_provenance"]["evidence_sha256"]="0"*64;path.write_text(json.dumps(auth),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"dataset provenance evidence hash mismatch"):evaluator.evaluation_gate.verify_evaluation_authorization(path,"c"*64,evaluator.sha256_file(tasks),freeze,"d"*40,"e"*64,1,20)
 def test_dataset_provenance_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tasks=root/"tasks";tasks.write_text("tasks");freeze=root/"freeze";freeze.write_text("freeze");compute=root/"compute";compute.write_text("free");outside=root/"outside";outside.write_text("provenance");link=root/"linked-provenance";link.symlink_to(outside)
   auth={"approval":"approved","candidate_record_sha256":"c"*64,"candidate_revision":"a"*40,"tasks_sha256":evaluator.sha256_file(tasks),"freeze_manifest_sha256":evaluator.sha256_file(freeze),"code_commit":"d"*40,"package_inventory_sha256":"e"*64,"dataset_provenance":{"status":"reviewed","evidence_path":"linked-provenance","evidence_sha256":evaluator.sha256_file(outside)},"hardware":{"verified_free_budget":True,"provider":"free","session_id":"s","evidence_path":"compute","evidence_sha256":evaluator.sha256_file(compute)},"budget":{"max_task_count":1,"max_new_tokens":20,"max_wall_seconds":30},"holdout_access":"sealed"}
   path=root/"auth.json";path.write_text(json.dumps(auth),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"dataset provenance evidence path contains symlink components"):evaluator.evaluation_gate.verify_evaluation_authorization(path,"c"*64,evaluator.sha256_file(tasks),freeze,"d"*40,"e"*64,1,20)
 def test_holdout_rejected_even_with_deprecated_flag(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"holdout.jsonl";tasks.write_text(json.dumps(task_record("h1","private","test","holdout"))+chr(10),encoding="utf-8")
   code=evaluator.evaluation_gate.git_head()
   result=subprocess.run([sys.executable,str(EVALUATOR),"--model","unused","--revision","unused","--tasks",str(tasks),"--output",str(Path(tmp)/"out"),"--freeze-manifest",str(Path(tmp)/"freeze.json"),"--candidate-record",str(Path(tmp)/"candidate.json"),"--authorization",str(Path(tmp)/"auth.json"),"--code-commit",code,"--allow-holdout"],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn("holdout inference blocked",result.stderr);self.assertFalse((Path(tmp)/"out").exists())
 def test_wall_budget_uses_monotonic_clock(self):
  source=EVALUATOR.read_text(encoding="utf-8")
  self.assertIn("run_started_monotonic=time.monotonic()",source)
  self.assertIn("time.monotonic()-run_started_monotonic>=max_wall_seconds",source)
 def test_trust_remote_code_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"dev.jsonl";tasks.write_text(json.dumps(task_record("d","p"))+chr(10),encoding="utf-8")
   code=evaluator.evaluation_gate.git_head()
   result=subprocess.run([sys.executable,str(EVALUATOR),"--model","unused","--revision","unused","--tasks",str(tasks),"--output",str(Path(tmp)/"out"),"--freeze-manifest",str(Path(tmp)/"freeze.json"),"--candidate-record",str(Path(tmp)/"candidate.json"),"--authorization",str(Path(tmp)/"auth.json"),"--code-commit",code,"--trust-remote-code"],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn("trust-remote-code is forbidden",result.stderr);self.assertFalse((Path(tmp)/"out").exists())
 def test_train_split_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"train.jsonl";tasks.write_text(json.dumps(task_record("t","p","c","train"))+chr(10),encoding="utf-8")
   code=evaluator.evaluation_gate.git_head()
   result=subprocess.run([sys.executable,str(EVALUATOR),"--model","unused","--revision","unused","--tasks",str(tasks),"--output",str(Path(tmp)/"out"),"--freeze-manifest",str(Path(tmp)/"freeze.json"),"--candidate-record",str(Path(tmp)/"candidate.json"),"--authorization",str(Path(tmp)/"auth.json"),"--code-commit",code],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn("development-only",result.stderr);self.assertFalse((Path(tmp)/"out").exists())

 def test_qwen3_thinking_setting_matches_verified_snapshot_config(self):
  with tempfile.TemporaryDirectory() as tmp:
   snapshot=Path(tmp);helper=evaluator.validate_qwen3_thinking_mode
   with self.assertRaisesRegex(ValueError,"requires config.json"):helper(snapshot,True)
   config=snapshot/"config.json";config.write_text(json.dumps({"model_type":"qwen3"}),encoding="utf-8")
   helper(snapshot,True)
   config.write_text(json.dumps({"model_type":"llama"}),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"only supported for a verified Qwen3-family"):helper(snapshot,True)
   config.write_text("invalid json",encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"verified model config is invalid"):helper(snapshot,True)
 def test_qwen3_thinking_disabled_does_not_require_config(self):
  with tempfile.TemporaryDirectory() as tmp:evaluator.validate_qwen3_thinking_mode(Path(tmp),False)

 def test_candidate_evidence_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);outside=root/"outside.txt";outside.write_text("evidence");link=root/"link.txt";link.symlink_to(outside)
   with self.assertRaisesRegex(ValueError,"symlink components"):evaluator.evaluation_gate.verify_evidence_file(root,"link.txt",hashlib.sha256(b"evidence").hexdigest(),"fixture")

 def test_candidate_evidence_parent_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);outside=root/"outside";outside.mkdir();(outside/"evidence.txt").write_text("evidence");link=root/"linked-dir";link.symlink_to(outside,target_is_directory=True)
   with self.assertRaisesRegex(ValueError,"symlink components"):evaluator.evaluation_gate.verify_evidence_file(root,"linked-dir/evidence.txt",hashlib.sha256(b"evidence").hexdigest(),"fixture")

if __name__=="__main__":unittest.main()
