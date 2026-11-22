#!/usr/bin/env python3
"""Prepare anonymized evaluator sheets and summarize scores; no inference performed."""
import argparse
import hashlib
import json
import os
import random
import re
import secrets
from pathlib import Path

DIMENSIONS = ["judgment", "naturalness", "situational_fit", "independence", "humor_timing", "useful_originality", "restraint", "grounding_calibration", "task_craft", "relational_intelligence", "long_context_consistency", "repair"]
CONDITIONS = {"base", "character_prompt"}
BLIND_LABELS = {"candidate_1", "candidate_2"}
ALLOWED_FLAGS = {"safety_regression", "factuality_regression", "calibration_regression", "intent_following_regression", "capability_regression"}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def validate_cases(cases):
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation cases must be a nonempty list")
    ids = [case.get("id") if isinstance(case, dict) else None for case in cases]
    if any(not isinstance(x, str) or not x.strip() for x in ids):
        raise ValueError("Case IDs must be nonempty strings")
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case IDs detected")
    for case in cases:
        if not {"prompt", "test", "dimension"}.issubset(case) or case["dimension"] not in DIMENSIONS:
            raise ValueError("Invalid case fields or dimension")
        if not isinstance(case["prompt"], str) or not case["prompt"].strip() or not isinstance(case["test"], str) or not case["test"].strip():
            raise ValueError("Case prompt and test must be nonempty strings")
        if not isinstance(case.get("context", ""), str):
            raise ValueError("Case context must be a string")
    return cases


def make_sheet(cases, outputs, seed=None):
    validate_cases(cases)
    if not isinstance(outputs, dict):
        raise ValueError("Outputs must be a mapping")
    case_ids = {case["id"] for case in cases}
    extra_ids = set(outputs) - case_ids
    missing_ids = case_ids - set(outputs)
    if extra_ids or missing_ids:
        raise ValueError(f"Output case IDs mismatch; missing={sorted(missing_ids)}, extra={sorted(extra_ids)}")
    # Actual evaluator sheets use an unpredictable permutation. A fixed seed is
    # supported only for deterministic unit tests and never exposed by the CLI.
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    sheet, mappings = [], {}
    for case in cases:
        case_outputs = outputs[case["id"]]
        if not isinstance(case_outputs, dict) or set(case_outputs) != CONDITIONS:
            raise ValueError(f'{case["id"]}: expected exactly base and character_prompt conditions')
        candidates = list(case_outputs.items())
        if any(not isinstance(response, str) or not response.strip() for _, response in candidates):
            raise ValueError(f'{case["id"]}: responses must be nonempty strings')
        rng.shuffle(candidates)
        response_rows = [{"blind_label": f"candidate_{i+1}", "response": response} for i, (_, response) in enumerate(candidates)]
        mappings[case["id"]] = {f"candidate_{i+1}": name for i, (name, _) in enumerate(candidates)}
        sheet.append({"case_id": case["id"], "prompt": case["prompt"], "context": case.get("context", ""),
                      "test": case["test"], "dimension": case["dimension"], "responses": response_rows})
    return sheet, mappings


def validate_output_directories(sheet_dir, map_dir):
    # Reject the mapping-directory symlink before canonicalizing paths. Returning
    # resolved paths would silently bypass the writer's own symlink guard.
    if map_dir.is_symlink():
        raise ValueError("Condition-map directory must not be a symlink")
    sheet_resolved, map_resolved = sheet_dir.resolve(), map_dir.resolve()
    if sheet_resolved == map_resolved or sheet_resolved in map_resolved.parents or map_resolved in sheet_resolved.parents:
        raise ValueError("Evaluator-facing and condition-map directories must be disjoint")
    if (sheet_resolved / "blind-label-map.json").exists():
        raise ValueError("Evaluator-facing directory already contains a condition map; use a clean directory")
    if (sheet_resolved / "blind-score-sheet.jsonl").exists():
        raise ValueError("Evaluator-facing score sheet already exists; use a fresh directory to preserve prior results")
    if (map_resolved / "blind-label-map.json").exists():
        raise ValueError("Condition mapping already exists; use a fresh restricted directory to preserve prior results")
    # Keep the original map path so the no-follow checks remain effective if
    # the path changes after this validation step.
    return sheet_dir, map_dir


