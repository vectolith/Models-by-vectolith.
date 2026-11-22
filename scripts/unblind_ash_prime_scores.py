#!/usr/bin/env python3
"""Unblind completed score records only in a restricted condition-map directory."""
import argparse
import json
import os
import stat
from pathlib import Path

from run_ash_prime_blind_eval import CONDITIONS, DIMENSIONS, read_jsonl, validate_cases, validate_scores


def validate_mapping(mapping, cases):
    case_ids = {case["id"] for case in validate_cases(cases)}
    if not isinstance(mapping, dict) or set(mapping) != case_ids:
        raise ValueError("Condition mapping case IDs must exactly match the evaluation cases")
    for cid, labels in mapping.items():
        if not isinstance(labels, dict) or set(labels) != {"candidate_1", "candidate_2"}:
            raise ValueError(f"{cid}: mapping must contain exactly both blind labels")
        if any(not isinstance(value, str) for value in labels.values()) or set(labels.values()) != CONDITIONS:
            raise ValueError(f"{cid}: mapping must contain both conditions exactly once")
    return mapping


def _open_directory_without_symlink_ancestors(path):
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(absolute.anchor, flags)
    try:
        for component in absolute.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def load_restricted_mapping(path):
    if path.is_symlink():
        raise ValueError("Condition-map file must not be a symlink")
    if os.name == "posix":
        dir_fd = _open_directory_without_symlink_ancestors(path.parent)
        try:
            if os.fstat(dir_fd).st_mode & 0o077:
                raise PermissionError("Condition map directory must be private (no group/other permissions)")
            fd = os.open(path.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=dir_fd)
            try:
                file_stat = os.fstat(fd)
                if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_mode & 0o077:
                    raise PermissionError("Condition map must be a private regular file (no group/other permissions)")
                with os.fdopen(fd, "r", encoding="utf-8") as stream:
                    fd = None
                    return json.load(stream)
            finally:
                if fd is not None:
                    os.close(fd)
        finally:
            os.close(dir_fd)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Condition map and parent directory must not be symlinks")
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def build_summary(scores, cases, mapping):
    validate_scores(scores, cases)
    mapping = validate_mapping(mapping, cases)
    accum = {condition: {dimension: [] for dimension in DIMENSIONS} for condition in CONDITIONS}
    flags = {condition: [] for condition in CONDITIONS}
    reviewer_pairs, reviewers = {}, set()
    for row in scores:
        cid, label, dimension, score = row["case_id"], row["blind_label"], row["dimension"], row.get("score")
        condition = mapping[cid][label]
        if score is not None:
            accum[condition][dimension].append(score)
        flags[condition].extend(row.get("gate_flags", []))
        reviewer = row["reviewer_id"]
        reviewers.add(reviewer)
        reviewer_pairs.setdefault((reviewer, cid, dimension), {})[condition] = score
    paired = {dimension: [] for dimension in DIMENSIONS}
    complete_pairs = 0
    for (_, _, dimension), pair in reviewer_pairs.items():
        if set(pair) == CONDITIONS and pair["base"] is not None and pair["character_prompt"] is not None:
            paired[dimension].append(pair["character_prompt"] - pair["base"])
            complete_pairs += 1
    return {
        "condition_dimension_means": {condition: {d: (round(sum(v)/len(v), 3) if v else None) for d, v in dimensions.items()} for condition, dimensions in accum.items()},
        "condition_dimension_counts": {condition: {d: len(v) for d, v in dimensions.items()} for condition, dimensions in accum.items()},
        "paired_difference_means_character_minus_base": {d: (round(sum(v)/len(v), 3) if v else None) for d, v in paired.items()},
        "paired_difference_counts": {d: len(v) for d, v in paired.items()},
        "gate_flags_by_condition": {condition: sorted(set(v)) for condition, v in flags.items()},
        "scored_records": len(scores), "unique_reviewers": len(reviewers), "complete_reviewer_case_pairs": complete_pairs,
        "note": "Restricted post-review descriptive summary. No statistical significance or model-quality claim is established."
    }


def write_restricted_summary(output, map_path, summary):
    if output.parent.resolve() != map_path.parent.resolve() or output.name == map_path.name:
        raise ValueError("Unblinded summary must be written beside the condition map, inside the same restricted directory")
    if output.is_symlink():
        raise ValueError("Restricted output file must not be a symlink")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    serialized = json.dumps(summary, indent=2) + "\n"
    if os.name == "posix":
        dir_fd = _open_directory_without_symlink_ancestors(output.parent)
        try:
            os.fchmod(dir_fd, 0o700)
            fd = os.open(output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dir_fd)
            try:
                os.fchmod(fd, 0o600)
                stream = os.fdopen(fd, "w", encoding="utf-8")
                fd = None
                with stream:
                    stream.write(serialized)
            finally:
                if fd is not None:
                    os.close(fd)
        finally:
            os.close(dir_fd)
    else:
        if output.parent.is_symlink():
            raise ValueError("Restricted output parent must not be a symlink")
        with output.open("x", encoding="utf-8") as stream:
            stream.write(serialized)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/ash-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--scores", type=Path, required=True, help="Completed blind score JSONL")
    p.add_argument("--map", type=Path, required=True, help="Restricted blind-label-map.json")
    p.add_argument("--output", type=Path, required=True, help="Unblinded summary path inside the map directory")
    args = p.parse_args()
    try:
        cases, scores = read_jsonl(args.cases), read_jsonl(args.scores)
        mapping = validate_mapping(load_restricted_mapping(args.map), cases)
        summary = build_summary(scores, cases, mapping)
        write_restricted_summary(args.output, args.map, summary)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
