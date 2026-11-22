#!/usr/bin/env python3
"""Generate paired local Core Prime outputs with an append-only completion audit ledger.

This script does not train or use hosted inference. A pair is publishable only
when every condition reaches a verified EOS token and metadata is consistent.
"""
import argparse
import hashlib
import json
import os
import secrets
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def build_messages(row, system_prompt=None):
    context = row.get("context", "").strip()
    prompt = row["prompt"].strip()
    user_text = "\n\n".join(part for part in (context, prompt) if part)
    messages = []
    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": user_text})
    return messages


def serialize_messages(messages):
    """Explicit role-marked fallback for tokenizers without a chat template."""
    return "\n\n".join(f"{message['role'].upper()}:\n{message['content']}" for message in messages)


def validate_cases(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Evaluation cases must be a nonempty JSONL list")
    ids = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each evaluation case must be a JSON object")
        case_id, prompt = row.get("id"), row.get("prompt")
        context = row.get("context", "")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Evaluation case IDs must be nonempty strings")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{case_id}: prompt must be a nonempty string")
        if not isinstance(context, str):
            raise ValueError(f"{case_id}: context must be a string")
        ids.append(case_id)
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation case IDs must be unique")
    return rows


def _input_device(model):
    try:
        return model.get_input_embeddings().weight.device
    except (AttributeError, RuntimeError, TypeError):
        return model.device


def _normalize_eos_value(value, source):
    if value is None:
        return None
    values = value if isinstance(value, (list, tuple, set)) else [value]
    if not values or any(type(item) is not int or item < 0 for item in values):
        raise RuntimeError(f"Invalid EOS token IDs in {source}")
    normalized = set(values)
    if not normalized:
        raise RuntimeError(f"Empty EOS token IDs in {source}")
    return normalized


def _eos_token_ids(model, tokenizer):
    sources = {}
    for name, value in (
        ("tokenizer", getattr(tokenizer, "eos_token_id", None)),
        ("generation_config", getattr(getattr(model, "generation_config", None), "eos_token_id", None)),
        ("model_config", getattr(getattr(model, "config", None), "eos_token_id", None)),
    ):
        normalized = _normalize_eos_value(value, name)
        if normalized is not None:
            sources[name] = normalized
    if not sources:
        raise RuntimeError("Cannot verify completion: no EOS token ID is configured")
    baseline = next(iter(sources.values()))
    if any(ids != baseline for ids in sources.values()):
        details = {name: sorted(ids) for name, ids in sources.items()}
        raise RuntimeError(f"Conflicting EOS token IDs across configuration sources: {details}")
    return sorted(baseline), sources


def _flat_int_list(value):
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, tuple):
        value = list(value)
    if not isinstance(value, list):
        raise RuntimeError("Generation/input IDs are not a list-like tensor")
    if len(value) == 1 and isinstance(value[0], (list, tuple)):
        value = list(value[0])
    if any(type(item) is not int for item in value):
        raise RuntimeError("Token ID sequence contains non-integer values")
    return list(value)


def _sha256_json(value):
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _native_stop_metadata(generated):
    found = []
    for name in ("finish_reason", "stop_reason"):
        value = generated.get(name) if isinstance(generated, dict) else getattr(generated, name, None)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            if len(value) != 1:
                raise RuntimeError(f"Conflicting native {name} metadata for single-example generation")
            value = value[0]
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Invalid native {name} metadata")
        found.append((name, value.strip().lower().replace("-", "_")))
    if not found:
        return None
    if len({value for _, value in found}) > 1:
        raise RuntimeError(f"Conflicting native stop metadata: {found}")
    return found[0][1]


def _stop_category(value):
    if value is None:
        return None
    if value in {"eos", "eos_token", "end_of_sequence", "stop", "completed"}:
        return "eos"
    if value in {"length", "max_length", "max_new_tokens", "budget_exhausted", "limit"}:
        return "budget"
    return "unknown"


