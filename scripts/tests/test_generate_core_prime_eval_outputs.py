"""Tests for paired Core Prime generation/audit helpers; all generation is mocked."""
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_core_prime_eval_outputs as gen


class FakeTensor:
    def __init__(self, values, device=None):
        self.values = values
        self.device = device
        self.shape = (1, len(values[0])) if values and isinstance(values[0], list) else (1, len(values))
    def to(self, device):
        self.device = device
        return self
    def __getitem__(self, index):
        return self.values[index]


class FakeTorch:
    class _NoGrad:
        def __enter__(self): return self
        def __exit__(self, *args): return False
    def no_grad(self): return self._NoGrad()


class FakeModel:
    device = "cpu"
    def __init__(self, sequences=None, reason="eos"):
        self.generation_config = type("Config", (), {"eos_token_id": 4})()
        self.config = type("Config", (), {"eos_token_id": 4, "_commit_hash": "mock-revision"})()
        self.sequences = sequences or [[1, 2, 3, 4]]
        self.reason = reason
        self.received = None
    def generate(self, inputs, **kwargs):
        self.received = (inputs, kwargs)
        return {"sequences": self.sequences, "finish_reason": self.reason}


class FakeTokenizer:
    chat_template = None
    eos_token_id = 4
    init_kwargs = {}
    name_or_path = "fake-tokenizer"
    def __init__(self):
        self.text = None
        self.messages = None
    def __call__(self, text, return_tensors):
        self.text = text
        return {"input_ids": FakeTensor([[1, 2]]), "attention_mask": FakeTensor([[1, 1]])}
    def decode(self, tokens, skip_special_tokens):
        self.tokens = tokens
        return "  generated answer  "


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

    def test_complete_generation_records_hashes_and_stop_metadata(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Question"}, "Character"), 4096)
        self.assertEqual(tokenizer.text, "SYSTEM:\nCharacter\n\nUSER:\nQuestion")
        self.assertEqual(tokenizer.tokens, [3, 4])
        self.assertEqual(result["response_text"], "generated answer")
        self.assertEqual(result["completion_status"], "complete")
        self.assertEqual(result["completion_reason"], "eos_token")
        self.assertEqual(result["native_stop_metadata"], "eos")
        self.assertEqual(result["generated_token_ids"], [3, 4])
        self.assertEqual(result["generated_token_count"], 2)
        self.assertEqual(result["max_new_tokens"], 4096)
        self.assertTrue(result["prompt_token_ids_sha256"])
        self.assertTrue(result["generated_token_ids_sha256"])
        self.assertTrue(result["response_sha256"])
        self.assertTrue(model.received[1]["return_dict_in_generate"])

    def test_budget_exhaustion_is_incomplete_not_accepted(self):
        model, tokenizer = FakeModel([[1, 2, 3]], reason="length"), FakeTokenizer()
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)
        self.assertEqual(result["completion_status"], "incomplete")
        self.assertEqual(result["completion_reason"], "budget_exhausted")
        self.assertEqual(result["generated_token_ids"], [3])

    def test_eos_followed_by_tokens_is_a_conflict(self):
        model, tokenizer = FakeModel([[1, 2, 4, 5]], reason="eos"), FakeTokenizer()
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)
        self.assertEqual(result["completion_status"], "conflict")
        self.assertEqual(result["completion_reason"], "contradictory_stop_metadata")
        self.assertEqual(result["generated_token_ids"], [4, 5])

    def test_native_budget_metadata_conflicts_with_eos(self):
        model, tokenizer = FakeModel([[1, 2, 3, 4]], reason="length"), FakeTokenizer()
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)
        self.assertEqual(result["completion_status"], "conflict")

    def test_native_eos_metadata_without_eos_token_is_a_conflict(self):
        model, tokenizer = FakeModel([[1, 2, 3]], reason="eos"), FakeTokenizer()
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)
        self.assertEqual(result["completion_status"], "conflict")
        self.assertEqual(result["completion_reason"], "contradictory_stop_metadata")

    def test_unknown_native_stop_metadata_is_rejected(self):
        model, tokenizer = FakeModel([[1, 2, 3, 4]], reason="custom-stop"), FakeTokenizer()
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)
        self.assertEqual(result["completion_status"], "conflict")

    def test_eos_config_conflicts_fail_closed_before_generation(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        model.generation_config.eos_token_id = 5
        with self.assertRaisesRegex(RuntimeError, "Conflicting EOS token IDs"):
            gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)
        self.assertIsNone(model.received)

    def test_missing_eos_configuration_fails_closed(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        tokenizer.eos_token_id = None
        model.generation_config.eos_token_id = None
        model.config.eos_token_id = None
        with self.assertRaisesRegex(RuntimeError, "no EOS token ID"):
            gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)

    def test_empty_decoded_response_is_not_complete(self):
        model, tokenizer = FakeModel(), FakeTokenizer()
        tokenizer.decode = lambda tokens, skip_special_tokens: "  "
        result = gen.generate(model, tokenizer, FakeTorch(), gen.build_messages({"prompt": "Q"}), 10)
        self.assertEqual(result["completion_status"], "incomplete")
        self.assertEqual(result["completion_reason"], "empty_decoded_response")

    def test_audit_ledger_is_exclusive_and_append_preserves_records(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run.audit.jsonl"
            gen._append_audit(path, {"type": "run_start", "run_id": "r"}, create=True)
            gen._append_audit(path, {"type": "attempt", "run_id": "r"})
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows, [{"type": "run_start", "run_id": "r"}, {"type": "attempt", "run_id": "r"}])
            with self.assertRaises(FileExistsError):
                gen._append_audit(path, {"type": "new"}, create=True)
            if __import__("os").name == "posix":
                self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(__import__("os").name == "posix", "POSIX no-follow file protection required")
    def test_audit_ledger_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.jsonl"
            target.write_text("preserve\\n", encoding="utf-8")
            link = root / "audit.jsonl"
            link.symlink_to(target)
            with self.assertRaises(OSError):
                gen._append_audit(link, {"type": "record"}, create=True)
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve\\n")

    @unittest.skipUnless(__import__("os").name == "posix", "POSIX no-follow path traversal required")
    def test_generation_artifacts_reject_symlinked_parent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.mkdir(mode=0o700)
            link = root / "parent-link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(OSError):
                gen._append_audit(link / "ledger.jsonl", {"type": "record"}, create=True)
            with self.assertRaises(OSError):
                gen.write_outputs(link / "outputs.json", {"x": {"base": "A"}})
            self.assertFalse((target / "ledger.jsonl").exists())
            self.assertFalse((target / "outputs.json").exists())

    @unittest.skipUnless(__import__("os").name == "posix", "POSIX private directory/file modes required")
    def test_generation_artifacts_create_private_directory_and_files(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td) / "private"
            audit = directory / "run.audit.jsonl"
            output = directory / "outputs.json"
            gen._append_audit(audit, {"type": "run_start"}, create=True)
            gen.write_outputs(output, {"x": {"base": "A"}})
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual(audit.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_output_writer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "outputs.json"
            path.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                gen.write_outputs(path, {"x": {"base": "A"}})
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")

    def test_cli_refuses_existing_output_and_audit_before_model_load(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases = root / "cases.jsonl"
            prompt = root / "character.txt"
            output = root / "outputs.json"
            audit = gen.audit_path_for(output)
            cases.write_text(json.dumps({"id": "x", "prompt": "p"}) + "\n", encoding="utf-8")
            prompt.write_text("character", encoding="utf-8")
            audit.write_text("existing audit", encoding="utf-8")
            args = ["generator.py", "--model", "unused", "--cases", str(cases), "--character-prompt", str(prompt), "--output", str(output), "--max-new-tokens", "4096"]
            with patch.object(sys, "argv", args):
                with self.assertRaises(SystemExit):
                    gen.main()
            self.assertEqual(audit.read_text(encoding="utf-8"), "existing audit")
            self.assertFalse(output.exists())

    def test_case_validation_rejects_duplicate_ids_and_bad_context(self):
        with self.assertRaises(ValueError):
            gen.validate_cases([{"id": "x", "prompt": "p"}, {"id": "x", "prompt": "p"}])
        with self.assertRaises(ValueError):
            gen.validate_cases([{"id": "x", "prompt": "p", "context": None}])

    @unittest.skipUnless(__import__("os").name == "posix", "POSIX file permissions required")
    def test_audit_append_rejects_permissive_existing_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            path.write_text("{}\\n", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(OSError, "permissions are too permissive"):
                gen._append_audit(path, {"type": "attempt"})
            self.assertEqual(path.read_text(encoding="utf-8"), "{}\\n")


if __name__ == "__main__":
    unittest.main()
