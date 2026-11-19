import importlib.util, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("compare",Path(__file__).parents[1]/"compare_grades.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ComparisonTests(unittest.TestCase):
 def test_paired_delta_and_counts(self):
  a={"1":{"candidate_id":"base","scores":{"quality":2,"format":1}},"2":{"candidate_id":"base","scores":{"quality":1,"format":2}}}
  b={"1":{"candidate_id":"adapter","scores":{"quality":3,"format":1}},"2":{"candidate_id":"adapter","scores":{"quality":0,"format":3}}}
  r=m.compare(a,b);self.assertEqual(r["baseline_candidate_id"],"base");self.assertEqual(r["adapter_candidate_id"],"adapter");self.assertEqual(r["criteria"]["quality"]["mean_delta"],0);self.assertEqual(r["criteria"]["quality"]["improved"],1);self.assertEqual(r["criteria"]["quality"]["regressed"],1);self.assertEqual(r["criteria"]["format"]["mean_delta"],0.5)
 def test_mismatch_ids_rejected(self):
  with self.assertRaises(ValueError):m.compare({"1":{"candidate_id":"b","scores":{"x":1}}},{"2":{"candidate_id":"a","scores":{"x":1}}})
 def test_mismatch_criteria_rejected(self):
  with self.assertRaises(ValueError):m.compare({"1":{"candidate_id":"b","scores":{"x":1}}},{"1":{"candidate_id":"a","scores":{"y":1}}})
 def test_load_duplicate_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x";p.write_text('{"task_id":"1","candidate_id":"b","scores":{"x":1}}\n{"task_id":"1","candidate_id":"b","scores":{"x":2}}\n')
   with self.assertRaises(ValueError):m.load(p)
 def test_nonfinite_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x";p.write_text('{"task_id":"1","candidate_id":"b","scores":{"x":NaN}}\n')
   with self.assertRaises(ValueError):m.load(p)
 def test_candidate_id_required(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x";p.write_text('{"task_id":"1","scores":{"x":1}}\n')
   with self.assertRaisesRegex(ValueError,"candidate_id required"):m.load(p)
 def test_candidate_id_consistency(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x";p.write_text('{"task_id":"1","candidate_id":"b","scores":{"x":1}}\n{"task_id":"2","candidate_id":"a","scores":{"x":2}}\n')
   with self.assertRaisesRegex(ValueError,"consistent"):m.load(p)
 def test_whitespace_criterion_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x";p.write_text('{"task_id":"1","candidate_id":"b","scores":{"   ":1}}\n')
   with self.assertRaisesRegex(ValueError,"finite numeric"):m.load(p)
 def test_notes_must_be_text(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x";p.write_text('{"task_id":"1","candidate_id":"b","scores":{"x":1},"notes":[]}\n')
   with self.assertRaisesRegex(ValueError,"notes must be text"):m.load(p)
if __name__=="__main__":unittest.main()
