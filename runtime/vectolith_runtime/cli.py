"""Command-line entry point for the Models by vectolith runtime.

Sub-commands:

  selfcheck   Verify the installed package: schemas compile, every evaluation
              fixture parses, the ASH PRIME manifest registers and is
              discoverable. Exit code 1 on any failure.
  preflight   Validate a training dataset and its evidence manifests without
              loading model weights (delegates to training_preflight).
  train       Run evidence-gated SFT (delegates to distillation_training).

Every command reports what it actually observed. Nothing is asserted about
model quality or availability that the command did not itself verify.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema_files() -> list[Path]:
    candidates = [
        REPO_ROOT / "schemas",
        Path(__file__).resolve().parent / "schemas",
    ]
    seen: dict[Path, None] = {}
    for directory in candidates:
        if directory.is_dir():
            for path in sorted(directory.glob("*.schema.json")):
                seen[path.resolve()] = None
    return list(seen)


def _fixture_files() -> list[Path]:
    directory = REPO_ROOT / "evaluation" / "fixtures"
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.jsonl"))


def selfcheck() -> dict[str, Any]:
    """Return a report of what the installed runtime can actually do."""
    from jsonschema import Draft202012Validator

    from .registry import ASH_PRIME_TARGET_CAPABILITIES, ModelManifest, ModelRegistry

    report: dict[str, Any] = {"ok": True, "checks": [], "problems": []}

    def record(name: str, ok: bool, detail: str) -> None:
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            report["ok"] = False
            report["problems"].append(f"{name}: {detail}")

    schemas = _schema_files()
    if not schemas:
        record("schemas.present", False, "no *.schema.json found")
    for path in schemas:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            record(f"schema.{path.name}", True, "valid Draft 2020-12 schema")
        except Exception as exc:  # noqa: BLE001 - report, do not abort the sweep
            record(f"schema.{path.name}", False, f"{type(exc).__name__}: {exc}")

    fixtures = _fixture_files()
    total_records = 0
    if not fixtures:
        record("fixtures.present", False, "no evaluation fixtures found")
    for path in fixtures:
        bad = 0
        count = 0
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                count += 1
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    bad += 1
                    if bad == 1:
                        record(f"fixture.{path.name}", False, f"line {line_number}: {exc.msg}")
                    continue
                if not isinstance(value, dict):
                    bad += 1
                    if bad == 1:
                        record(f"fixture.{path.name}", False, f"line {line_number}: record is not an object")
        total_records += count
        if bad == 0:
            record(f"fixture.{path.name}", True, f"{count} records parsed")
    report["fixture_records"] = total_records

    try:
        registry = ModelRegistry()
        manifest = ModelManifest(
            model_id="ash-prime",
            display_name="ASH PRIME",
            version="0.0.0-unreleased",
            specialization="unified general intelligence",
            capabilities=ASH_PRIME_TARGET_CAPABILITIES,
        )
        registry.register(manifest)
        found = registry.discover(ASH_PRIME_TARGET_CAPABILITIES)
        record(
            "registry.ash-prime",
            len(found) == 1 and found[0].model_id == "ash-prime",
            f"manifest registered, {len(ASH_PRIME_TARGET_CAPABILITIES)} target capabilities discoverable",
        )
        report["ash_prime_capabilities"] = len(ASH_PRIME_TARGET_CAPABILITIES)
    except Exception as exc:  # noqa: BLE001
        record("registry.ash-prime", False, f"{type(exc).__name__}: {exc}")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vectolith-runtime", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("selfcheck", help="verify schemas, fixtures and the ASH PRIME manifest")

    preflight = sub.add_parser("preflight", help="validate training data and evidence manifests")
    preflight.add_argument("--dataset", required=True)
    preflight.add_argument("--foundation-model", required=True)
    preflight.add_argument("--foundation-revision", required=True)
    preflight.add_argument("--foundation-selection", required=True)
    preflight.add_argument("--teacher-manifests", required=True)
    preflight.add_argument("--holdout-deployment", required=True)
    preflight.add_argument("--holdout-results", required=True)
    preflight.add_argument("--execution-manifest", required=True)
    preflight.add_argument("--code-revision", required=True)

    train = sub.add_parser("train", help="run evidence-gated SFT")
    train.add_argument("--dataset", required=True)
    train.add_argument("--foundation-model", required=True)
    train.add_argument("--foundation-revision", required=True)
    train.add_argument("--foundation-selection", required=True)
    train.add_argument("--teacher-manifests", required=True)
    train.add_argument("--holdout-deployment", required=True)
    train.add_argument("--holdout-results", required=True)
    train.add_argument("--execution-manifest", required=True)
    train.add_argument("--code-revision", required=True)
    train.add_argument("--output-dir", required=True)
    train.add_argument("--max-seq-length", type=int, default=4096)
    train.add_argument("--epochs", type=float, default=1.0)
    train.add_argument("--learning-rate", type=float, default=2e-5)
    train.add_argument("--no-lora", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "selfcheck":
        report = selfcheck()
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1

    if args.command == "preflight":
        from .training_preflight import validate_training_preflight

        result = validate_training_preflight(
            dataset_path=args.dataset,
            foundation_model=args.foundation_model,
            foundation_revision=args.foundation_revision,
            foundation_selection_path=args.foundation_selection,
            teacher_manifest_dir=args.teacher_manifests,
            holdout_deployment_manifest_path=args.holdout_deployment,
            holdout_evaluation_results_dir=args.holdout_results,
            training_execution_manifest_path=args.execution_manifest,
            training_code_revision=args.code_revision,
            training_config={
                "max_seq_length": args.max_seq_length,
                "epochs": args.epochs,
                "learning_rate": args.learning_rate,
            },
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "train":
        from .distillation_training import train_student

        result = train_student(
            foundation_model=args.foundation_model,
            foundation_revision=args.foundation_revision,
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            foundation_selection_manifest=args.foundation_selection,
            teacher_qualification_manifest_dir=args.teacher_manifests,
            holdout_deployment_manifest=args.holdout_deployment,
            holdout_evaluation_results_dir=args.holdout_results,
            training_execution_manifest=args.execution_manifest,
            training_code_revision=args.code_revision,
            max_seq_length=args.max_seq_length,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            use_lora=not args.no_lora,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
