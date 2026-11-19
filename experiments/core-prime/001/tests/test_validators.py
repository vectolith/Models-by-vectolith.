import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
tasks=load("task_validator",ROOT/"validate_tasks.py");candidate=load("candidate_validator",ROOT/"validate_candidate.py");evaluator=load("evaluator",ROOT/"evaluate.py")
def file_rows(rows):
 f=tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",delete=False)
 for row in rows:f.write(json.dumps(row)+"\n")
 f.close();return Path(f.name)
def row(tid,prompt,split="train"):return {"task_id":tid,"category":"test","prompt":prompt,"split":split,"rubric_id":"r1","provenance":"fixture"}
class TaskTests(unittest.TestCase):
 def test_valid_record(self):self.assertEqual(tasks.validate([file_rows([row("1","hello")])])[1],[])
 def test_duplicate_id(self):self.assertTrue(any("duplicate task_id" in e for e in tasks.validate([file_rows([row("1","a"),row("1","b")])])[1]))
 def test_cross_split_prompt_leakage(self):self.assertTrue(any("leakage" in e for e in tasks.validate([file_rows([row("1","same prompt","train"),row("2"," SAME  prompt ","holdout")])])[1]))
 def test_prompt_hash_mismatch(self):
  r=row("1","prompt");r["content_sha256"]="0"*64;self.assertTrue(any("mismatch" in e for e in tasks.validate([file_rows([r])])[1]))
 def test_invalid_json(self):
  f=tempfile.NamedTemporaryFile(mode="w",delete=False);f.write("{bad\n");f.close();self.assertTrue(any("JSON parse" in e for e in tasks.validate([Path(f.name)])[1]))
 def test_normalization(self):self.assertEqual(tasks.normalized_prompt("A  B\nC"),"a b c")
class CandidateTests(unittest.TestCase):
 def record(self):return {"record_version":"1","candidate_id":"c1","repository_id":"org/model","revision":"a"*40,"status":"pending","output_training_permission":"pending","human_legal_review":"pending","compatibility_status":"pending"}
 def test_minimal_valid(self):self.assertEqual(candidate.validate(self.record()),[])
 def test_unpinned_revision(self):r=self.record();r["revision"]="main";self.assertTrue(any("revision" in e for e in candidate.validate(r)))
 def test_null_revision_rejected(self):r=self.record();r["revision"]=None;self.assertTrue(any("non-null" in e for e in candidate.validate(r)))
 def test_verified_gate(self):r=self.record();r["status"]="verified";self.assertTrue(any("verified status requires" in e for e in candidate.validate(r)))
 def test_verified_candidate_evidence_fields(self):
  r=self.record();r.update({"status":"verified","license_identifier":"Apache-2.0","license_evidence_path":"license.txt","license_evidence_sha256":"a"*64,"output_training_permission":"verified","output_training_permission_evidence_path":"permission.txt","output_training_permission_evidence_sha256":"b"*64,"human_legal_review":"approved","human_legal_review_evidence_path":"review.txt","human_legal_review_evidence_sha256":"c"*64,"model_config_evidence_path":"config.json","model_config_sha256":"d"*64,"tokenizer_revision":r["revision"],"chat_template_evidence_path":"template.txt","chat_template_sha256":"e"*64,"compatibility_status":"compatible","weight_inventory":[{"path":"weights.bin","sha256":"f"*64}]})
  self.assertEqual(candidate.validate(r),[])
 def test_hash_validation(self):r=self.record();r["license_evidence_sha256"]="z"*64;self.assertTrue(any("license_evidence" in e for e in candidate.validate(r)))
 def test_extra_fields(self):r=self.record();r["arbitrary"]=1;self.assertTrue(any("unexpected fields" in e for e in candidate.validate(r)))
