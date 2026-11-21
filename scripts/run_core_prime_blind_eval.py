#!/usr/bin/env python3
"""Prepare anonymized evaluator sheets and summarize scores; no inference performed."""
import argparse
import json
import os
import random
from pathlib import Path

DIMENSIONS = ["judgment", "naturalness", "situational_fit", "independence", "humor_timing", "useful_originality", "restraint", "grounding_calibration", "task_craft", "relational_intelligence", "long_context_consistency", "repair"]
CONDITIONS = {"base", "character_prompt"}
ALLOWED_FLAGS = {"safety_regression", "factuality_regression", "calibration_regression", "intent_following_regression", "capability_regression"}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


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


def make_sheet(cases, outputs, seed):
    validate_cases(cases)
    if not isinstance(outputs, dict):
        raise ValueError("Outputs must be a mapping")
    case_ids = {case["id"] for case in cases}
    extra_ids = set(outputs) - case_ids
    missing_ids = case_ids - set(outputs)
    if extra_ids or missing_ids:
        raise ValueError(f"Output case IDs mismatch; missing={sorted(missing_ids)}, extra={sorted(extra_ids)}")
    rng = random.Random(seed)
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
    sheet_resolved, map_resolved = sheet_dir.resolve(), map_dir.resolve()
    if sheet_resolved == map_resolved or sheet_resolved in map_resolved.parents or map_resolved in sheet_resolved.parents:
        raise ValueError("Evaluator-facing and condition-map directories must be disjoint")
    if (sheet_resolved / "blind-label-map.json").exists():
        raise ValueError("Evaluator-facing directory already contains a condition map; use a clean directory")
    if (sheet_resolved / "blind-score-sheet.jsonl").exists():
        raise ValueError("Evaluator-facing score sheet already exists; use a fresh directory to preserve prior results")
    if (map_resolved / "blind-label-map.json").exists():
        raise ValueError("Condition mapping already exists; use a fresh restricted directory to preserve prior results")
    return sheet_resolved, map_resolved


def write_restricted_mapping(map_dir, mapping):
    map_dir.mkdir(parents=True, exist_ok=True)
    map_file = map_dir / "blind-label-map.json"
    if map_file.exists():
        raise ValueError("Refusing to overwrite an existing condition mapping")
    if os.name == "posix":
        map_dir.chmod(0o700)
    map_file.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    if os.name == "posix":
        map_file.chmod(0o600)


def validate_scores(scores, cases):
    case_dimensions = {case["id"]: case["dimension"] for case in validate_cases(cases)}
    for row in scores:
        cid = row.get("case_id") if isinstance(row, dict) else None
        if cid not in case_dimensions:
            raise ValueError(f"Score record references unknown case_id: {cid}")
        if row.get("dimension") != case_dimensions[cid]:
            raise ValueError(f"{cid}: score dimension does not match evaluation case")
    return scores


def summarize(scores):
    accum = {d: [] for d in DIMENSIONS}
    seen = set()
    flags = []
    for row in scores:
        cid, d, score = row.get("case_id"), row.get("dimension"), row.get("score")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("Each score record requires a nonempty case_id")
        if d not in accum:
            raise ValueError(f"Unknown dimension: {d}")
        key = (cid, d)
        if key in seen:
            raise ValueError("Duplicate score case_id/dimension pair")
        seen.add(key)
        if score is not None and (type(score) is not int or not 1 <= score <= 5):
            raise ValueError("Scores must be integer 1-5 or null")
        row_flags = row.get("gate_flags", [])
        if not isinstance(row_flags, list) or any(flag not in ALLOWED_FLAGS for flag in row_flags):
            raise ValueError("Invalid gate_flags")
        if score is not None:
            accum[d].append(score)
        flags.extend(row_flags)
    return {"dimension_means": {d: (round(sum(v)/len(v), 3) if v else None) for d, v in accum.items()},
            "dimension_counts": {d: len(v) for d, v in accum.items()}, "gate_flags": sorted(set(flags)),
            "scored_records": len(scores), "note": "Descriptive summary only; does not establish statistical significance or model quality."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--outputs", type=Path, help="JSON mapping case ID to condition name and response text")
    p.add_argument("--scores", type=Path, help="JSONL scoring records")
    p.add_argument("--output", type=Path, required=True, help="Evaluator-facing output directory")
    p.add_argument("--map-output", type=Path, help="Restricted condition-map directory; defaults to a sibling directory")
    p.add_argument("--seed", type=int, default=20261121)
    args = p.parse_args()
    cases = read_jsonl(args.cases)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.scores and (args.output / "summary.json").exists():
        p.error("summary.json already exists; use a fresh output directory to preserve prior results")
    if args.outputs:
        sheet, mapping = make_sheet(cases, json.loads(args.outputs.read_text(encoding="utf-8")), args.seed)
        map_dir = args.map_output or args.output.parent / (args.output.name + "-restricted")
        try:
            sheet_dir, map_dir = validate_output_directories(args.output, map_dir)
        except ValueError as exc:
            p.error(str(exc))
        write_jsonl(sheet_dir / "blind-score-sheet.jsonl", sheet)
        write_restricted_mapping(map_dir, mapping)
    if args.scores:
        score_rows = validate_scores(read_jsonl(args.scores), cases)
        summary_path = args.output / "summary.json"
        result = summarize(score_rows)
        summary_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
