#!/usr/bin/env python3
"""Re-bind semantic decisions to the current blinded alias map.

The blinded identity map is regenerated (randomised) on every prepare run, so a
decision produced under a previous run's map carries a stale alias. The
response_sha256 recorded on each decision is the evidence link to the exact
response text that was graded, so decisions are re-bound to the current alias by
digest plus case id. A decision whose digest does not bind to exactly one
population row is dropped and will be regraded; nothing is ever re-labelled by
alias alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=pathlib.Path, required=True,
                        help="Current prepared batch with candidate_alias/case_id/response_sha256")
    parser.add_argument("--decisions", type=pathlib.Path, required=True,
                        help="Decision JSONL file or directory of decision JSONL files")
    parser.add_argument("--out-file", type=pathlib.Path)
    parser.add_argument("--out-dir", type=pathlib.Path)
    parser.add_argument("--shard-count", type=int, default=30)
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args()

    requests = read_jsonl(args.requests)
    by_digest: dict[str, list[tuple[int, str, str]]] = {}
    for index, row in enumerate(requests):
        by_digest.setdefault(row["response_sha256"], []).append(
            (index, row["candidate_alias"], row["case_id"]))

    files: list[pathlib.Path] = []
    if args.decisions.is_dir():
        files = sorted(args.decisions.rglob("*.jsonl"))
    elif args.decisions.exists():
        files = [args.decisions]

    kept: dict[tuple[str, str], dict[str, Any]] = {}
    dropped: list[dict[str, Any]] = []
    duplicate = 0
    relabelled = 0
    for path in files:
        for decision in read_jsonl(path):
            digest = decision.get("response_sha256")
            case_id = decision.get("case_id")
            hits = [h for h in by_digest.get(digest, []) if h[2] == case_id]
            if len(hits) != 1:
                dropped.append({"case_id": case_id,
                                "stale_alias": decision.get("candidate_alias"),
                                "reason": "digest does not bind to exactly one population row"})
                continue
            index, alias, _ = hits[0]
            key = (alias, case_id)
            if key in kept:
                duplicate += 1
                continue
            if decision.get("candidate_alias") != alias:
                relabelled += 1
            decision = dict(decision)
            decision["candidate_alias"] = alias
            decision["_population_index"] = index
            kept[key] = decision

    shard_count = max(1, args.shard_count)
    total = len(requests)
    per_shard: dict[int, list[dict[str, Any]]] = {}
    for decision in kept.values():
        index = decision.pop("_population_index")
        shard = index * shard_count // total if total else 0
        per_shard.setdefault(shard, []).append(
            {k: v for k, v in decision.items() if k != "_population_index"})

    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for shard, rows in per_shard.items():
            rows.sort(key=lambda d: d["case_id"])
            payload = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                              for r in rows)
            (args.out_dir / f"shard-{shard}.jsonl").write_text(payload, encoding="utf-8")
    if args.out_file:
        args.out_file.parent.mkdir(parents=True, exist_ok=True)
        ordered = [kept[k] for k in sorted(kept)]
        for row in ordered:
            row.pop("_population_index", None)
        payload = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                          for r in ordered)
        args.out_file.write_text(payload, encoding="utf-8")

    report = {
        "schema_version": "vectolith-ash-prime-decision-rebind/1.0",
        "population_count": total,
        "decisions_read": sum(len(read_jsonl(p)) for p in files),
        "decisions_kept": len(kept),
        "decisions_relabelled": relabelled,
        "decisions_dropped": len(dropped),
        "duplicates_skipped": duplicate,
        "shard_count": shard_count,
        "outputs": sorted(p.name for p in args.out_dir.glob("*.jsonl")) if args.out_dir else [],
        "dropped": dropped,
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("population_count", "decisions_read", "decisions_kept",
                       "decisions_relabelled", "decisions_dropped", "duplicates_skipped")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
