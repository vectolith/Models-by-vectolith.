import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPOSITORY_ROOT=ROOT.parents[3]
class RequirementsTests(unittest.TestCase):
 def test_baseline_requirements_are_directly_pinned(self):
  lines=(ROOT/"requirements.txt").read_text(encoding="utf-8").splitlines()
  self.assertEqual(lines,[
   "torch==2.8.0","transformers==4.57.1","accelerate==1.10.1",
   "safetensors==0.6.2","huggingface_hub==0.36.0"])
  self.assertTrue(all(line.strip() and "\\n" not in line for line in lines))
 def test_training_requirements_extend_baseline_with_peft_pin(self):
  lines=(ROOT/"requirements-training.txt").read_text(encoding="utf-8").splitlines()
  self.assertEqual(lines,["-r requirements.txt","peft==0.13.0"])
 def test_ci_persists_hashed_dependency_inventory(self):
  workflow=(REPOSITORY_ROOT/".github/workflows/core-prime-experiment-tests.yml").read_text(encoding="utf-8")
  self.assertIn("actions/upload-artifact@615b319bd27bb32c3d64dca6b6ed6974d5fbe653",workflow)
  self.assertIn("evidence/dependency-inventory.txt",workflow)
  self.assertIn("evidence/dependency-inventory.sha256",workflow)
  self.assertIn("if-no-files-found: error",workflow)
  self.assertIn("retention-days: 14",workflow)
if __name__=="__main__":unittest.main()
