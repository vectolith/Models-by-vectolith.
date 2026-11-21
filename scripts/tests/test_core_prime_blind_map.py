import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_core_prime_blind_eval as blind

class BlindSheetTests(unittest.TestCase):
    def test_mapping_is_not_embedded_in_evaluator_sheet(self):
        cases=[{"id":"x","prompt":"p","context":"","test":"t","dimension":"judgment"}]
        outputs={"x":{"base":"first","character":"second"}}
        sheet,mapping=blind.make_sheet(cases,outputs,1)
        self.assertNotIn("mapping",sheet[0])
        self.assertEqual(set(mapping["x"].values()),{"base","character"})
        labels={r["blind_label"] for r in sheet[0]["responses"]}
        self.assertEqual(labels,{"candidate_1","candidate_2"})

if __name__=="__main__":
    unittest.main()
