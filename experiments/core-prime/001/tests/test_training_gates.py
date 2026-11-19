import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("trainer",ROOT/"train_lora.py");trainer=importlib.util.module_from_spec(spec);spec.loader.exec_module(trainer)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.dataset=self.d/"train.jsonl";self.dataset.write_text(json.dumps({"task_id":"x","prompt":"p","response":"r","provenance":"authored","split":"train"})+"\n")
  self.x=type("X",(),{"dataset":self.dataset,"max_steps":10,"max_wall_seconds":60,"code_commit":"c"*40})();self.c={"status":"verified","output_training_permission":"verified","human_legal_review":"approved","compatibility_status":"compatible","revision":"a"*40};self.a={"approval":"approved","candidate_revision":"a"*40,"dataset_sha256":trainer.sha256_file(self.dataset),"code_commit":"c"*40,"hardware":{"verified_free_budget":True,"provider":"p","session_id":"s"},"budget":{"max_steps":10,"max_wall_seconds":60},"holdout_access":"sealed"}
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
 def test_duplicate_ids_rejected(self):r={"task_id":"x","prompt":"p","response":"r","provenance":"a","split":"train"};self.dataset.write_text(json.dumps(r)+"\n"+json.dumps(r));self.assertRaisesRegex(ValueError,"duplicate",trainer.load_rows,self.dataset)
 def test_telemetry_run_cumulative_accounting(self):
  rows=[{"run_id":"r1","session_elapsed_seconds":12},{"run_id":"r1","session_elapsed_seconds":8},{"run_id":"r2","session_elapsed_seconds":5}]
  self.assertEqual(trainer.telemetry_elapsed(rows),17)
 def test_telemetry_invalid_elapsed_rejected(self):
  with self.assertRaises(ValueError):trainer.telemetry_elapsed([{"run_id":"x","session_elapsed_seconds":float("nan")}])
 def test_telemetry_negative_elapsed_rejected(self):
  with self.assertRaises(ValueError):trainer.telemetry_elapsed([{"run_id":"x","session_elapsed_seconds":-1}])
 def test_checkpoint_validation(self):
  ck=self.d/"checkpoint-3";ck.mkdir();(ck/"trainer_state.json").write_text(json.dumps({"global_step":3}));(ck/"adapter_model.safetensors").write_bytes(b"weights");(ck/"optimizer.pt").write_bytes(b"opt");(ck/"scheduler.pt").write_bytes(b"sched");(ck/"rng_state.pth").write_bytes(b"rng")
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
 def test_runner_masks_prompt_and_validates_recovery(self):
  source=(ROOT/"train_lora.py").read_text(encoding="utf-8")
  self.assertIn("labels[i,:int(prefix_len)]=-100",source)
  self.assertIn("validate_checkpoint(resume)",source)
if __name__=="__main__":unittest.main()
