import json,subprocess,sys,tempfile,unittest
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EVALUATOR=ROOT/"evaluate.py"
spec=importlib.util.spec_from_file_location("evaluator",EVALUATOR);evaluator=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluator)
class HoldoutTests(unittest.TestCase):
 def test_frozen_manifest_exact_match_and_hash(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"tasks.jsonl";tasks.write_text('{"task_id":"a","prompt":"p","category":"c","split":"development"}'+chr(10),encoding="utf-8")
   manifest=Path(tmp)/"freeze.json";values={"model":"m","revision":"r","tasks_sha256":evaluator.sha256_file(tasks),"seed":7,"max_new_tokens":20,"temperature":0.0,"trust_remote_code":False,"qwen3_thinking":False,"limit":1,"selected_task_count":1,"selected_task_ids_sha256":evaluator.sha256_serialized(["a"])}
   manifest.write_text(json.dumps(values),encoding="utf-8")
   digest=evaluator.verify_frozen_config(manifest,"m","r",tasks,7,20,0.0,False,False,1,["a"])
   self.assertEqual(digest,evaluator.sha256_file(manifest))
   with self.assertRaisesRegex(ValueError,"revision"):evaluator.verify_frozen_config(manifest,"m","other",tasks,7,20,0.0,False,False,1,["a"])
   with self.assertRaisesRegex(ValueError,"limit"):evaluator.verify_frozen_config(manifest,"m","r",tasks,7,20,0.0,False,False,0,["a"])
 def test_fallback_prompt_tokenization_matches_training_template(self):\n  source=EVALUATOR.read_text(encoding="utf-8")\n  self.assertIn("encoded=f\\\"User:\\\\\\\\n{prompt}\\\\\\\\nAssistant:\\\\n\\\"",source)\n  self.assertIn("add_special_tokens=False",source)\n def test_holdout_rejected_even_with_deprecated_flag(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"holdout.jsonl"
   tasks.write_text(json.dumps({"task_id":"h1","prompt":"private","category":"test","split":"holdout"})+chr(10),encoding="utf-8")
   result=subprocess.run([sys.executable,str(EVALUATOR),"--model","unused","--revision","unused","--tasks",str(tasks),"--output",str(Path(tmp)/"out"),"--freeze-manifest",str(Path(tmp)/"freeze.json"),"--allow-holdout"],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0)
   self.assertIn("holdout inference blocked",result.stderr)
   self.assertFalse((Path(tmp)/"out").exists())
if __name__=="__main__":unittest.main()
