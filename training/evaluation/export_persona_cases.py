
#!/usr/bin/env python3
"""Export the persona evaluation cases into the flat shape the training kernel reads.

The cases themselves are unchanged: this only attaches the reviewed ASH PRIME system
prompt to each prompt so the adapter is evaluated under the same contract it was
trained under.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "evaluation/personality/ash-prime-evaluation-cases-v1.jsonl"
SYSTEM = ROOT / "evaluation/personality/ash-prime-character-system-prompt-v1.txt"
OUT = ROOT / "training/evaluation/persona-cases-v1.jsonl"


def main() -> None:
    system = SYSTEM.read_text(encoding="utf-8").strip()
    rows = []
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        rows.append({"id": case["id"], "system": system, "prompt": case["prompt"]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"cases": len(rows), "output": str(OUT)}))


if __name__ == "__main__":
    main()
