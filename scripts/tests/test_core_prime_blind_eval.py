import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_core_prime_blind_eval as ev
class EvalHarnessTests(unittest.TestCase):
 def test_summary_and_validation(self):
  rows=[{"dimension":"judgment","score":4,"gate_flags":[]},{"dimension":"judgment","score":2,"gate_flags":["capability_regression"]},{"dimension":"repair","score":None,"gate_flags":[]}]
  result=ev.summarize(rows)
  self.assertEqual(result["dimension_means"]["judgment"],3.0)
  self.assertEqual(result["dimension_counts"]["repair"],0)
  self.assertEqual(result["gate_flags"],["capability_regression"])
  with self.assertRaises(ValueError): ev.summarize([{"dimension":"judgment","score":6}])
 def test_blinding_deterministic(self):
  cases=[{"id":"x","prompt":"p","test":"t","dimension":"judgment"}]
  outputs={"x":{"base":"response A","candidate":"response B"}}
  a=ev.make_sheet(cases,outputs,7); b=ev.make_sheet(cases,outputs,7)
  self.assertEqual(a,b)
  self.assertEqual(len(a[0]["mapping"]),2)
if __name__=="__main__": unittest.main()
