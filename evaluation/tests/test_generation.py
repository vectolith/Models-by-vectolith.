from __future__ import annotations

import unittest

from evaluation.generation import render_prompt


class PromptRenderingTests(unittest.TestCase):
    def test_removes_token_type_ids_not_supported_by_causal_models(self):
        class FakeTokenizer:
            def apply_chat_template(self, messages, **kwargs):
                self.messages = messages
                self.options = kwargs
                return {
                    "input_ids": "input",
                    "attention_mask": "mask",
                    "token_type_ids": "unused segment ids",
                }

        tokenizer = FakeTokenizer()
        messages = [{"role": "user", "content": "test"}]
        encoded = render_prompt(tokenizer, messages)

        self.assertEqual(encoded, {"input_ids": "input", "attention_mask": "mask"})
        self.assertEqual(tokenizer.messages, messages)
        self.assertTrue(tokenizer.options["add_generation_prompt"])


if __name__ == "__main__":
    unittest.main()
