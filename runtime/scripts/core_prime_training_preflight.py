#!/usr/bin/env python3
"""Fail-closed, auditable Core Prime training preflight CLI.

This command validates evidence only. It never downloads weights, allocates
compute, contacts providers, or starts training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from vectolith_runtime.training_preflight import validate_training_preflight  # noqa: E402


def _load_config(path: Path, expected_model: str) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise ValueError("YAML config requires PyYAML; install runtime[training]") from exc
        document = yaml.safe_load(raw)
    else:
        document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError("training configuration must be a mapping")
    metadata = document.get("run_metadata")
    model = document.get("model")
    params = document.get("sft_hyperparameters")
    if not all(isinstance(item, dict) for item in (metadata, model, params)):
        raise ValueError("config requires run_metadata, model, and sft_hyperparameters mappings")
    if not metadata.get("approved_by") or not metadata.get("date"):
        raise ValueError("config approval metadata is incomplete")
    if model.get("base_model") != expected_model:
        raise ValueError("config model.base_model does not match --foundation-model")
    lora = params.get("lora", {})
    if not isinstance(lora, dict) or not isinstance(lora.get("enabled"), bool):
        raise ValueError("config sft_hyperparameters.lora.enabled must be boolean")
    required = ("max_sequence_length", "epochs", "learning_rate",
                "per_device_batch_size", "gradient_accumulation_steps",
                "validation_fraction", "seed")
    missing = [key for key in required if key not in params]
    if missing:
        raise ValueError("training configuration missing: " + ", ".join(missing))
    return {
        "max_seq_length": params["max_sequence_length"],
        "epochs": params["epochs"],
        "learning_rate": params["learning_rate"],
        "per_device_batch_size": params["per_device_batch_size"],
        "gradient_accumulation_steps": params["gradient_accumulation_steps"],
        "validation_fraction": params["validation_fraction"],
        "seed": params["seed"],
        "use_lora": lora["enabled"],
    }


def _artifact_sha256(path: Path) -> str | None:
    """Hash a file or a directory tree with stable relative-path ordering."""
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    if not path.is_dir():
        return None
    tree = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        return None
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        tree.update(relative + b"\\0" + bytes.fromhex(_artifact_sha256(item)) + b"\\n")
    return tree.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--foundation-model", required=True)
    parser.add_argument("--foundation-revision", required=True)
    parser.add_argument("--foundation-selection", required=True, type=Path)
    parser.add_argument("--teacher-manifests", required=True, type=Path)
    parser.add_argument("--holdout-deployment", required=True, type=Path)
    parser.add_argument("--holdout-results", required=True, type=Path)
    parser.add_argument("--execution-manifest", required=True, type=Path)
    parser.add_argument("--training-code-revision", required=True)
    parser.add_argument("--training-config", required=True, type=Path,
                        help="Approved YAML or JSON config")
    parser.add_argument("--report", required=True, type=Path,
                        help="Path for the machine-readable preflight report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = {
        "dataset": args.dataset,
        "foundation_selection": args.foundation_selection,
        "holdout_deployment": args.holdout_deployment,
        "holdout_results": args.holdout_results,
        "teacher_manifests": args.teacher_manifests,
        "execution_manifest": args.execution_manifest,
        "training_config": args.training_config,
    }
    report: dict[str, Any] = {
        "schema_version": "vectolith-core-prime-preflight-report/1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked",
        "authorization": "not_granted",
        "foundation_model": args.foundation_model,
        "foundation_revision": args.foundation_revision,
        "training_code_revision": args.training_code_revision,
        "input_sha256": {name: _artifact_sha256(path) for name, path in inputs.items()},
        "errors": [],
    }
    try:
        config = _load_config(args.training_config, args.foundation_model)
        rows, result = validate_training_preflight(
            dataset_path=args.dataset,
            foundation_model=args.foundation_model,
            foundation_revision=args.foundation_revision,
            foundation_selection_path=args.foundation_selection,
            teacher_manifest_dir=args.teacher_manifests,
            holdout_deployment_manifest_path=args.holdout_deployment,
            holdout_evaluation_results_dir=args.holdout_results,
            training_execution_manifest_path=args.execution_manifest,
            training_code_revision=args.training_code_revision,
            training_config=config,
        )
        report.update({
            "status": "passed",
            "authorization": "preflight_passed_not_training_authorized",
            "validated_training_rows": len(rows),
            "preflight": result,
        })
        exit_code = 0
    except Exception as exc:
        report["errors"] = [f"{type(exc).__name__}: {exc}"]
        exit_code = 1

    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_name(args.report.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
