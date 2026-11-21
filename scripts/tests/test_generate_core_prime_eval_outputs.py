"""Tests for paired Core Prime evaluation generation helpers."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_core_prime_eval_outputs as gen

class GenerationHelperTests(unittest.TestCase):
    def test_base_messages_include_context_without_system(self):
        row={"context":"Prior context","prompt":"Current prompt"}
        messages=gen.build_messages(row)
        self.assertEqual(messages,[{"role":"user","content":"Prior context\\n\\nCurrent prompt"}])

    def test_character_messages_add_system_prompt(self):
        row={"context":"","prompt":"Question"}
        messages=gen.build_messages(row,"  Character contract  ")
        self.assertEqual(messages,[{"role":"system","content":"Character contract"},{"role":"user","content":"Question"}])

if __name__=="__main__":
    unittest.main()