def generate(model, tokenizer, torch, messages, max_new_tokens):
    if max_new_tokens < 1:
        raise ValueError("max_new_tokens must be positive")
    if getattr(tokenizer, "chat_template", None) and callable(getattr(tokenizer, "apply_chat_template", None)):
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        )
    else:
        encoded = tokenizer(serialize_messages(messages), return_tensors="pt")
    if isinstance(encoded, dict):
        input_ids, attention_mask = encoded["input_ids"], encoded.get("attention_mask")
    else:
        input_ids, attention_mask = encoded, None
    device = _input_device(model)
    input_ids = input_ids.to(device)
    prompt_ids = _flat_int_list(input_ids[0])
    prompt_hash = _sha256_json(prompt_ids)
    eos_ids, eos_sources = _eos_token_ids(model, tokenizer)
    kwargs = {"max_new_tokens": max_new_tokens, "do_sample": False, "return_dict_in_generate": True}
    if attention_mask is not None:
        kwargs["attention_mask"] = attention_mask.to(device)
    with torch.no_grad():
        generated = model.generate(input_ids, **kwargs)
    sequences = generated.get("sequences") if isinstance(generated, dict) else getattr(generated, "sequences", generated)
    sequence_ids = _flat_int_list(sequences[0])
    if sequence_ids[: len(prompt_ids)] != prompt_ids:
        raise RuntimeError("Returned sequence does not preserve the exact input token prefix")
    raw_token_ids = sequence_ids[len(prompt_ids):]
    native_reason = _native_stop_metadata(generated)
    native_category = _stop_category(native_reason)
    eos_index = next((i for i, token_id in enumerate(raw_token_ids) if token_id in eos_ids), None)
    conflict = native_category == "unknown"
    if native_category == "eos" and eos_index is None:
        conflict = True
    if native_category == "budget" and eos_index is not None:
        conflict = True
    if eos_index is not None and eos_index != len(raw_token_ids) - 1:
        conflict = True
    if conflict:
        status, reason, accepted_ids = "conflict", "contradictory_stop_metadata", raw_token_ids
    elif eos_index is None:
        status, reason, accepted_ids = "incomplete", "budget_exhausted", raw_token_ids
    else:
        status, reason, accepted_ids = "complete", "eos_token", raw_token_ids
    response = tokenizer.decode(accepted_ids, skip_special_tokens=True).strip()
    if not response and status == "complete":
        status, reason = "incomplete", "empty_decoded_response"
    return {
        "completion_status": status,
        "completion_reason": reason,
        "native_stop_metadata": native_reason,
        "response_text": response,
        "prompt_token_count": len(prompt_ids),
        "prompt_token_ids_sha256": _sha256_json(prompt_ids),
        "generated_token_ids": raw_token_ids,
        "generated_token_count": len(raw_token_ids),
        "generated_token_ids_sha256": _sha256_json(raw_token_ids),
        "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        "eos_token_ids": eos_ids,
        "eos_sources": {name: sorted(ids) for name, ids in eos_sources.items()},
        "stop_token_id": raw_token_ids[eos_index] if eos_index is not None else None,
        "max_new_tokens": max_new_tokens,
    }


def audit_path_for(output_path):
    return Path(str(output_path) + ".audit.jsonl")


