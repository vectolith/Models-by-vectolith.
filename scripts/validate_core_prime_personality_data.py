#!/usr/bin/env python3
"""Validate Core Prime personality draft JSONL assets without dependencies."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "trajectories": ROOT / "data/personality/core-prime-multiturn-trajectories-v1.jsonl",
    "preferences": ROOT / "data/personality/core-prime-contrastive-preferences-v1.jsonl",
    "micro": ROOT / "data/personality/core-prime-behavioral-micro-scenarios-v1.jsonl",
}

def load_lines(path):
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return records

def validate():
    traj = load_lines(FILES["trajectories"])
    pref = load_lines(FILES["preferences"])
    micro = load_lines(FILES["micro"])
    for name, rows in (("trajectories", traj), ("preferences", pref), ("micro", micro)):
        ids = [r.get("id") for r in rows]
        if any(not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"{name}: missing or duplicate IDs")
        if any(r.get("split") not in {"train", "holdout"} for r in rows):
            raise ValueError(f"{name}: invalid split label")
    for r in traj:
        turns = r.get("turns", [])
        if len(turns) < 4 or len(turns) % 2:
            raise ValueError(f"{r['id']}: expected >=4 even turns")
        for i, turn in enumerate(turns):
            expected = "user" if i % 2 == 0 else "assistant"
            if turn.get("role") != expected or not isinstance(turn.get("text"), str) or not turn["text"].strip():
                raise ValueError(f"{r['id']}: malformed turn {i}")
    all_ids = [r["id"] for rows in (traj, pref, micro) for r in rows]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("IDs must be globally unique across datasets")
    for r in pref:
        if r.get("preference") not in {"A", "B"}:
            raise ValueError(f"{r['id']}: preference must be A or B")
        if r["preferred"].get("label") != r["preference"] or r["rejected"].get("label") == r["preference"]:
            raise ValueError("preference labels contradict preferred/rejected for " + r["id"])
        for candidate in ("preferred", "rejected"):
            if not isinstance(r.get(candidate, {}).get("text"), str) or not r[candidate]["text"].strip():
                raise ValueError(f"{r['id']}: missing candidate text")
        if not r.get("reason", "").strip():
            raise ValueError(f"{r['id']}: missing observable rationale")
    train_ids = {r["id"] for r in traj if r["split"] == "train"}
    holdout_ids = {r["id"] for r in traj if r["split"] == "holdout"}
    if train_ids & holdout_ids:
        raise ValueError("trajectory train/holdout ID overlap")
    for r in micro:
        if not r.get("trait") or not r.get("scenario") or not r.get("prompt") or not r.get("desired_observable_behavior"):
            raise ValueError(f"{r.get('id')}: incomplete micro scenario")
    print(f"OK: {len(traj)} trajectories ({len(train_ids)} train, {len(holdout_ids)} holdout); {len(pref)} preference pairs; {len(micro)} micro scenarios")
if __name__ == "__main__":
    validate()
