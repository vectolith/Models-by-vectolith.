import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EVALUATOR=ROOT/"evaluate.py"
class HoldoutTests(unittest.TestCase):
 def test_holdout_rejected_even_with_deprecated_flag(self):
  with tempfile.TemporaryDirectory() as tmp:
   tasks=Path(tmp)/"holdout.jsonl"
   tasks.write_text(json.dumps({"task_id":"h1","prompt":"private","category":"test","split":"holdout"})+"\\n",encoding="utf-8")
   result=subprocess.run([sys.executable,str(EVALUATOR),"--model","unused","--revision","unused","--tasks",str(tasks),"--output",str(Path(tmp)/"out"),"--allow-holdout"],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0)
   self.assertIn("holdout inference blocked",result.stderr)
   self.assertFalse((Path(tmp)/"out").exists())
if __name__=="__main__":unittest.main()
