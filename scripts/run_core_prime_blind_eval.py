#!/usr/bin/env python3
"""Prepare anonymized evaluator sheets and summarize scores; no inference performed."""
import argparse
import json
import random
from pathlib import Path

DIMENSIONS = ["judgment","naturalness","situational_fit","independence","humor_timing","useful_originality","restraint","grounding_calibration","task_craft","relational_intelligence","long_context_consistency","repair"]

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\\n" for row in rows), encoding="utf-8")

def make_sheet(cases, outputs, seed):
    rng = random.Random(seed)
    sheet, mappings = [], {}
    for case in cases:
        candidates = list(outputs.get(case["id"], {}).items())
        if len(candidates) < 2:
            raise ValueError(f'{case["id"]}: at least two conditions are required for blind comparison')
        if any(not isinstance(name, str) or not isinstance(response, str) or not response.strip() for name, response in candidates):
            raise ValueError(f'{case["id"]}: condition names and nonempty responses must be strings')
        rng.shuffle(candidates)
        response_rows = [{"blind_label": f"candidate_{i+1}", "response": response} for i, (_, response) in enumerate(candidates)]
        mappings[case["id"]] = {f"candidate_{i+1}": name for i, (name, _) in enumerate(candidates)}
        sheet.append({"case_id": case["id"], "prompt": case["prompt"], "context": case.get("context", ""),
                      "test": case["test"], "dimension": case["dimension"], "responses": response_rows})
    return sheet, mappings

def summarize(scores):
    accum = {d: [] for d in DIMENSIONS}
    flags = []
    allowed_flags = {"safety_regression","factuality_regression","calibration_regression","intent_following_regression","capability_regression"}
    for row in scores:
        d, score = row.get("dimension"), row.get("score")
        if d not in accum: raise ValueError(f"Unknown dimension: {d}")
        if score is not None and (type(score) is not int or not 1 <= score <= 5):
            raise ValueError("Scores must be integer 1-5 or null")
        row_flags = row.get("gate_flags", [])
        if not isinstance(row_flags, list) or any(flag not in allowed_flags for flag in row_flags):
            raise ValueError("Invalid gate_flags")
        if score is not None: accum[d].append(score)
        flags.extend(row_flags)
    return {"dimension_means": {d: (round(sum(v)/len(v), 3) if v else None) for d,v in accum.items()},
            "dimension_counts": {d: len(v) for d,v in accum.items()}, "gate_flags": sorted(set(flags)),
            "scored_records": len(scores), "note": "Descriptive summary only; does not establish statistical significance or model quality."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--outputs", type=Path, help="JSON mapping case ID to condition name and response text")
    p.add_argument("--scores", type=Path, help="JSONL scoring records")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20261121)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = read_jsonl(args.cases)
    if args.outputs:
        sheet, mapping = make_sheet(cases, json.loads(args.outputs.read_text(encoding="utf-8")), args.seed)
        write_jsonl(args.output / "blind-score-sheet.jsonl", sheet)
        (args.output / "blind-label-map.json").write_text(json.dumps(mapping, indent=2) + "\\n", encoding="utf-8")
    if args.scores:
        result = summarize(read_jsonl(args.scores))
        (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\\n", encoding="utf-8")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