def _open_private_directory_chain(path):
    """Create/open each directory component without following symlinks (POSIX)."""
    if os.name != "posix" or getattr(os, "O_DIRECTORY", None) is None or getattr(os, "O_NOFOLLOW", None) is None:
        raise OSError("Secure generation artifacts require POSIX O_DIRECTORY and O_NOFOLLOW")
    absolute = Path(os.path.abspath(os.fspath(path)))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(absolute.anchor, flags)
    try:
        for component in absolute.parts[1:]:
            if component in ("", "."):
                continue
            try:
                next_fd = os.open(component, flags, dir_fd=fd)
            except FileNotFoundError:
                try:
                    os.mkdir(component, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        os.fchmod(fd, 0o700)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _append_audit(path, record, create=False):
    dir_fd = _open_private_directory_chain(path.parent)
    fd = None
    try:
        flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        if create:
            flags |= os.O_CREAT | os.O_EXCL
        fd = os.open(path.name, flags, 0o600, dir_fd=dir_fd)
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise OSError("Audit ledger is not a regular file")
        if opened_stat.st_mode & 0o077:
            raise OSError("Audit ledger permissions are too permissive; expected private mode")
        stream = os.fdopen(fd, "a", encoding="utf-8")
        fd = None
        with stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd is not None:
            os.close(fd)
        os.close(dir_fd)


def write_outputs(path, outputs):
    dir_fd = _open_private_directory_chain(path.parent)
    serialized = json.dumps(outputs, ensure_ascii=False, indent=2) + "\n"
    data = serialized.encode("utf-8")
    temp_name = f".{path.name}.tmp-{secrets.token_hex(8)}"
    fd = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(temp_name, flags, 0o600, dir_fd=dir_fd)
        stream = os.fdopen(fd, "wb")
        fd = None
        with stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp_name, path.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)
        os.fsync(dir_fd)
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temp_name, dir_fd=dir_fd)
        except FileNotFoundError:
            pass
        os.close(dir_fd)
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="Model ID or local directory")
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--offline", action="store_true", help="Load only from local model cache/directory")
    p.add_argument("--character-prompt", type=Path, required=True, help="System prompt file for paired condition")
    p.add_argument("--max-new-tokens", type=int, required=True, help="Explicit per-run budget; no fixed default")
    args = p.parse_args()
    if args.max_new_tokens < 1:
        p.error("--max-new-tokens must be positive")
    try:
        rows = validate_cases([json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()])
        character = args.character_prompt.read_text(encoding="utf-8").strip()
        if not character:
            p.error("Character prompt file must not be empty")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    audit_path = audit_path_for(args.output)
    if args.output.exists() or audit_path.exists():
        p.error("Output or audit ledger already exists; use a fresh run path to preserve prior artifacts")
    run_id = str(uuid4())
    header = {
        "type": "run_start",
        "schema_version": 1,
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "max_new_tokens": args.max_new_tokens,
        "case_count": len(rows),
        "cases_sha256": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        "character_prompt_sha256": hashlib.sha256(character.encode("utf-8")).hexdigest(),
        "sampling": {"do_sample": False},
    }
    _append_audit(audit_path, header, create=True)
    attempts = []
    outputs = {}
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        tok = AutoTokenizer.from_pretrained(args.model, local_files_only=args.offline)
        model = AutoModelForCausalLM.from_pretrained(
            args.model, local_files_only=args.offline, torch_dtype="auto", device_map="auto"
        )
        _append_audit(audit_path, {
            "type": "model_loaded",
            "run_id": run_id,
            "model_revision": getattr(getattr(model, "config", None), "_commit_hash", None) or args.model,
            "model_revision_is_pinned": bool(getattr(getattr(model, "config", None), "_commit_hash", None)),
            "tokenizer_revision": getattr(tok, "_commit_hash", None) or getattr(tok, "init_kwargs", {}).get("revision"),
            "tokenizer_revision_is_pinned": bool(getattr(tok, "_commit_hash", None)),
            "tokenizer_name_or_path": getattr(tok, "name_or_path", None),
        })
        all_complete = True
        for row in rows:
            outputs[row["id"]] = {}
            for condition, system_prompt in (("base", None), ("character_prompt", character)):
                messages = build_messages(row, system_prompt)
                try:
                    result = generate(model, tok, torch, messages, args.max_new_tokens)
                    result.update({"type": "generation_attempt", "run_id": run_id, "case_id": row["id"], "condition": condition})
                except Exception as exc:
                    result = {
                        "type": "generation_attempt", "run_id": run_id, "case_id": row["id"],
                        "condition": condition, "completion_status": "error",
                        "completion_reason": "generation_exception", "error": f"{type(exc).__name__}: {exc}",
                        "response_text": "", "response_sha256": hashlib.sha256(b"").hexdigest(),
                        "max_new_tokens": args.max_new_tokens, "generated_token_ids": [],
                        "generated_token_count": 0, "generated_token_ids_sha256": _sha256_json([]),
                    }
                _append_audit(audit_path, result)
                attempts.append(result)
                outputs[row["id"]][condition] = result.get("response_text", "")
                all_complete = all_complete and result.get("completion_status") == "complete"
        output_sha256 = write_outputs(args.output, outputs) if all_complete else None
        summary = {
            "type": "run_summary", "run_id": run_id,
            "status": "complete" if all_complete else "incomplete",
            "expected_attempts": len(rows) * 2, "recorded_attempts": len(attempts),
            "complete_attempts": sum(a.get("completion_status") == "complete" for a in attempts),
            "failed_attempts": sum(a.get("completion_status") != "complete" for a in attempts),
            "output_sha256": output_sha256, "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        _append_audit(audit_path, summary)
        if not all_complete:
            print(f"Run {run_id} incomplete; partial responses and audit records preserved. No paired output file published.")
            return
        print(f"Run {run_id} complete: {len(outputs)} paired cases. Audit ledger: {audit_path}")
    except Exception as exc:
        _append_audit(audit_path, {
            "type": "run_failure", "run_id": run_id,
            "error": f"{type(exc).__name__}: {exc}",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        _append_audit(audit_path, {
            "type": "run_summary", "run_id": run_id, "status": "incomplete",
            "expected_attempts": len(rows) * 2, "recorded_attempts": len(attempts),
            "complete_attempts": sum(a.get("completion_status") == "complete" for a in attempts),
            "failed_attempts": sum(a.get("completion_status") != "complete" for a in attempts),
            "output_sha256": None, "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        raise


if __name__ == "__main__":
    main()
