import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_core_prime_blind_eval as ev

class EvalHarnessTests(unittest.TestCase):
    def test_summary_and_validation(self):
        rows = [{"dimension":"judgment","score":4,"gate_flags":[]},
                 {"dimension":"judgment","score":2,"gate_flags":["capability_regression"]},
                 {"dimension":"repair","score":None,"gate_flags":[]}]
        result = ev.summarize(rows)
        self.assertEqual(result["dimension_means"]["judgment"], 3.0)
        self.assertEqual(result["dimension_counts"]["repair"], 0)
        self.assertEqual(result["gate_flags"], ["capability_regression"])
        with self.assertRaises(ValueError): ev.summarize([{"dimension":"judgment","score":6}])
        with self.assertRaises(ValueError): ev.summarize([{"dimension":"judgment","score":2,"gate_flags":["badflag"]}])

    def test_blinding_mapping_is_separate_and_deterministic(self):
        cases = [{"id":"x","prompt":"p","test":"t","dimension":"judgment"}]
        outputs = {"x":{"base":"response A","candidate":"response B"}}
        a, mapping = ev.make_sheet(cases, outputs, 7)
        b, mapping_b = ev.make_sheet(cases, outputs, 7)
        self.assertEqual(a, b)
        self.assertEqual(mapping, mapping_b)
        self.assertNotIn("mapping", a[0])
        self.assertEqual(len(mapping["x"]), 2)

    def test_duplicate_case_ids_and_missing_outputs(self):
        with self.assertRaises(ValueError): ev.validate_cases([{'id':'x','prompt':'p','test':'t','dimension':'judgment'},{'id':'x','prompt':'p','test':'t','dimension':'judgment'}])
        with self.assertRaises(ValueError): ev.make_sheet([{'id':'x','prompt':'p','test':'t','dimension':'judgment'}], {}, 1)

    def test_jsonl_writer_real_newlines(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'out.jsonl'
            ev.write_jsonl(path, [{'x':1},{'x':2}])
            self.assertEqual(len(path.read_text(encoding='utf-8').splitlines()), 2)

    def test_missing_condition_fails(self):
        with self.assertRaises(ValueError):
            ev.make_sheet([{"id":"x","prompt":"p","test":"t","dimension":"judgment"}], {"x":{"only":"one"}}, 1)

if __name__ == "__main__":
    unittest.main()
