import sys
import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_core_prime_blind_eval as ev


def case():
    return {"id":"x","prompt":"p","context":"","test":"t","dimension":"judgment"}


class EvalHarnessTests(unittest.TestCase):
    def test_summary_and_validation(self):
        rows = [{"case_id":"x","dimension":"judgment","score":4,"gate_flags":[]},
                 {"case_id":"y","dimension":"judgment","score":2,"gate_flags":["capability_regression"]},
                 {"case_id":"z","dimension":"repair","score":None,"gate_flags":[]}]
        result = ev.summarize(rows)
        self.assertEqual(result["dimension_means"]["judgment"], 3.0)
        self.assertEqual(result["dimension_counts"]["repair"], 0)
        self.assertEqual(result["gate_flags"], ["capability_regression"])
        with self.assertRaises(ValueError): ev.summarize([{"case_id":"x","dimension":"judgment","score":6}])
        with self.assertRaises(ValueError): ev.summarize([{"case_id":"x","dimension":"judgment","score":2,"gate_flags":["badflag"]}])
        with self.assertRaises(ValueError): ev.summarize([{"dimension":"judgment","score":2}])
        with self.assertRaises(ValueError): ev.summarize([{"case_id":"x","dimension":"judgment","score":2},{"case_id":"x","dimension":"judgment","score":3}])

    def test_blinding_mapping_is_separate_and_deterministic(self):
        outputs = {"x":{"base":"response A","character_prompt":"response B"}}
        a, mapping = ev.make_sheet([case()], outputs, 7)
        b, mapping_b = ev.make_sheet([case()], outputs, 7)
        self.assertEqual(a, b)
        self.assertEqual(mapping, mapping_b)
        self.assertNotIn("mapping", a[0])
        self.assertEqual(set(mapping["x"].values()), {"base","character_prompt"})
        self.assertEqual({r["blind_label"] for r in a[0]["responses"]}, {"candidate_1","candidate_2"})

    def test_case_and_output_validation(self):
        with self.assertRaises(ValueError): ev.validate_cases([case(), case()])
        with self.assertRaises(ValueError): ev.make_sheet([case()], {}, 1)
        with self.assertRaises(ValueError): ev.make_sheet([case()], {"x":{"base":"A","other":"B"}}, 1)
        with self.assertRaises(ValueError): ev.make_sheet([case()], {"x":{"base":"A","character_prompt":""}}, 1)
        with self.assertRaises(ValueError): ev.make_sheet([case()], {"x":{"base":"A","character_prompt":"B"},"extra":{}}, 1)

    def test_jsonl_writer_real_newlines(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.jsonl"
            ev.write_jsonl(path, [{"x":1},{"x":2}])
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)

    def test_directories_must_be_disjoint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError): ev.validate_output_directories(root / "sheet", root / "sheet" / "nested")
            with self.assertRaises(ValueError): ev.validate_output_directories(root / "sheet" / "nested", root / "sheet")
            self.assertEqual(ev.validate_output_directories(root / "sheet", root / "map")[0], (root / "sheet").resolve())


    def test_score_ids_and_dimensions_are_bound_to_cases(self):
        score_rows = [{"case_id":"x","dimension":"judgment","score":3}]
        self.assertEqual(ev.validate_scores(score_rows, [case()]), score_rows)
        with self.assertRaises(ValueError):
            ev.validate_scores([{"case_id":"unknown","dimension":"judgment","score":3}], [case()])
        with self.assertRaises(ValueError):
            ev.validate_scores([{"case_id":"x","dimension":"repair","score":3}], [case()])

    def test_cli_refuses_to_overwrite_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases_path = root / "cases.jsonl"
            scores_path = root / "scores.jsonl"
            output = root / "summary-output"
            cases_path.write_text(json.dumps(case()) + "\n", encoding="utf-8")
            scores_path.write_text(json.dumps({"case_id":"x","dimension":"judgment","score":4,"gate_flags":[]}) + "\n", encoding="utf-8")
            args = ["run_core_prime_blind_eval.py", "--cases", str(cases_path), "--scores", str(scores_path), "--output", str(output)]
            with patch.object(sys, "argv", args):
                ev.main()
            summary = output / "summary.json"
            original = summary.read_text(encoding="utf-8")
            with patch.object(sys, "argv", args):
                with self.assertRaises(SystemExit):
                    ev.main()
            self.assertEqual(summary.read_text(encoding="utf-8"), original)

    def test_cli_keeps_mapping_out_of_evaluator_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases_path = root / "cases.jsonl"
            outputs_path = root / "outputs.json"
            sheet_dir = root / "score-sheets"
            map_dir = root / "restricted"
            cases_path.write_text(json.dumps(case()) + "\n", encoding="utf-8")
            outputs_path.write_text(json.dumps({"x":{"base":"A","character_prompt":"B"}}), encoding="utf-8")
            with patch.object(sys, "argv", ["run_core_prime_blind_eval.py", "--cases", str(cases_path), "--outputs", str(outputs_path), "--output", str(sheet_dir), "--map-output", str(map_dir)]):
                ev.main()
            self.assertTrue((sheet_dir / "blind-score-sheet.jsonl").exists())
            self.assertTrue((map_dir / "blind-label-map.json").exists())
            self.assertFalse((sheet_dir / "blind-label-map.json").exists())
            if os.name == "posix":
                self.assertEqual(map_dir.stat().st_mode & 0o777, 0o700)
                self.assertEqual((map_dir / "blind-label-map.json").stat().st_mode & 0o777, 0o600)

if __name__ == "__main__":
    unittest.main()
