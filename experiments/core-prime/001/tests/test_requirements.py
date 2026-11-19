import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RequirementsTests(unittest.TestCase):
 def test_training_requirements_are_separate_lines(self):
  lines=(ROOT/"requirements-training.txt").read_text(encoding="utf-8").splitlines()
  self.assertEqual(lines,["torch","transformers","accelerate","safetensors","peft"])
  self.assertTrue(all(line.strip() and "\\n" not in line for line in lines))
if __name__=="__main__":unittest.main()
