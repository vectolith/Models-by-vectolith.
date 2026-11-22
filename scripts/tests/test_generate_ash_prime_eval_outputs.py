"""Tests for paired ASH PRIME evaluation generation helpers."""
import sys
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_ash_prime_eval_outputs as gen


class FakeTensor:
    def __init__(self, shape=(1, 2), device=None):
        self.shape = shape
        self.device = device
    def to(self, device):
        self.device = device
        return self


class FakeTorch:
    class _NoGrad:
        def __enter__(self): return self
        def __exit__(self, *args): return False
    def no_grad(self): return self._NoGrad()


class FakeModel:
    device = "cpu"
    def __init__(self): self.received = None
    def generate(self, inputs, **kwargs):
        self.received = (inputs, kwargs)
        return [[1, 2, 3, 4]]


class FakeTokenizer:
    chat_template = None
    eos_token_id = 4
    def __init__(self): self.text = None; self.messages = None
    def __call__(self, text, return_tensors):
        self.text = text
        return {"input_ids": FakeTensor(), "attention_mask": FakeTensor()}
    def decode(self, tokens, skip_special_tokens):
        self.tokens = tokens
        return "  generated answer  "
    def apply_chat_template(self, messages, tokenize, add_generation_prompt, return_tensors):
        self.messages = messages
        return FakeTensor()


class GenerationHelperTests(unittest.TestCase):
    def test_base_messages_include_context_without_system(self):
        messages = gen.build_messages({"context": "Prior context", "prompt": "Current prompt"})
        self.assertEqual(messages, [{"role": "user", "content": "Prior context\n\nCurrent prompt"}])

    def test_character_messages_add_system_prompt(self):
        messages = gen.build_messages({"context": "", "prompt": "Question"}, "  Character contract  ")
        self.assertEqual(messages, [{"role": "system", "content": "Character contract"}, {"role": "user", "content": "Question"}])

    def test_fallback_serialization_preserves_roles(self):
        text = gen.serialize_messages([{"role": "system", "content": "Character"}, {"role": "user", "content": "Question"}])
        self.assertEqual(text, "SYSTEM:\nCharacter\n\nUSER:\nQuestion")

    def test_fallback_generate_moves_inputs_and_trims_prompt(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Question"}, "Character"), 5)
        self.assertEqual(tokenizer.text, "SYSTEM:\nCharacter\n\nUSER:\nQuestion")
        self.assertEqual(tokenizer.tokens, [3, 4])
        self.assertEqual(result, "generated answer")
        self.assertEqual(model.received[1]["max_new_tokens"], 5)
        self.assertEqual(model.received[1]["do_sample"], False)

    def test_generation_rejects_output_without_eos(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        model.generate = lambda inputs, **kwargs: [[1, 2, 3]]
        with self.assertRaisesRegex(RuntimeError, "did not reach EOS"):
            gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Question"}), 5)

    def test_generation_rejects_empty_decoded_response(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        tokenizer.decode = lambda tokens, skip_special_tokens: "  "
        with self.assertRaisesRegex(RuntimeError, "empty response"):
            gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Question"}), 5)

    def test_generation_fails_closed_when_eos_is_unconfigured(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        tokenizer.eos_token_id = None
        with self.assertRaisesRegex(RuntimeError, "no EOS token ID is configured"):
            gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Question"}), 5)

    def test_chat_template_path_and_embedding_device(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        tokenizer.chat_template = "fake-template"
        tokenizer.apply_chat_template = FakeTokenizer.apply_chat_template.__get__(tokenizer)
        model.get_input_embeddings = lambda: type("Emb", (), {"weight": type("W", (), {"device": "cuda:1"})()})()
        gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 2)
        self.assertEqual(tokenizer.messages, [{"role": "user", "content": "Q"}])
        self.assertEqual(model.received[0].device, "cuda:1")

    def test_output_writer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "outputs.json"
            path.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                gen.write_outputs(path, {"x": {"base": "A"}})
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")

    def test_cli_refuses_existing_output_before_model_load(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases = root / "cases.jsonl"
            prompt = root / "character.txt"
            output = root / "outputs.json"
            cases.write_text(json.dumps({"id": "x", "prompt": "p"}) + "\n", encoding="utf-8")
            prompt.write_text("character", encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            args = ["generator.py", "--model", "unused", "--cases", str(cases), "--character-prompt", str(prompt), "--output", str(output), "--max-new-tokens", "4096"]
            with patch.object(sys, "argv", args):
                with self.assertRaises(SystemExit):
                    gen.main()
            self.assertEqual(output.read_text(encoding="utf-8"), "existing")

    def test_case_validation_rejects_duplicate_ids_and_bad_context(self):
        with self.assertRaises(ValueError):
            gen.validate_cases([{"id": "x", "prompt": "p"}, {"id": "x", "prompt": "p"}])
        with self.assertRaises(ValueError):
            gen.validate_cases([{"id": "x", "prompt": "p", "context": None}])


if __name__ == "__main__":
    unittest.main()