def _open_private_directory_chain(path):
    """Open/create every path component without following symlinks (POSIX)."""
    # Fail closed: silently omitting either flag would weaken traversal checks.
    if getattr(os, "O_DIRECTORY", None) is None or getattr(os, "O_NOFOLLOW", None) is None:
        raise OSError("Secure condition-map publication requires O_DIRECTORY and O_NOFOLLOW")
    absolute = Path(os.path.abspath(os.fspath(path)))
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(absolute.anchor, dir_flags)
    try:
        for component in absolute.parts[1:]:
            if component in ("", "."):
                continue
            try:
                next_fd = os.open(component, dir_flags, dir_fd=fd)
            except FileNotFoundError:
                try:
                    os.mkdir(component, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                next_fd = os.open(component, dir_flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        os.fchmod(fd, 0o700)
        return fd
    except BaseException:
        os.close(fd)
        raise


def write_restricted_mapping(map_dir, mapping):
    if map_dir.is_symlink():
        raise ValueError("Condition-map directory must not be a symlink")
    map_file = map_dir / "blind-label-map.json"
    serialized = json.dumps(mapping, indent=2) + "\n"
    if os.name == "posix":
        dir_fd = _open_private_directory_chain(map_dir)
        temp_name = None
        created_temp = False
        published = False
        fd = None
        try:
            file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            for _ in range(8):
                temp_name = f".{map_file.name}.tmp-{secrets.token_hex(8)}"
                try:
                    fd = os.open(temp_name, file_flags, 0o600, dir_fd=dir_fd)
                    created_temp = True
                    break
                except FileExistsError:
                    continue
            if fd is None:
                raise FileExistsError("Could not create an exclusive temporary mapping file")
            os.fchmod(fd, 0o600)
            stream = os.fdopen(fd, "w", encoding="utf-8")
            fd = None
            with stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
            # Atomically publish the complete mapping without replacing a prior one.
            os.link(temp_name, map_file.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)
            published = True
            os.unlink(temp_name, dir_fd=dir_fd)
            created_temp = False
            os.fsync(dir_fd)
        except BaseException:
            if fd is not None:
                os.close(fd)
            if created_temp and temp_name is not None:
                try:
                    os.unlink(temp_name, dir_fd=dir_fd)
                except FileNotFoundError:
                    pass
            if published:
                try:
                    os.unlink(map_file.name, dir_fd=dir_fd)
                    os.fsync(dir_fd)
                except OSError:
                    pass
            raise
        finally:
            os.close(dir_fd)
    else:
        map_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if map_dir.is_symlink():
            raise ValueError("Condition-map directory must not be a symlink")
        with map_file.open("x", encoding="utf-8") as stream:
            stream.write(serialized)


def validate_scores(scores, cases):
    case_dimensions = {case["id"]: case["dimension"] for case in validate_cases(cases)}
    seen = set()
    for row in scores:
        if not isinstance(row, dict):
            raise ValueError("Each score record must be an object")
        cid, label, dimension = row.get("case_id"), row.get("blind_label"), row.get("dimension")
        reviewer, score = row.get("reviewer_id"), row.get("score")
        if "score" not in row:
            raise ValueError("Each score record must include score (1-5 or null)")
        if not isinstance(cid, str) or cid not in case_dimensions:
            raise ValueError(f"Score record references unknown case_id: {cid}")
        if not isinstance(label, str) or label not in BLIND_LABELS:
            raise ValueError(f"{cid}: blind_label must be candidate_1 or candidate_2")
        if not isinstance(dimension, str) or dimension != case_dimensions[cid]:
            raise ValueError(f"{cid}: score dimension does not match evaluation case")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("Each score record requires a nonempty pseudonymous reviewer_id")
        if score is not None and (type(score) is not int or not 1 <= score <= 5):
            raise ValueError("Scores must be integer 1-5 or null")
        flags = row.get("gate_flags", [])
        if not isinstance(flags, list) or any(not isinstance(flag, str) or flag not in ALLOWED_FLAGS for flag in flags):
            raise ValueError("Invalid gate_flags")
        key = (reviewer, cid, label, dimension)
        if key in seen:
            raise ValueError("Duplicate reviewer/case/blind-label/dimension score record")
        seen.add(key)
    return scores


def summarize(scores):
    accum = {d: [] for d in DIMENSIONS}
    seen, flags = set(), []
    label_counts = {label: 0 for label in BLIND_LABELS}
    reviewers, case_labels, reviewer_case_labels = set(), set(), {}
    for row in scores:
        cid, label, d, score = row.get("case_id"), row.get("blind_label"), row.get("dimension"), row.get("score")
        reviewer = row.get("reviewer_id")
        if "score" not in row:
            raise ValueError("Each score record must include score (1-5 or null)")
        if not isinstance(cid, str) or not cid.strip() or not isinstance(label, str) or label not in BLIND_LABELS or not isinstance(d, str) or d not in accum:
            raise ValueError("Score record requires case_id, blind_label and valid dimension")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("Each score record requires reviewer_id")
        key = (reviewer, cid, label, d)
        if key in seen:
            raise ValueError("Duplicate reviewer/case/blind-label/dimension score record")
        seen.add(key)
        if score is not None and (type(score) is not int or not 1 <= score <= 5):
            raise ValueError("Scores must be integer 1-5 or null")
        row_flags = row.get("gate_flags", [])
        if not isinstance(row_flags, list) or any(not isinstance(flag, str) or flag not in ALLOWED_FLAGS for flag in row_flags):
            raise ValueError("Invalid gate_flags")
        if score is not None:
            accum[d].append(score)
        flags.extend(row_flags)
        label_counts[label] += 1
        reviewers.add(reviewer)
        case_labels.add((cid, label))
        reviewer_case_labels.setdefault((reviewer, cid), set()).add(label)
    complete_pairs = sum(1 for labels in reviewer_case_labels.values() if labels == BLIND_LABELS)
    return {"dimension_means": {d: (round(sum(v)/len(v), 3) if v else None) for d, v in accum.items()},
            "dimension_counts": {d: len(v) for d, v in accum.items()},
            "blind_label_record_counts": label_counts, "gate_flags": sorted(set(flags)),
            "scored_records": len(scores), "unique_reviewers": len(reviewers),
            "case_label_coverage": len(case_labels), "complete_reviewer_case_pairs": complete_pairs,
            "note": "Pooled blinded descriptive summary only; labels are randomized per case and this report does not compare conditions."}


def validate_generation_audit(outputs, cases, audit_rows, output_bytes, cases_bytes, character_prompt_bytes):
    """Fail closed unless outputs, exact inputs and every attempt bind to the audit."""
    case_ids = {case["id"] for case in validate_cases(cases)}
    if not isinstance(outputs, dict) or set(outputs) != case_ids:
        raise ValueError("Audited output case IDs must exactly match evaluation cases")
    for cid, case_outputs in outputs.items():
        if not isinstance(case_outputs, dict) or set(case_outputs) != CONDITIONS:
            raise ValueError(f"{cid}: audited outputs must contain exactly both experiment conditions")
    if not isinstance(audit_rows, list) or len(audit_rows) < 3 or any(not isinstance(row, dict) for row in audit_rows):
        raise ValueError("Generation audit ledger is missing or contains non-object records")
    allowed_types = {"run_start", "model_loaded", "generation_attempt", "run_summary"}
    if any(row.get("type") not in allowed_types for row in audit_rows):
        raise ValueError("Generation audit ledger contains unknown record types")
    header, summary = audit_rows[0], audit_rows[-1]
    if header.get("type") != "run_start" or header.get("schema_version") != 1:
        raise ValueError("Unsupported or missing audit ledger header")
    if summary.get("type") != "run_summary" or summary.get("status") != "complete":
        raise ValueError("Audit ledger does not declare a complete run")
    if sum(row.get("type") == "run_start" for row in audit_rows) != 1 or sum(row.get("type") == "run_summary" for row in audit_rows) != 1:
        raise ValueError("Audit ledger must contain exactly one header and one summary")
    if sum(row.get("type") == "model_loaded" for row in audit_rows) != 1:
        raise ValueError("Audit ledger must contain exactly one model-load record")
    model_loaded = next(row for row in audit_rows if row.get("type") == "model_loaded")
    if not isinstance(header.get("model"), str) or not header["model"].strip():
        raise ValueError("Audit header is missing model identity")
    if model_loaded.get("run_id") != header.get("run_id"):
        raise ValueError("Model-load provenance record has a mismatched run ID")
    for field in ("model_revision", "tokenizer_name_or_path"):
        if not isinstance(model_loaded.get(field), str) or not model_loaded[field].strip():
            raise ValueError(f"Audit model-load provenance is missing {field}")
    if header.get("case_count") != len(cases) or type(header.get("case_count")) is not int:
        raise ValueError("Audit header case count does not match evaluation cases")
    if header.get("cases_sha256") != hashlib.sha256(cases_bytes).hexdigest():
        raise ValueError("Audit header is not bound to the exact evaluation case file")
    if header.get("character_prompt_sha256") != hashlib.sha256(character_prompt_bytes).hexdigest():
        raise ValueError("Audit header is not bound to the exact character prompt")
    run_id = header.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip() or summary.get("run_id") != run_id:
        raise ValueError("Audit run IDs do not match")
    budget = header.get("max_new_tokens")
    if type(budget) is not int or budget < 1:
        raise ValueError("Audit header lacks an explicit positive generation budget")
    if summary.get("output_sha256") != hashlib.sha256(output_bytes).hexdigest():
        raise ValueError("Output file hash does not match audit summary")
    attempts = [row for row in audit_rows if row.get("type") == "generation_attempt"]
    expected = {(cid, condition) for cid in case_ids for condition in CONDITIONS}
    observed = set()
    for row in attempts:
        cid, condition = row.get("case_id"), row.get("condition")
        key = (cid, condition)
        if row.get("run_id") != run_id or key not in expected or key in observed:
            raise ValueError("Audit attempts contain an unknown, duplicated or mismatched case/condition")
        observed.add(key)
        if row.get("completion_status") != "complete" or row.get("completion_reason") != "eos_token":
            raise ValueError(f"{cid}/{condition}: incomplete or conflicting generation metadata")
        if row.get("max_new_tokens") != budget:
            raise ValueError(f"{cid}/{condition}: attempt budget differs from run budget")
        native = row.get("native_stop_metadata")
        if native is not None and native not in {"eos", "eos_token", "end_of_sequence", "stop", "completed"}:
            raise ValueError(f"{cid}/{condition}: contradictory native stop metadata")
        response = row.get("response_text")
        if not isinstance(response, str) or not response.strip() or outputs[cid].get(condition) != response:
            raise ValueError(f"{cid}/{condition}: response text is missing or does not match audit")
        response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest()
        if row.get("response_sha256") != response_hash:
            raise ValueError(f"{cid}/{condition}: response hash mismatch")
        token_ids = row.get("generated_token_ids")
        eos_ids = row.get("eos_token_ids")
        if not isinstance(token_ids, list) or not token_ids or any(type(t) is not int for t in token_ids):
            raise ValueError(f"{cid}/{condition}: invalid raw generation token IDs")
        if not isinstance(eos_ids, list) or not eos_ids or any(type(t) is not int for t in eos_ids):
            raise ValueError(f"{cid}/{condition}: missing EOS metadata")
        sources = row.get("eos_sources")
        if not isinstance(sources, dict) or not sources or any(values != eos_ids for values in sources.values()):
            raise ValueError(f"{cid}/{condition}: EOS source metadata conflicts")
        if token_ids[-1] not in eos_ids or row.get("stop_token_id") != token_ids[-1]:
            raise ValueError(f"{cid}/{condition}: EOS stop token is not bound to the final generated token")
        if row.get("generated_token_count") != len(token_ids):
            raise ValueError(f"{cid}/{condition}: token count mismatch")
        token_hash = hashlib.sha256(json.dumps(token_ids, separators=(",", ":")).encode("utf-8")).hexdigest()
        if row.get("generated_token_ids_sha256") != token_hash:
            raise ValueError(f"{cid}/{condition}: raw token hash mismatch")
        prompt_hash = row.get("prompt_token_ids_sha256")
        if not isinstance(prompt_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", prompt_hash):
            raise ValueError(f"{cid}/{condition}: invalid prompt token hash")
        if row.get("prompt_token_count", 0) < 1:
            raise ValueError(f"{cid}/{condition}: prompt token count is missing")
    if observed != expected:
        raise ValueError(f"Audit ledger lacks required generation attempts: {sorted(expected-observed)}")
    if summary.get("expected_attempts") != len(expected) or summary.get("recorded_attempts") != len(expected):
        raise ValueError("Audit summary attempt counts do not match the experiment")
    if summary.get("complete_attempts") != len(expected) or summary.get("failed_attempts") != 0:
        raise ValueError("Audit summary reports incomplete attempts")
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--outputs", type=Path, help="JSON mapping case ID to condition name and response text")
    p.add_argument("--character-prompt", type=Path, help="Exact system prompt file used for the character condition; required with --outputs")
    p.add_argument("--scores", type=Path, help="JSONL scoring records")
    p.add_argument("--output", type=Path, required=True, help="Evaluator-facing output directory")
    p.add_argument("--map-output", type=Path, help="Restricted condition-map directory; defaults to a sibling directory")
    args = p.parse_args()
    cases = read_jsonl(args.cases)
    if args.outputs:
        try:
            if not args.character_prompt:
                p.error("--character-prompt is required when --outputs is supplied")
            cases_bytes = args.cases.read_bytes()
            character_prompt_bytes = args.character_prompt.read_text(encoding="utf-8").strip().encode("utf-8")
            if not character_prompt_bytes:
                p.error("Character prompt file must not be empty")
            output_bytes = args.outputs.read_bytes()
            outputs = json.loads(output_bytes.decode("utf-8"))
            audit_path = Path(str(args.outputs) + ".audit.jsonl")
            audit_rows = read_jsonl(audit_path)
            validate_generation_audit(outputs, cases, audit_rows, output_bytes, cases_bytes, character_prompt_bytes)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            p.error(f"Paired outputs rejected by generation audit: {exc}")
    if args.output.exists() and args.scores and (args.output / "summary.json").exists():
        p.error("summary.json already exists; use a fresh output directory to preserve prior results")
    if args.outputs:
        sheet, mapping = make_sheet(cases, outputs)
        map_dir = args.map_output or args.output.parent / (args.output.name + "-restricted")
        try:
            sheet_dir, map_dir = validate_output_directories(args.output, map_dir)
        except ValueError as exc:
            p.error(str(exc))
        args.output.mkdir(parents=True, exist_ok=True)
        write_jsonl(sheet_dir / "blind-score-sheet.jsonl", sheet)
        write_restricted_mapping(map_dir, mapping)
    if args.scores:
        args.output.mkdir(parents=True, exist_ok=True)
        score_rows = validate_scores(read_jsonl(args.scores), cases)
        summary_path = args.output / "summary.json"
        result = summarize(score_rows)
        with summary_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
