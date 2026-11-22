import unittest
from vectolith_runtime.ash_prime_cli import render_messages, trim_messages, SYSTEM_PROMPT

class FakeTokenizer:
    chat_template = None
    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": text.split()}

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

    def test_trim_preserves_system_and_latest_user(self):
        tok = FakeTokenizer()
        msgs = [
            {"role":"system","content":"keep"},
            {"role":"user","content":"old user message"},
            {"role":"assistant","content":"old answer"},
            {"role":"user","content":"newest request"},
        ]
        trimmed = trim_messages(tok, msgs, 5)
        self.assertEqual(trimmed[0]["role"], "system")
        self.assertEqual(trimmed[-1]["content"], "newest request")
        self.assertLess(len(tok(render_messages(tok, trimmed))["input_ids"]), len(tok(render_messages(tok, msgs))["input_ids"]))

if __name__ == "__main__":
    unittest.main()