class EvaluatorTests(unittest.TestCase):
 def test_hash_text(self):self.assertEqual(evaluator.sha256_text("abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
 def test_serialized_hash_stable_for_object(self):
  self.assertEqual(evaluator.sha256_serialized({"b":2,"a":1}),evaluator.sha256_serialized({"a":1,"b":2}))
 def test_package_inventory_snapshot_hashes_single_capture(self):
  from unittest.mock import patch
  expected=[{"name":"fixture","version":"1"}]
  with patch.object(evaluator,"package_inventory",return_value=expected) as capture:
   inventory,digest=evaluator.package_inventory_snapshot()
   self.assertEqual(inventory,expected)
   self.assertEqual(digest,evaluator.sha256_serialized(expected))
   capture.assert_called_once()
 def test_task_load_valid(self):self.assertEqual(len(evaluator.load_jsonl(file_rows([row("1","prompt")]))),1)
 def test_duplicate_task_id_rejected(self):
  with self.assertRaises(ValueError):evaluator.load_jsonl(file_rows([row("1","a"),row("1","b")]))
 def test_initialization_failure_records_cover_every_task(self):
  tasks=[row("1","first"),row("2","second")]
  records=evaluator.initialization_failure_records("run",tasks,RuntimeError("load failed"))
  self.assertEqual([r["task_id"] for r in records],["1","2"])
  self.assertTrue(all(r["status"]=="initialization_failed" for r in records))
  self.assertTrue(all(r["prompt_sha256"] for r in records))
  self.assertTrue(all("load failed" in r["error"] for r in records))
 def test_run_ids_are_unique(self):
  self.assertNotEqual(evaluator.new_run_id(),evaluator.new_run_id())
 def test_python_rng_seed_is_repeatable(self):
  import random
  evaluator.seed_python(123);first=random.random()
  evaluator.seed_python(123);second=random.random()
  self.assertEqual(first,second)
 def test_jsonl_writer_writes_parseable_lines_and_hash(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"out.jsonl"
   records=[{"task_id":"1","response":"a"},{"task_id":"2","response":"b"}]
   evaluator.write_jsonl(path,records)
   lines=path.read_text(encoding="utf-8").splitlines()
   self.assertEqual([json.loads(line) for line in lines],records)
   self.assertTrue(path.read_bytes().endswith(b"\n"))
   self.assertEqual(evaluator.sha256_file(path),evaluator.sha256_text(path.read_text(encoding="utf-8")))
 def test_dependency_block_records_status(self):
  records=evaluator.initialization_failure_records("run",[row("1","p")],RuntimeError("missing"),status="dependency_blocked")
  self.assertEqual(records[0]["status"],"dependency_blocked")
 def test_task_result_tally_partial_and_failure(self):
  records=[{"task_id":"1","status":"completed"},{"task_id":"2","status":"failed"},{"task_id":"3","status":"initialization_failed"}]
  self.assertEqual(evaluator.tally_records(records,3),(1,2,"partial"))
 def test_task_result_tally_initialization_failure(self):
  records=[{"status":"initialization_failed"},{"status":"initialization_failed"}]
  self.assertEqual(evaluator.tally_records(records,2),(0,2,"failed"))
 def test_task_result_tally_complete(self):
  records=[{"task_id":"1","status":"completed"},{"task_id":"2","status":"completed"}]
  self.assertEqual(evaluator.tally_records(records,2),(2,0,"completed"))
 def test_task_result_tally_missing_record(self):
  records=[{"task_id":"1","status":"completed"}]
  self.assertEqual(evaluator.tally_records(records,2),(1,1,"partial"))
 def test_task_result_tally_duplicate_record(self):
  records=[{"task_id":"1","status":"completed"},{"task_id":"1","status":"completed"}]
  self.assertEqual(evaluator.tally_records(records,2),(0,2,"failed"))
 def test_task_result_tally_extra_record(self):
  records=[{"task_id":"1","status":"completed"},{"task_id":"2","status":"completed"},{"task_id":"3","status":"completed"}]
  self.assertEqual(evaluator.tally_records(records,2),(2,1,"partial"))
if __name__=="__main__":unittest.main()
