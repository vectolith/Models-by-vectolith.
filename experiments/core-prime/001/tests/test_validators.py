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
 def test_hash_validation(self):r=self.record();r["license_evidence_sha256"]="z"*64;self.assertTrue(any("license_evidence" in e for e in candidate.validate(r)))
 def test_extra_fields(self):r=self.record();r["arbitrary"]=1;self.assertTrue(any("unexpected fields" in e for e in candidate.validate(r)))
class EvaluatorTests(unittest.TestCase):
 def test_hash_text(self):self.assertEqual(evaluator.sha256_text("abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
 def test_task_load_valid(self):self.assertEqual(len(evaluator.load_jsonl(file_rows([row("1","prompt")]))),1)
 def test_duplicate_task_id_rejected(self):
  with self.assertRaises(ValueError):evaluator.load_jsonl(file_rows([row("1","a"),row("1","b")]))
if __name__=="__main__":unittest.main()
