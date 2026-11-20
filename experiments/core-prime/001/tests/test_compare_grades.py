import importlib.util, tempfile, unittest, json
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


 def test_load_snapshot_hash_is_bound_to_parsed_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"grades.jsonl";original=json.dumps({"task_id":"1","candidate_id":"base","scores":{"x":1}})+"\\n";p.write_text(original,encoding="utf-8")
   rows,digest=m.load_snapshot(p)
   p.write_text(json.dumps({"task_id":"2","candidate_id":"changed","scores":{"x":2}})+"\n",encoding="utf-8")
   self.assertEqual(set(rows),{"1"})
   self.assertEqual(digest,__import__("hashlib").sha256(original.encode("utf-8")).hexdigest())
\n def test_main_records_input_hashes_and_atomic_output(self):
  import sys
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);base=root/"base.jsonl";adapter=root/"adapter.jsonl";out=root/"comparison.json"
   base.write_text(json.dumps({"task_id":"1","candidate_id":"base","scores":{"quality":1}})+"\n",encoding="utf-8")
   adapter.write_text(json.dumps({"task_id":"1","candidate_id":"adapter","scores":{"quality":2}})+"\n",encoding="utf-8")
   with patch.object(sys,"argv",["compare_grades.py","--baseline-grades",str(base),"--adapter-grades",str(adapter),"--output",str(out)]):m.main()
   result=json.loads(out.read_text(encoding="utf-8"))
   self.assertEqual(result["comparison_schema_version"],1)
   self.assertEqual(result["input_grade_file_sha256"],{"baseline":m.sha256_file(base),"adapter":m.sha256_file(adapter)})
   self.assertFalse(out.with_suffix(out.suffix+".tmp").exists())
if __name__=="__main__":unittest.main()
