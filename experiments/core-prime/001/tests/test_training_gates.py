import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("trainer",ROOT/"train_lora.py");trainer=importlib.util.module_from_spec(spec);spec.loader.exec_module(trainer)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.dataset=self.d/"train.jsonl";self.dataset.write_text(json.dumps({"task_id":"x","prompt":"p","response":"r","provenance":"authored","split":"train"})+"\n")
  self.candidate_path=self.d/"candidate.json";self.authorization_path=self.d/"authorization.json"
  self.x=type("X",(),{"dataset":self.dataset,"candidate":self.candidate_path,"authorization":self.authorization_path,"max_steps":10,"max_wall_seconds":60,"code_commit":"c"*40})()
  self.c={"status":"verified","output_training_permission":"verified","human_legal_review":"approved","compatibility_status":"compatible","revision":"a"*40,"license_identifier":"Apache-2.0","tokenizer_revision":"a"*40,"weight_inventory":[{"path":"weights.bin","sha256":"f"*64}]}
  for path_key,hash_key,filename,content in (("license_evidence_path","license_evidence_sha256","license.txt","license fixture"),("output_training_permission_evidence_path","output_training_permission_evidence_sha256","permission.txt","permission fixture"),("human_legal_review_evidence_path","human_legal_review_evidence_sha256","review.txt","review fixture"),("model_config_evidence_path","model_config_sha256","config.json","config fixture"),("chat_template_evidence_path","chat_template_sha256","template.txt","template fixture")):
   path=self.d/filename;path.write_text(content);self.c[path_key]=filename;self.c[hash_key]=trainer.sha256_file(path)
  compute=self.d/"compute.json";compute.write_text("compute fixture")
  provenance=self.d/"provenance.json";provenance.write_text("provenance fixture")
  self.a={"approval":"approved","candidate_revision":"a"*40,"dataset_sha256":trainer.sha256_file(self.dataset),"code_commit":"c"*40,"hardware":{"verified_free_budget":True,"provider":"p","session_id":"s","evidence_path":"compute.json","evidence_sha256":trainer.sha256_file(compute)},"dataset_provenance":{"status":"reviewed","evidence_path":"provenance.json","evidence_sha256":trainer.sha256_file(provenance)},"budget":{"max_steps":10,"max_wall_seconds":60},"holdout_access":"sealed"}
 def tearDown(self):self.tmp.cleanup()
 def test_all_gates_pass(self):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_pending_permission_blocked(self):self.c["output_training_permission"]="pending";self.assertRaisesRegex(ValueError,"output_training_permission",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_legal_review_blocked(self):self.c["human_legal_review"]="pending";self.assertRaisesRegex(ValueError,"human_legal_review",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_dataset_hash_blocked(self):self.a["dataset_sha256"]="0"*64;self.assertRaisesRegex(ValueError,"dataset hash",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_code_hash_blocked(self):self.a["code_commit"]="d"*40;self.assertRaisesRegex(ValueError,"code commit",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_free_compute_blocked(self):self.a["hardware"]["verified_free_budget"]=False;self.assertRaisesRegex(ValueError,"free compute",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_budget_limit(self):self.x.max_steps=11;self.assertRaisesRegex(ValueError,"max_steps",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_holdout_access_blocked(self):self.a["holdout_access"]="open";self.assertRaisesRegex(ValueError,"holdout",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_dev_split_rejected(self):self.dataset.write_text(json.dumps({"task_id":"x","prompt":"p","response":"r","provenance":"authored","split":"development"}));self.assertRaisesRegex(ValueError,"split must be train",trainer.load_rows,self.dataset)
 def test_empty_data_rejected(self):self.dataset.write_text("");self.assertRaisesRegex(ValueError,"empty",trainer.load_rows,self.dataset)
 def test_candidate_evidence_hash_mismatch(self):
  (self.d/"license.txt").write_text("tampered")
  with self.assertRaisesRegex(ValueError,"license evidence hash mismatch"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_compute_evidence_missing(self):
  (self.d/"compute.json").unlink()
  with self.assertRaisesRegex(ValueError,"free compute evidence file missing"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_dataset_provenance_missing(self):
  (self.d/"provenance.json").unlink()
  with self.assertRaisesRegex(ValueError,"dataset provenance evidence file missing"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_duplicate_ids_rejected(self):r={"task_id":"x","prompt":"p","response":"r","provenance":"a","split":"train"};self.dataset.write_text(json.dumps(r)+"\n"+json.dumps(r));self.assertRaisesRegex(ValueError,"duplicate",trainer.load_rows,self.dataset)
 def test_telemetry_run_cumulative_accounting(self):
  rows=[{"run_id":"r1","session_elapsed_seconds":12},{"run_id":"r1","session_elapsed_seconds":8},{"run_id":"r2","session_elapsed_seconds":5}]
  self.assertEqual(trainer.telemetry_elapsed(rows),17)
 def test_telemetry_invalid_elapsed_rejected(self):
  with self.assertRaises(ValueError):trainer.telemetry_elapsed([{"run_id":"x","session_elapsed_seconds":float("nan")}])
 def test_telemetry_negative_elapsed_rejected(self):
  with self.assertRaises(ValueError):trainer.telemetry_elapsed([{"run_id":"x","session_elapsed_seconds":-1}])
 def make_checkpoint(self,root,name,step):
  ck=root/name;ck.mkdir()
  (ck/"trainer_state.json").write_text(json.dumps({"global_step":step}))
  (ck/"adapter_model.safetensors").write_bytes(b"weights")
  (ck/"optimizer.pt").write_bytes(b"opt");(ck/"scheduler.pt").write_bytes(b"sched");(ck/"rng_state.pth").write_bytes(b"rng")
  trainer.seal_checkpoint(ck)
  return ck
 def test_recovery_selection_falls_back_to_valid_checkpoint(self):
  root=self.d/"checkpoints";root.mkdir()
  good=self.make_checkpoint(root,"checkpoint-2",2)
  bad=root/"checkpoint-9";bad.mkdir()
  (bad/"trainer_state.json").write_text(json.dumps({"global_step":9}))
  (bad/"adapter_model.safetensors").write_bytes(b"weights")
  self.assertEqual(trainer.select_recovery_checkpoint(root),good)
 def test_recovery_ignores_malformed_checkpoint_names(self):
  root=self.d/"checkpoints";root.mkdir()
  good=self.make_checkpoint(root,"checkpoint-2",2)
  (root/"checkpoint-not-a-step").mkdir()
  (root/"checkpoint-").mkdir()
  self.assertEqual(trainer.select_recovery_checkpoint(root),good)
 def test_checkpoint_validation(self):
  ck=self.make_checkpoint(self.d,"checkpoint-3",3)
  self.assertEqual(trainer.validate_checkpoint(ck),3)
 def test_checkpoint_step_mismatch(self):
  ck=self.d/"checkpoint-3";ck.mkdir();(ck/"trainer_state.json").write_text(json.dumps({"global_step":2}));(ck/"adapter_model.safetensors").write_bytes(b"weights")
  with self.assertRaisesRegex(ValueError,"step mismatch"):trainer.validate_checkpoint(ck)
 def test_checkpoint_missing_weights_rejected(self):
  ck=self.d/"checkpoint-3";ck.mkdir();(ck/"trainer_state.json").write_text(json.dumps({"global_step":3}))
  with self.assertRaisesRegex(ValueError,"weights missing"):trainer.validate_checkpoint(ck)
 def test_checkpoint_requires_optimizer_scheduler_rng(self):
  ck=self.d/"checkpoint-4";ck.mkdir();(ck/"trainer_state.json").write_text(json.dumps({"global_step":4}));(ck/"adapter_model.safetensors").write_bytes(b"weights")
  with self.assertRaisesRegex(ValueError,"optimizer.pt"):trainer.validate_checkpoint(ck)
 def test_checkpoint_hash_tamper_rejected(self):
  ck=self.make_checkpoint(self.d,"checkpoint-5",5)
  (ck/"optimizer.pt").write_bytes(b"tampered")
  with self.assertRaisesRegex(ValueError,"integrity hash mismatch"):trainer.validate_checkpoint(ck)
 def test_checkpoint_manifest_required(self):
  ck=self.d/"checkpoint-6";ck.mkdir();(ck/"trainer_state.json").write_text(json.dumps({"global_step":6}));(ck/"adapter_model.safetensors").write_bytes(b"weights");(ck/"optimizer.pt").write_bytes(b"opt");(ck/"scheduler.pt").write_bytes(b"sched");(ck/"rng_state.pth").write_bytes(b"rng")
  with self.assertRaisesRegex(ValueError,"manifest missing"):trainer.validate_checkpoint(ck)
 def test_runner_masks_prompt_and_validates_recovery(self):
  source=(ROOT/"train_lora.py").read_text(encoding="utf-8")
  self.assertIn("labels[i,:int(prefix_len)]=-100",source)
  self.assertIn("select_recovery_checkpoint",source)
 def test_wall_budget_stop_requests_checkpoint(self):
  source=(ROOT/"train_lora.py").read_text(encoding="utf-8")
  self.assertIn("control.should_training_stop=True",source)
  self.assertIn("control.should_save=True",source)
  self.assertIn("run_started_monotonic",source)
  self.assertIn("def on_save",source)
  self.assertIn("seal_checkpoint(checkpoint)",source)
 def test_build_sequence_masks_prefix_boundary(self):
  class Tok:
   eos_token="<eos>"
   def __call__(self,text,add_special_tokens=True):
    parts=text.split()
    if add_special_tokens:parts=["<s>"]+parts
    return {"input_ids":parts}
  ids,prefix=trainer.build_sequence(Tok(),"prompt words","answer words",max_length=30)
  self.assertEqual(ids[prefix:],["answer","words<eos>"])
  self.assertGreater(prefix,0)
 def test_build_sequence_rejects_truncated_response(self):
  class Tok:
   eos_token="<eos>"
   def __call__(self,text,add_special_tokens=True):return {"input_ids":text.split()}
  with self.assertRaisesRegex(ValueError,"no response tokens"):trainer.build_sequence(Tok(),"very long prefix words","answer",max_length=3)
if __name__=="__main__":unittest.main()
