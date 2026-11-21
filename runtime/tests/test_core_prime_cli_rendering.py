import unittest
from vectolith_runtime.core_prime_cli import render_messages, SYSTEM_PROMPT

class FakeTokenizer:
    chat_template = None

class CliRenderingTests(unittest.TestCase):
    def test_fallback_rendering(self):
        rendered = render_messages(FakeTokenizer(), [
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":"Hi"},
        ])
        self.assertIn("USER: Hi", rendered)
        self.assertTrue(rendered.endswith("ASSISTANT:"))

    def test_template_rendering_is_used(self):
        calls = {}
        class T:
            chat_template = "template"
            def apply_chat_template(self, messages, tokenize, add_generation_prompt):
                calls["messages"] = messages
                calls["tokenize"] = tokenize
                calls["generation_prompt"] = add_generation_prompt
                return "rendered"
        self.assertEqual(render_messages(T(), [{"role":"user","content":"Hi"}]), "rendered")
        self.assertFalse(calls["tokenize"])
        self.assertTrue(calls["generation_prompt"])
        self.assertEqual(calls["messages"], [{"role":"user","content":"Hi"}])

if __name__ == "__main__":
    unittest.main()
