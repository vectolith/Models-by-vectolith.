import importlib.util,json,tempfile,unittest,os,subprocess
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("trainer",ROOT/"train_lora.py");trainer=importlib.util.module_from_spec(spec);spec.loader.exec_module(trainer)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.dataset=self.d/"train.jsonl";self.dataset.write_text(json.dumps({"task_id":"x","prompt":"p","response":"r","provenance":"authored","split":"train"})+"\n")
  self.candidate_path=self.d/"candidate.json";self.authorization_path=self.d/"authorization.json"
  self.x=type("X",(),{"dataset":self.dataset,"candidate":self.candidate_path,"authorization":self.authorization_path,"max_steps":10,"max_wall_seconds":60,"rank":8,"alpha":16,"target_modules":"q_proj,k_proj,v_proj,o_proj","code_commit":"c"*40})()
  snapshot=self.d/"snapshot";snapshot.mkdir()
  weights=snapshot/"weights.bin";weights.write_bytes(b"candidate weight fixture")
  config=snapshot/"config.json";config.write_text("{}")
  template=snapshot/"chat_template.txt";template.write_text("template")
  inventory=[{"path":"snapshot/weights.bin","sha256":trainer.sha256_file(weights)},{"path":"snapshot/config.json","sha256":trainer.sha256_file(config)},{"path":"snapshot/chat_template.txt","sha256":trainer.sha256_file(template)}]
  self.c={"status":"verified","output_training_permission":"verified","human_legal_review":"approved","compatibility_status":"compatible","revision":"a"*40,"license_identifier":"Apache-2.0","tokenizer_revision":"a"*40,"model_snapshot_path":"snapshot","weight_inventory":inventory,"model_config_evidence_path":"snapshot/config.json","model_config_sha256":trainer.sha256_file(config),"chat_template_evidence_path":"snapshot/chat_template.txt","chat_template_sha256":trainer.sha256_file(template)}
  for path_key,hash_key,filename,content in (("license_evidence_path","license_evidence_sha256","license.txt","license fixture"),("output_training_permission_evidence_path","output_training_permission_evidence_sha256","permission.txt","permission fixture"),("human_legal_review_evidence_path","human_legal_review_evidence_sha256","review.txt","review fixture")):
   path=self.d/filename;path.write_text(content);self.c[path_key]=filename;self.c[hash_key]=trainer.sha256_file(path)
  self.c["weight_inventory"]=[{"path":i["path"],"sha256":i["sha256"]} for i in inventory]
  self.candidate_path.write_text(json.dumps(self.c,sort_keys=True),encoding="utf-8")
  compute=self.d/"compute.json";compute.write_text("compute fixture")
  provenance=self.d/"provenance.json";provenance.write_text(json.dumps({"dataset_sha256":trainer.sha256_file(self.dataset),"review_status":"reviewed","reviewer":"independent-reviewer","review_scope":"training dataset provenance and rights review","reviewed_at_utc":"2026-11-20T08:00:00+00:00"}))
  self.a={"approval":"approved","candidate_revision":"a"*40,"candidate_record_sha256":trainer.sha256_file(self.candidate_path),"environment_package_inventory_sha256":trainer.package_inventory_sha256(),"dataset_sha256":trainer.sha256_file(self.dataset),"code_commit":"c"*40,"hardware":{"verified_free_budget":True,"provider":"p","session_id":"s","evidence_path":"compute.json","evidence_sha256":trainer.sha256_file(compute)},"dataset_provenance":{"status":"reviewed","evidence_path":"provenance.json","evidence_sha256":trainer.sha256_file(provenance)},"budget":{"max_steps":10,"max_wall_seconds":60},"training_config_sha256":trainer.training_config_sha256(self.x),"holdout_access":"sealed"}
 def tearDown(self):self.tmp.cleanup()

 def test_confined_reader_and_hash_reject_fifo_without_blocking(self):
  with tempfile.TemporaryDirectory() as d:
   fifo=Path(d)/"fifo";os.mkfifo(fifo)
   script="\n".join([
    "import sys",
    "sys.path.insert(0,sys.argv[1])",
    "import evaluation_gate",
    "for fn in (evaluation_gate.read_confined_bytes,evaluation_gate.hash_confined_file):",
    " try:",
    "  fn(sys.argv[2],'fifo','test')",
    " except ValueError as exc:",
    "  if 'not regular' not in str(exc): raise",
    " else:",
    "  raise AssertionError('FIFO accepted')",
   ])
   result=subprocess.run([sys.executable,"-c",script,str(ROOT),d],capture_output=True,text=True,timeout=3)
   self.assertEqual(result.returncode,0,result.stderr)
 def test_all_gates_pass(self):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_pending_permission_blocked(self):
  self.c["output_training_permission"]="pending";self.candidate_path.write_text(json.dumps(self.c,sort_keys=True));self.a["candidate_record_sha256"]=trainer.sha256_file(self.candidate_path)
  self.assertRaisesRegex(ValueError,"output-training permission",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_legal_review_blocked(self):
  self.c["human_legal_review"]="pending";self.candidate_path.write_text(json.dumps(self.c,sort_keys=True));self.a["candidate_record_sha256"]=trainer.sha256_file(self.candidate_path)
  self.assertRaisesRegex(ValueError,"independent human legal review",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)

 def test_dataset_authorization_binds_loaded_snapshot_bytes(self):
  rows,digest=trainer.load_rows_snapshot(self.dataset)
  self.dataset.write_text(json.dumps({"task_id":"changed","prompt":"changed","response":"changed","provenance":"changed","split":"train"})+"\n",encoding="utf-8")
  self.assertEqual(rows[0]["task_id"],"x")
  self.assertEqual(digest,self.a["dataset_sha256"])
  trainer.gates(self.c,self.a,rows,self.x,dataset_sha256=digest)

 def test_dataset_hash_blocked(self):self.a["dataset_sha256"]="0"*64;self.assertRaisesRegex(ValueError,"dataset hash",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_code_hash_blocked(self):self.a["code_commit"]="d"*40;self.assertRaisesRegex(ValueError,"code commit",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_free_compute_blocked(self):self.a["hardware"]["verified_free_budget"]=False;self.assertRaisesRegex(ValueError,"free compute",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_budget_limit(self):self.x.max_steps=11;self.a["training_config_sha256"]=trainer.training_config_sha256(self.x);self.assertRaisesRegex(ValueError,"max_steps",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_holdout_access_blocked(self):self.a["holdout_access"]="open";self.assertRaisesRegex(ValueError,"holdout",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_dev_split_rejected(self):self.dataset.write_text(json.dumps({"task_id":"x","prompt":"p","response":"r","provenance":"authored","split":"development"}));self.assertRaisesRegex(ValueError,"split must be train",trainer.load_rows,self.dataset)
 def test_training_dataset_unknown_fields_rejected(self):
  row={"task_id":"x","prompt":"p","response":"r","provenance":"authored","split":"train","extra":"unbound"}
  self.dataset.write_text(json.dumps(row)+"\n",encoding="utf-8")
  with self.assertRaisesRegex(ValueError,"unexpected training dataset fields"):trainer.load_rows(self.dataset)
 def test_training_dataset_response_must_be_nonempty_text(self):
  row={"task_id":"x","prompt":"p","response":"  ","provenance":"authored","split":"train"}
  self.dataset.write_text(json.dumps(row)+"\n",encoding="utf-8")
  with self.assertRaisesRegex(ValueError,"response required as non-empty text"):trainer.load_rows(self.dataset)
 def test_empty_data_rejected(self):self.dataset.write_text("");self.assertRaisesRegex(ValueError,"empty",trainer.load_rows,self.dataset)
 def test_candidate_evidence_hash_mismatch(self):
  (self.d/"license.txt").write_text("tampered")
  with self.assertRaisesRegex(ValueError,"license evidence hash mismatch"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_candidate_weight_hash_mismatch(self):
  (self.d/"snapshot"/"weights.bin").write_bytes(b"tampered candidate weight")
  with self.assertRaisesRegex(ValueError,"candidate snapshot evidence hash mismatch"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_candidate_weight_missing(self):
  (self.d/"snapshot"/"weights.bin").unlink()
  with self.assertRaisesRegex(ValueError,"candidate snapshot evidence file missing"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_snapshot_inventory_incomplete(self):
  (self.d/"snapshot"/"extra.bin").write_bytes(b"unlisted")
  with self.assertRaisesRegex(ValueError,"inventory incomplete"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_candidate_record_hash_mismatch(self):
  self.a["candidate_record_sha256"]="0"*64
  with self.assertRaisesRegex(ValueError,"candidate record hash mismatch"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_environment_package_inventory_mismatch(self):
  self.a["environment_package_inventory_sha256"]="0"*64
  with self.assertRaisesRegex(ValueError,"environment package inventory hash"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_compute_evidence_missing(self):
  (self.d/"compute.json").unlink()
  with self.assertRaisesRegex(ValueError,"free compute evidence file missing"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)

 def test_training_compute_evidence_uses_shared_confined_verifier(self):
  from unittest.mock import patch
  secure=trainer.evaluation_gate.verify_evidence_file
  with patch.object(trainer.evaluation_gate,"verify_evidence_file",wraps=secure) as verifier:
   trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
  self.assertTrue(any(call.args[3]=="free compute" for call in verifier.call_args_list))
 def test_dataset_provenance_evidence_dataset_hash_mismatch(self):
  provenance=self.d/"provenance.json";provenance.write_text(json.dumps({"dataset_sha256":"0"*64,"review_status":"reviewed","reviewer":"independent-reviewer","review_scope":"review","reviewed_at_utc":"2026-11-20T08:00:00+00:00"}))
  self.a["dataset_provenance"]["evidence_sha256"]=trainer.sha256_file(provenance)
  with self.assertRaisesRegex(ValueError,"dataset provenance evidence dataset SHA-256 mismatch"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_dataset_provenance_missing(self):
  (self.d/"provenance.json").unlink()
  with self.assertRaisesRegex(ValueError,"dataset provenance evidence file missing"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)

 def test_compute_evidence_symlink_rejected(self):
  (self.d/"compute.json").unlink()
  outside=self.d/"outside.json";outside.write_text("compute fixture")
  (self.d/"compute.json").symlink_to(outside)
  self.a["hardware"]["evidence_sha256"]=trainer.sha256_file(outside)
  with self.assertRaisesRegex(ValueError,"free compute evidence path contains symlink components"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_provenance_evidence_symlink_directory_rejected(self):
  (self.d/"provenance.json").unlink()
  outside=self.d/"outside";outside.mkdir();(outside/"provenance.json").write_text("provenance fixture")
  (self.d/"provenance-dir").symlink_to(outside,target_is_directory=True)
  self.a["dataset_provenance"]["evidence_path"]="provenance-dir/provenance.json"
  self.a["dataset_provenance"]["evidence_sha256"]=trainer.sha256_file(outside/"provenance.json")
  with self.assertRaisesRegex(ValueError,"dataset provenance evidence path contains symlink components"):trainer.gates(self.c,self.a,trainer.load_rows(self.dataset),self.x)

 def test_duplicate_training_dataset_keys_rejected(self):
  self.dataset.write_text('{"task_id":"x","task_id":"y","prompt":"p","response":"r","provenance":"a","split":"train"}\n',encoding="utf-8")
  with self.assertRaisesRegex(ValueError,"duplicate JSON object key"):trainer.load_rows_snapshot(self.dataset)
 def test_duplicate_ids_rejected(self):r={"task_id":"x","prompt":"p","response":"r","provenance":"a","split":"train"};self.dataset.write_text(json.dumps(r)+"\n"+json.dumps(r));self.assertRaisesRegex(ValueError,"duplicate",trainer.load_rows,self.dataset)

 def test_training_config_hash_binds_cli_parameters(self):
  original=trainer.training_config_sha256(self.x)
  self.x.rank=16
  self.assertNotEqual(original,trainer.training_config_sha256(self.x))
  self.assertRaisesRegex(ValueError,"training config hash mismatch",trainer.gates,self.c,self.a,trainer.load_rows(self.dataset),self.x)
 def test_duplicate_training_target_modules_rejected(self):
  self.x.target_modules="q_proj,q_proj"
  self.assertRaisesRegex(ValueError,"target_modules must be unique",trainer.training_config,self.x)
 def test_training_package_inventory_snapshot_is_single_capture(self):
  from unittest.mock import patch
  items=[{"name":"fixture-package","version":"1.0"}]
  with patch.object(trainer,"package_inventory",return_value=items) as capture:
   inventory,digest=trainer.package_inventory_snapshot()
  self.assertEqual(inventory,items);self.assertEqual(digest,trainer.evaluation_gate.sha256_serialized(items));self.assertEqual(capture.call_count,1)
 def test_training_manifest_uses_preflight_package_snapshot(self):
  source=(ROOT/"train_lora.py").read_text(encoding="utf-8")
  self.assertIn('evaluation_gate.load_json_snapshot(x.candidate,"candidate record")',source)
  self.assertIn('evaluation_gate.load_json_snapshot(x.authorization,"training authorization")',source)
  self.assertIn("snapshot=gates(c,a,rows,x,packages_hash,training_config_hash,dataset_sha256,candidate_record_sha256)",source)
  self.assertIn('"candidate_record_sha256":candidate_record_sha256,"authorization_sha256":authorization_sha256',source)
  self.assertIn('"training_config":cfg,"training_config_sha256":training_config_hash',source)
  self.assertIn('"package_inventory":packages,"package_inventory_sha256":packages_hash,"environment_package_inventory_sha256":packages_hash',source)
 def test_telemetry_run_cumulative_accounting(self):
  rows=[{"run_id":"r1","session_elapsed_seconds":12},{"run_id":"r1","session_elapsed_seconds":8},{"run_id":"r2","session_elapsed_seconds":5}]
  self.assertEqual(trainer.telemetry_elapsed(rows),17)
 def test_telemetry_step_cumulative_accounting(self):
  rows=[{"run_id":"r1","start_global_step":0,"step":5},{"run_id":"r1","start_global_step":0,"step":4},{"run_id":"r2","start_global_step":5,"step":8},{"run_id":"r3","start_global_step":8,"step":10}]
  self.assertEqual(trainer.telemetry_steps(rows),10)
 def test_cumulative_step_budget_accounts_for_recovery(self):
  self.assertEqual(trainer.check_step_budget(5,10,5,10),10)
  with self.assertRaisesRegex(ValueError,"cumulative step budget exceeded"):trainer.check_step_budget(5,10,3,10)
  with self.assertRaisesRegex(ValueError,"target max_steps"):trainer.check_step_budget(5,5,5,10)
 def test_telemetry_step_start_mismatch_rejected(self):
  with self.assertRaisesRegex(ValueError,"disagree on start_global_step"):trainer.telemetry_steps([{"run_id":"r","start_global_step":0,"step":2},{"run_id":"r","start_global_step":1,"step":3}])
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
 def test_checkpoint_budget_write_does_not_follow_predictable_tmp_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ck=root/"checkpoint-1";ck.mkdir();outside=root/"outside.txt";outside.write_text("preserve",encoding="utf-8")
   (ck/"checkpoint-budget.json.tmp").symlink_to(outside)
   trainer.write_checkpoint_budget_state(ck,1,3.5)
   self.assertEqual(outside.read_text(encoding="utf-8"),"preserve")
   record=json.loads((ck/"checkpoint-budget.json").read_text(encoding="utf-8"))
   self.assertEqual(record["global_step"],1);self.assertEqual(record["cumulative_elapsed_seconds"],3.5)
   self.assertFalse(any(p.name.startswith("checkpoint-budget.json.") and p.name.endswith(".tmp") and p!=ck/"checkpoint-budget.json.tmp" for p in ck.iterdir()))
 def test_checkpoint_atomic_write_cleans_temp_on_replace_failure(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);target=root/"state.json";target.write_text("previous",encoding="utf-8")
   with patch.object(trainer.os,"replace",side_effect=OSError("forced replace failure")):
    with self.assertRaisesRegex(OSError,"forced replace failure"):trainer.atomic_write_text(target,"new")
   self.assertEqual(target.read_text(encoding="utf-8"),"previous")
   self.assertEqual(list(root.glob(target.name+".*.tmp")),[])
 def test_checkpoint_budget_state_and_recovery(self):
  ck=self.make_checkpoint(self.d,"checkpoint-3",3)
  trainer.seal_checkpoint(ck,cumulative_elapsed_seconds=42.5)
  steps,elapsed=trainer.recover_budget_from_checkpoint(0,0.0,ck)
  self.assertEqual(steps,3)
  self.assertEqual(elapsed,42.5)
  self.assertEqual(trainer.recover_budget_from_checkpoint(5,60.0,ck),(5,60.0))
 def test_checkpoint_budget_state_tamper_rejected(self):
  ck=self.make_checkpoint(self.d,"checkpoint-4",4)
  state=ck/"checkpoint-budget.json"
  record=json.loads(state.read_text())
  record["cumulative_elapsed_seconds"]=99.0
  state.write_text(json.dumps(record))
  with self.assertRaisesRegex(ValueError,"integrity hash mismatch"):trainer.validate_checkpoint(ck)
 def test_telemetry_append_fsyncs(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"telemetry.jsonl"
   with patch.object(trainer.os,"fsync") as sync:
    trainer.append_telemetry_record(path,{"run_id":"r","step":1})
    sync.assert_called_once()
   self.assertEqual(json.loads(path.read_text())["step"],1)
 def test_hash_confined_file_reads_in_bounded_chunks(self):
  from unittest.mock import patch
  import hashlib,os
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);data=b"x"*(2*1024*1024+17);path=root/"large.bin";path.write_bytes(data)
   original_read=os.read;observed=[]
   def recording_read(fd,size):
    observed.append(size)
    return original_read(fd,size)
   with patch.object(trainer.evaluation_gate.os,"read",side_effect=recording_read):
    target,digest,size=trainer.evaluation_gate.hash_confined_file(root,"large.bin","checkpoint",chunk_size=65536)
   self.assertEqual(target,path);self.assertEqual(digest,hashlib.sha256(data).hexdigest());self.assertEqual(size,len(data))
   self.assertTrue(observed);self.assertTrue(all(size==65536 for size in observed))

 def test_checkpoint_inventory_uses_confined_descriptor_reads(self):
  ck=self.make_checkpoint(self.d,"checkpoint-13",13)
  from unittest.mock import patch
  secure_read=trainer.evaluation_gate.read_confined_bytes
  secure_hash=trainer.evaluation_gate.hash_confined_file
  observed=[]
  def wrapped_read(base,relative,label):
   observed.append((Path(base),relative,label,"read"))
   return secure_read(base,relative,label)
  def wrapped_hash(base,relative,label,chunk_size=1024*1024):
   observed.append((Path(base),relative,label,"hash"))
   return secure_hash(base,relative,label,chunk_size)
  with patch.object(trainer.evaluation_gate,"read_confined_bytes",side_effect=wrapped_read),patch.object(trainer.evaluation_gate,"hash_confined_file",side_effect=wrapped_hash):
   inventory=trainer.checkpoint_inventory(ck)
  self.assertTrue(observed)
  self.assertTrue(all(label=="checkpoint" for _,_,label,_ in observed))
  self.assertTrue(any(relative.startswith(ck.name+"/") for _,relative,_,_ in observed))
  expected_count=len([p for p in ck.iterdir() if p.is_file() and p.name not in ("checkpoint-integrity.json","checkpoint-integrity.json.tmp","checkpoint-budget.json.tmp")])
  self.assertEqual(len(inventory),expected_count)

 def test_checkpoint_inventory_hashes_nested_control_named_payload(self):
  ck=self.make_checkpoint(self.d,"checkpoint-18",18)
  nested=ck/"nested";nested.mkdir()
  names=("checkpoint-integrity.json","checkpoint-integrity.json.tmp","checkpoint-budget.json.tmp")
  for name in names:(nested/name).write_bytes(("payload:"+name).encode("utf-8"))
  # Root control files/temp files are excluded; same-named nested payloads are not.
  for name in names:(ck/name).write_bytes(("root-control:"+name).encode("utf-8"))
  trainer.seal_checkpoint(ck)
  inventory=trainer.checkpoint_inventory(ck)
  inventory_paths={item["path"] for item in inventory}
  self.assertEqual({item["path"] for item in inventory if item["path"].startswith("nested/")},{ "nested/"+name for name in names })
  self.assertTrue(all(name not in inventory_paths for name in names))
  self.assertEqual(trainer.validate_checkpoint(ck),18)
  (nested/"checkpoint-integrity.json").write_bytes(b"tampered")
  with self.assertRaisesRegex(ValueError,"integrity hash mismatch: nested/checkpoint-integrity.json"):
   trainer.validate_checkpoint(ck)

 def test_checkpoint_inventory_rejects_symlink_swap_before_hash(self):
  ck=self.make_checkpoint(self.d,"checkpoint-14",14)
  target=ck/"trainer_state.json"
  outside=self.d/"outside.json";outside.write_text("outside",encoding="utf-8")
  secure_read=trainer.evaluation_gate.read_confined_bytes
  secure_hash=trainer.evaluation_gate.hash_confined_file
  swapped=False
  def swap():
   nonlocal swapped
   if not swapped:
    target.unlink()
    target.symlink_to(outside)
    swapped=True
  def swap_then_read(base,relative,label):
   if relative.endswith("/trainer_state.json"):swap()
   return secure_read(base,relative,label)
  def swap_then_hash(base,relative,label,chunk_size=1024*1024):
   if relative.endswith("/trainer_state.json"):swap()
   return secure_hash(base,relative,label,chunk_size)
  from unittest.mock import patch
  with patch.object(trainer.evaluation_gate,"read_confined_bytes",side_effect=swap_then_read),patch.object(trainer.evaluation_gate,"hash_confined_file",side_effect=swap_then_hash):
   with self.assertRaisesRegex(ValueError,"symlink components or is unreadable"):
    trainer.checkpoint_inventory(ck)
  self.assertTrue(swapped)

 def test_checkpoint_step_rejects_symlink_state(self):
  ck=self.make_checkpoint(self.d,"checkpoint-15",15)
  target=ck/"trainer_state.json";target.unlink()
  outside=self.d/"outside-state.json";outside.write_text(json.dumps({"global_step":15}),encoding="utf-8")
  target.symlink_to(outside)
  with self.assertRaisesRegex(ValueError,"symlink components or is unreadable"):
   trainer.checkpoint_step(ck)

 def test_checkpoint_budget_state_rejects_symlink(self):
  ck=self.make_checkpoint(self.d,"checkpoint-16",16)
  target=ck/"checkpoint-budget.json";target.unlink()
  outside=self.d/"outside-budget.json";outside.write_text(json.dumps({"schema_version":1,"global_step":16,"cumulative_elapsed_seconds":10}),encoding="utf-8")
  target.symlink_to(outside)
  with self.assertRaisesRegex(ValueError,"symlink components or is unreadable"):
   trainer.checkpoint_budget_state(ck)

 def test_checkpoint_integrity_manifest_rejects_symlink(self):
  ck=self.make_checkpoint(self.d,"checkpoint-17",17)
  target=ck/"checkpoint-integrity.json";target.unlink()
  outside=self.d/"outside-manifest.json";outside.write_text(json.dumps({"schema_version":1,"step":17,"files":[]}),encoding="utf-8")
  target.symlink_to(outside)
  with self.assertRaisesRegex(ValueError,"symlink components or is unreadable"):
   trainer.validate_checkpoint(ck)

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
 def test_checkpoint_symlink_file_rejected(self):
  ck=self.make_checkpoint(self.d,"checkpoint-11",11);outside=self.d/"outside.bin";outside.write_bytes(b"outside")
  target=ck/"adapter_model.safetensors";target.unlink();target.symlink_to(outside)
  with self.assertRaisesRegex(ValueError,"contains symlinks"):trainer.validate_checkpoint(ck)
 def test_checkpoint_directory_symlink_rejected(self):
  outside=self.d/"external";outside.mkdir();valid=self.make_checkpoint(outside,"checkpoint-12",12)
  root=self.d/"checkpoints";root.mkdir();link=root/"checkpoint-12";link.symlink_to(valid,target_is_directory=True)
  with self.assertRaisesRegex(ValueError,"directory symlink"):trainer.select_recovery_checkpoint(root)
 def test_checkpoint_manifest_duplicate_paths_rejected(self):
  ck=self.make_checkpoint(self.d,"checkpoint-7",7)
  manifest=json.loads((ck/"checkpoint-integrity.json").read_text())
  manifest["files"].append(manifest["files"][0])
  (ck/"checkpoint-integrity.json").write_text(json.dumps(manifest))
  with self.assertRaisesRegex(ValueError,"duplicate paths"):trainer.validate_checkpoint(ck)
 def test_checkpoint_manifest_malformed_entry_rejected(self):
  ck=self.make_checkpoint(self.d,"checkpoint-8",8)
  manifest=json.loads((ck/"checkpoint-integrity.json").read_text())
  manifest["files"][0]["sha256"]="invalid"
  (ck/"checkpoint-integrity.json").write_text(json.dumps(manifest))
  with self.assertRaisesRegex(ValueError,"entries malformed"):trainer.validate_checkpoint(ck)
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
  self.assertIn("seal_checkpoint(checkpoint,cumulative_elapsed_seconds=",source)
 def test_tokenizer_validation_requires_eos_and_padding_id(self):
  class MissingEOS:
   eos_token=None
   pad_token=None
   pad_token_id=None
  with self.assertRaisesRegex(ValueError,"EOS token"):trainer.validate_tokenizer_tokens(MissingEOS())
  class MissingPaddingID:
   eos_token="<eos>"
   pad_token="<pad>"
   pad_token_id=None
  with self.assertRaisesRegex(ValueError,"padding token ID"):trainer.validate_tokenizer_tokens(MissingPaddingID())
  class ValidTokenizer:
   eos_token="<eos>"
   pad_token=None
   @property
   def pad_token_id(self):return 1 if self.pad_token is not None else None
  tok=ValidTokenizer()
  self.assertIs(trainer.validate_tokenizer_tokens(tok),tok)
  self.assertEqual(tok.pad_token,tok.eos_token)
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
 def test_build_sequence_truncates_prompt_to_preserve_response(self):
  class Tok:
   eos_token="<eos>"
   def __call__(self,text,add_special_tokens=True):
    parts=text.split()
    if parts and parts[-1]=="response<eos>":parts[-1]="response";parts.append("<eos>")
    elif parts and parts[-1]=="answer<eos>":parts[-1]="answer";parts.append("<eos>")
    return {"input_ids":parts}
  ids,prefix=trainer.build_sequence(Tok(),"very long prefix words","answer",max_length=4)
  self.assertEqual(ids,["words","Assistant:","answer","<eos>"])
  self.assertEqual(prefix,2)
 def test_build_sequence_rejects_response_over_limit(self):
  class Tok:
   eos_token="<eos>"
   def __call__(self,text,add_special_tokens=True):
    parts=text.split()
    if parts and parts[-1].endswith("<eos>"):
     parts[-1]=parts[-1][:-5]
     parts.append("<eos>")
    return {"input_ids":parts}
  with self.assertRaisesRegex(ValueError,"response exceeds sequence limit"):trainer.build_sequence(Tok(),"prompt","answer response",max_length=3)
 def test_build_sequence_uses_chat_template_prefix(self):
  class Tok:
   eos_token="<eos>"
   chat_template="fixture"
   def apply_chat_template(self,messages,tokenize=False,add_generation_prompt=False,enable_thinking=False):
    self.kw={"messages":messages,"add_generation_prompt":add_generation_prompt,"enable_thinking":enable_thinking}
    return "templated-prefix"
   def __call__(self,text,add_special_tokens=True):
    return {"input_ids":text.split()}
  tok=Tok()
  ids,prefix=trainer.build_sequence(tok,"question","answer",max_length=30)
  self.assertEqual(tok.kw["messages"],[{"role":"user","content":"question"}])
  self.assertTrue(tok.kw["add_generation_prompt"])
  self.assertFalse(tok.kw["enable_thinking"])
  self.assertEqual(ids[:prefix],["templated-prefix"])
  self.assertEqual(ids[prefix:],["answer<eos>"])
if __name__=="__main__":unittest.main()
