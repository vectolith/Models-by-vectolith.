#!/usr/bin/env python3
"""Verify Run 42 ZIP artifacts and prepare candidate-balanced semantic grading batches.

Offline only: no model API calls, credentials, or training execution.
"""
from __future__ import annotations
import argparse, hashlib, json, secrets, sys, zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.grading.semantic_grader import PROMPT_VERSION, assemble_grade_record, build_grading_request
from evaluation.grading.pilot_aggregate_comparison import compare_pilot_aggregates
from evaluation.grading.verify_coverage import sha256_file, validate_grade_record, verify_coverage, verify_grade_bindings, write_jsonl

GRADER_LOCK = json.loads((ROOT / "evaluation/grading/local-grader-lock.json").read_text(encoding="utf-8"))
LOCKED_GRADER_ID = f"local/{GRADER_LOCK['model_id']}"
LOCKED_GRADER_VERSION = GRADER_LOCK["immutable_revision"]
if GRADER_LOCK.get("prompt_version") != PROMPT_VERSION:
    raise RuntimeError("local grader lock and semantic prompt version do not match")

RUN42 = {
 "granite-3.1-3b-a800m": ("a02780686e08a03fe0d2679a293b5c74a90efa89", "8d799a9c015ab6728079fe1f54bf8a6557d0c011d84fd4b826dbbd23e69a81fd"),
 "granite-4.2-3b": ("4e9c275e232f10211ec88644d106a1f6a1b60e06", "088e3dbee15c26627cc97d6cb09d46bca0a37340cc5a5ae08af86e4ccebcb45e"),
 "minicpm5-2b": ("42433e90dad95123ab87729fd7011e7110629556", "8375eb2eb02192c07c5fdebdf661bda4c9eeb54d852f40679a3863f1210e94d4"),
 "lfm2.5-2.6b": ("7141b56cd4650af95c7c7b86983443aed050c96a", "f6502425a369cd3b86347c311445c729793f45f438e4f4aa4a6f155406216e64"),
 "phi-4-mini-instruct": ("cfbefacb99257ffa30c83adab238a50856ac3083", "9b34e52ef661236741bae16b7de0ce9b04b065fdb223e2aec3bfb4d812cbac4c"),
}
PILOT_CASES = {"prime-reasoning-001", "prime-reasoning-002", "prime-math-001",
               "prime-knowledge-001", "prime-instruction-001", "prime-synthesis-001"}

def records_from_json(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if not isinstance(value, dict):
        return []
    if isinstance(value.get("results"), list):
        return [x for x in value["results"] if isinstance(x, dict)]
    if isinstance(value.get("response_text"), str):
        return [value]
    return []

def extract_artifact(path: Path, candidate_id: str) -> list[dict[str, Any]]:
    revision, expected_sha = RUN42[candidate_id]
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise ValueError(f"{candidate_id}: ZIP SHA-256 mismatch: {actual_sha}")
    rows = []
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if "evaluations" in Path(n).parts and n.endswith(".json") and not n.endswith("/") ]
        if not names:
            names = [n for n in archive.namelist() if n.endswith(".jsonl") and not n.endswith("/")]
        for name in names:
            raw = archive.read(name).decode("utf-8")
            values = ([json.loads(line) for line in raw.splitlines() if line.strip()]
                      if name.endswith(".jsonl") else records_from_json(json.loads(raw)))
            for row in values:
                if not isinstance(row.get("response_text"), str) or not row["response_text"].strip():
                    continue
                row_candidate = row.get("candidate_id")
                row_revision = row.get("model_revision") or row.get("immutable_revision")
                case_id = row.get("case_id") or row.get("benchmark_case_id")
                if row_candidate != candidate_id or row_revision != revision:
                    raise ValueError(f"{candidate_id}: candidate/revision mismatch in {name}")
                if not isinstance(case_id, str) or not case_id or not isinstance(row.get("rubric"), list) or not row["rubric"]:
                    raise ValueError(f"{candidate_id}: missing case ID or embedded rubric in {name}")
                response = row["response_text"]
                rows.append({"candidate_id": candidate_id, "candidate_revision": revision,
                    "case_id": case_id, "inference_run_id": str(row.get("run_id") or "43820188813"),
                    "rubric": row["rubric"], "response_text": response,
                    "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
                    "source_artifact_sha256": actual_sha})
    case_ids = [row["case_id"] for row in rows]
    if len(rows) != 180 or len(set(case_ids)) != 180:
        raise ValueError(f"{candidate_id}: expected 180 unique responses, found {len(rows)}")
    return rows

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try: result.append(json.loads(line))
            except json.JSONDecodeError as exc: raise ValueError(f"{path}:{number}: {exc}") from exc
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", action="append", required=True, metavar="CANDIDATE=ZIP")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=("pilot", "remaining", "all"), default="pilot",
                        help="Run the 30-response pilot first, then the remaining 870 after explicit pilot review")
    parser.add_argument("--pilot-report", type=Path, help="Completed pilot report required for --phase remaining")
    parser.add_argument("--confirm-pilot-review", action="store_true",
                        help="Acknowledge review of the completed pilot comparison before preparing remaining cases")
    parser.add_argument("--pilot-review-note", help="Required operator note recording the pilot comparison review and disposition")
    parser.add_argument("--grades", type=Path, help="Optional JSONL of completed strict grade records")
    parser.add_argument("--decisions", type=Path, help="Optional semantic grader decisions JSONL; converted into evidence-bound grade records")
    parser.add_argument("--grader-id", default=LOCKED_GRADER_ID, help="Locked local grader identifier; hosted APIs are not supported")
    parser.add_argument("--grader-version", default=LOCKED_GRADER_VERSION, help="Exact immutable local grader revision")
    parser.add_argument("--graded-at", help="ISO-8601 timestamp for imported grading decisions")
    parser.add_argument("--batch-size", type=int, default=30)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    if args.grader_id != LOCKED_GRADER_ID or args.grader_version != LOCKED_GRADER_VERSION:
        parser.error(
            f"only the pinned local grader {LOCKED_GRADER_ID}@{LOCKED_GRADER_VERSION} is permitted; "
            "remote grader backends are unsupported"
        )
    resolved_out = args.out_dir.resolve()
    try:
        resolved_out.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        parser.error("--out-dir must be outside the repository checkout to prevent raw-response and identity-map commits")
    if args.grades and args.decisions:
        parser.error("use only one of --grades or --decisions")
    if args.decisions and not (args.grader_id and args.grader_version and args.graded_at):
        parser.error("--decisions requires --grader-id, --grader-version and --graded-at")
    if args.phase == "remaining" and not (args.pilot_report and args.confirm_pilot_review and args.pilot_review_note and args.pilot_review_note.strip() and args.grader_id and args.grader_version):
        parser.error("--phase remaining requires --pilot-report, --confirm-pilot-review, a non-empty --pilot-review-note, --grader-id and --grader-version")

    artifact_paths = {}
    for item in args.artifact:
        if "=" not in item:
            parser.error("--artifact must be CANDIDATE=ZIP")
        candidate, filename = item.split("=", 1)
        if candidate not in RUN42 or candidate in artifact_paths:
            parser.error(f"unknown or duplicate candidate: {candidate}")
        artifact_paths[candidate] = Path(filename)
    if set(artifact_paths) != set(RUN42):
        parser.error("provide exactly one artifact for each of the five Run 42 candidates")

    population = []
    for candidate in RUN42:
        population.extend(extract_artifact(artifact_paths[candidate], candidate))
    if len(population) != 900:
        raise ValueError(f"expected 900 Run 42 responses, found {len(population)}")

    expected_artifacts = {key: RUN42[key][1] for key in RUN42}
    pilot_keys = {(candidate, case) for candidate in RUN42 for case in PILOT_CASES}
    pilot_report = None
    if args.phase == "remaining":
        pilot_report = json.loads(args.pilot_report.read_text(encoding="utf-8"))
        if (pilot_report.get("phase") != "pilot" or pilot_report.get("status") != "pilot_compared"
                or pilot_report.get("artifact_sha256") != expected_artifacts
                or not pilot_report.get("grade_coverage", {}).get("coverage_complete")
                or not pilot_report.get("grade_evidence_bindings", {}).get("criterion_decisions_complete")
                or not pilot_report.get("pilot_comparison")
                or not pilot_report.get("grade_records_path")):
            raise ValueError("pilot report is incomplete, unverified or bound to different Run 42 artifacts")
        pilot_ledger_path = Path(pilot_report["grade_records_path"])
        if not pilot_ledger_path.is_file() or sha256_file(pilot_ledger_path) != pilot_report.get("grade_records_sha256"):
            raise ValueError("pilot grade ledger is missing or its digest does not match the pilot report")
        pilot_grades = read_jsonl(pilot_ledger_path)
        for grade in pilot_grades:
            validate_grade_record(grade)
        pilot_population = [row for row in population if (row["candidate_id"], row["case_id"]) in pilot_keys]
        pilot_coverage = verify_coverage(
            [{"candidate_id": row["candidate_id"], "case_id": row["case_id"]} for row in pilot_population],
            pilot_grades)
        pilot_bindings = verify_grade_bindings(pilot_population, pilot_grades)
        if not pilot_coverage["coverage_complete"] or not pilot_bindings["criterion_decisions_complete"]:
            raise ValueError("pilot grade ledger no longer passes coverage and evidence-binding verification")
        reference = json.loads((Path(__file__).resolve().parent / "pilot_reference.json").read_text(encoding="utf-8"))
        if compare_pilot_aggregates(pilot_grades, reference) != pilot_report.get("pilot_comparison"):
            raise ValueError("pilot aggregate comparison does not match the immutable pilot grade ledger")
        prior_grader = pilot_report.get("grader") or {}
        if prior_grader.get("grader_id") != args.grader_id or prior_grader.get("grader_version") != args.grader_version:
            raise ValueError("remaining phase must use the same pinned grader ID and revision as the completed pilot")
        if prior_grader.get("prompt_version") != PROMPT_VERSION:
            raise ValueError("remaining phase grading prompt version differs from the completed pilot")

    if args.phase == "pilot":
        eligible = [row for row in population if (row["candidate_id"], row["case_id"]) in pilot_keys]
    elif args.phase == "remaining":
        eligible = [row for row in population if (row["candidate_id"], row["case_id"]) not in pilot_keys]
    else:
        eligible = population
    expected_count = {"pilot": 30, "remaining": 870, "all": 900}[args.phase]
    if len(eligible) != expected_count:
        raise ValueError(f"{args.phase} phase expected {expected_count} responses, found {len(eligible)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    phase_dir = args.out_dir / args.phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    index_sha = write_jsonl(args.out_dir / "run42-response-index.jsonl", population)

    # Keep one private randomized identity map across pilot and remaining phases.
    identity_path = args.out_dir / "candidate-identity-map.private.json"
    if identity_path.exists():
        identity_map = json.loads(identity_path.read_text(encoding="utf-8"))
        expected_blind_ids = {f"blind-{i:02d}" for i in range(1, 6)}
        if (not isinstance(identity_map, dict) or len(identity_map) != 5
                or set(identity_map) != expected_blind_ids or set(identity_map.values()) != set(RUN42)):
            raise ValueError("existing private identity map does not match the five Run 42 candidates")
        alias = {candidate: blind for blind, candidate in identity_map.items()}
    else:
        blinded_order = list(RUN42)
        secrets.SystemRandom().shuffle(blinded_order)
        alias = {candidate: f"blind-{i + 1:02d}" for i, candidate in enumerate(blinded_order)}
        identity_path.write_text(json.dumps({value: key for key, value in alias.items()}, indent=2) + "\n", encoding="utf-8")
        try:
            identity_path.chmod(0o600)
        except OSError:
            pass

    # Interleave candidates so every 30-record batch is candidate-balanced.
    by_candidate = {candidate: sorted((x for x in eligible if x["candidate_id"] == candidate),
                                      key=lambda x: x["case_id"]) for candidate in RUN42}
    ordered = []
    for index in range(max((len(v) for v in by_candidate.values()), default=0)):
        for candidate in RUN42:
            if index < len(by_candidate[candidate]):
                ordered.append(by_candidate[candidate][index])
    requests = [build_grading_request(candidate_alias=alias[row["candidate_id"]], case_id=row["case_id"],
                response=row["response_text"], rubric=row["rubric"], response_sha256=row["response_sha256"])
                for row in ordered]

    batch_dir = phase_dir / "requests"
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_count, batch_manifests = 0, []
    for offset in range(0, len(requests), args.batch_size):
        batch_count += 1
        batch_rows = requests[offset:offset + args.batch_size]
        batch_path = batch_dir / f"batch-{batch_count:03d}.jsonl"
        request_sha = write_jsonl(batch_path, batch_rows)
        manifest_path = batch_dir / f"batch-{batch_count:03d}.report.json"
        manifest = {"schema_version": "vectolith-core-prime-grading-batch/1.0",
                    "phase": args.phase, "batch_id": f"batch-{batch_count:03d}",
                    "request_count": len(batch_rows),
                    "candidate_alias_counts": {name: sum(1 for row in batch_rows if row["candidate_alias"] == name)
                                               for name in sorted(set(alias.values()))},
                    "request_file": batch_path.name, "request_sha256": request_sha,
                    "status": "prepared_not_graded"}
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        batch_manifests.append((manifest_path, batch_rows, manifest))

    report = {"schema_version": "vectolith-core-prime-grading-population/1.0",
        "inference_run_id": "43820188813", "phase": args.phase,
        "population_count": len(population), "expected_grading_count": len(eligible),
        "phase_excluded_count": len(population) - len(eligible),
        "grading_request_count": len(requests), "batch_size": args.batch_size,
        "batch_count": batch_count, "response_index_sha256": index_sha,
        "artifact_sha256": expected_artifacts,
        "candidate_aliases": sorted(set(alias.values())),
        "batch_reports": [x[0].name for x in batch_manifests],
        "status": "requests_prepared_not_graded"}
    if args.phase == "remaining":
        report["pilot_report_sha256"] = sha256_file(args.pilot_report)
        report["pilot_grade_records_sha256"] = pilot_report["grade_records_sha256"]
        report["pilot_comparison"] = pilot_report["pilot_comparison"]
        report["pilot_review"] = {"confirmed": True, "note": args.pilot_review_note.strip()}
    grade_path = args.grades
    if args.decisions:
        decisions = read_jsonl(args.decisions)
        alias_to_candidate = {value: key for key, value in alias.items()}
        population_lookup = {(row["candidate_id"], row["case_id"]): row for row in eligible}
        grades, seen_decisions = [], set()
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ValueError("semantic decision must be an object")
            blind_id, case_id = decision.get("candidate_alias"), decision.get("case_id")
            if blind_id not in alias_to_candidate or not isinstance(case_id, str):
                raise ValueError("semantic decision has unknown alias or missing case ID")
            candidate = alias_to_candidate[blind_id]
            key = (candidate, case_id)
            if key in seen_decisions:
                raise ValueError(f"duplicate semantic decision: {key}")
            seen_decisions.add(key)
            source = population_lookup.get(key)
            if source is None:
                raise ValueError(f"semantic decision is outside the {args.phase} grading population: {key}")
            if decision.get("response_sha256") != source["response_sha256"]:
                raise ValueError(f"{key}: semantic decision response digest mismatch")
            grades.append(assemble_grade_record(
                inference_run_id=source["inference_run_id"], candidate_id=candidate,
                candidate_revision=source["candidate_revision"], source_artifact_sha256=source["source_artifact_sha256"],
                case_id=case_id, response=source["response_text"], rubric=source["rubric"],
                semantic_decision={"criteria": decision.get("criteria")}, rubric_version="run42-embedded-rubric-v1",
                grader={"method": "model_assisted", "grader_id": args.grader_id,
                        "grader_version": args.grader_version, "prompt_version": PROMPT_VERSION},
                graded_at=args.graded_at))
        grade_path = phase_dir / "grade-records.jsonl"
        write_jsonl(grade_path, grades)
    elif args.grades:
        grades = read_jsonl(args.grades)
        for grade in grades:
            validate_grade_record(grade)

    if grade_path:
        grades = grades if args.decisions else read_jsonl(grade_path)
        for grade in grades:
            validate_grade_record(grade)
        expected = [{"candidate_id": x["candidate_id"], "case_id": x["case_id"]} for x in eligible]
        coverage = verify_coverage(expected, grades)
        bindings = verify_grade_bindings(eligible, grades)
        report["grade_coverage"] = coverage
        report["grade_evidence_bindings"] = bindings
        report["grade_records_sha256"] = sha256_file(grade_path)
        report["grade_records_path"] = str(Path(grade_path).resolve())
        if grades:
            graders = {(row["grader"]["grader_id"], row["grader"]["grader_version"], row["grader"]["prompt_version"])
                       for row in grades}
            if len(graders) != 1:
                raise ValueError("one grading phase must use a single pinned grader and prompt version")
            grader_id, grader_version, prompt_version = next(iter(graders))
            report["grader"] = {"grader_id": grader_id, "grader_version": grader_version,
                                "prompt_version": prompt_version}
            if args.phase == "remaining" and (grader_id != args.grader_id or grader_version != args.grader_version):
                raise ValueError("grade records do not use the pilot-approved grader identity and revision")
        report["status"] = "grading_incomplete"
        if coverage["coverage_complete"] and bindings["criterion_decisions_complete"]:
            if args.phase == "pilot":
                reference = json.loads((Path(__file__).resolve().parent / "pilot_reference.json").read_text(encoding="utf-8"))
                report["pilot_comparison"] = compare_pilot_aggregates(grades, reference)
                report["pilot_review_required"] = True
                report["status"] = "pilot_compared"
            else:
                report["status"] = "grading_complete"

        alias_to_candidate = {value: key for key, value in alias.items()}
        grade_lookup = {(row["candidate_id"], row["case_id"]): row for row in grades}
        for manifest_path, batch_rows, manifest in batch_manifests:
            batch_grades = []
            for request in batch_rows:
                candidate = alias_to_candidate[request["candidate_alias"]]
                grade = grade_lookup.get((candidate, request["case_id"]))
                if grade is not None:
                    batch_grades.append(grade)
            unresolved = sum(row["score"]["unscored"] for row in batch_grades)
            manifest.update({"graded_response_count": len(batch_grades),
                "ungraded_response_count": len(batch_rows) - len(batch_grades),
                "unscored_criterion_count": unresolved,
                "status": "graded_complete" if len(batch_grades) == len(batch_rows) and unresolved == 0 else "grading_incomplete"})
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if args.phase == "pilot" and report.get("grader") is None:
        report["grader"] = {"grader_id": args.grader_id, "grader_version": args.grader_version,
                            "prompt_version": PROMPT_VERSION}
    if args.phase == "remaining" and report.get("grader") is None:
        report["grader"] = {"grader_id": args.grader_id, "grader_version": args.grader_version,
                            "prompt_version": PROMPT_VERSION}
    pilot_graded = (pilot_report.get("grade_coverage", {}).get("graded_response_count", 0)
                    if args.phase == "remaining" else
                    report.get("grade_coverage", {}).get("graded_response_count", 0) if args.phase == "pilot" else 0)
    current_graded = report.get("grade_coverage", {}).get("graded_response_count", 0)
    overall_graded = pilot_graded + current_graded if args.phase == "remaining" else current_graded
    if args.phase == "all":
        overall_graded = current_graded
    report["overall_coverage"] = {"expected_response_count": 900,
        "graded_response_count": overall_graded,
        "ungraded_response_count": 900 - overall_graded,
        "complete": overall_graded == 900 and report["status"] in {"grading_complete", "pilot_compared"}}
    report_path = phase_dir / "run42-grading-population-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    final_summary = {"schema_version": "vectolith-core-prime-grading-summary/1.0",
        "inference_run_id": "43820188813", "phase": args.phase,
        "phase_expected_responses": len(eligible),
        "phase_graded_responses": current_graded,
        "phase_ungraded_responses": report.get("grade_coverage", {}).get("ungraded_response_count", len(eligible)),
        "expected_responses": 900,
        "graded_responses": overall_graded,
        "ungraded_responses": 900 - overall_graded,
        "unscored_criteria": report.get("grade_evidence_bindings", {}).get("unscored_criteria"),
        "pilot_comparison": report.get("pilot_comparison"),
        "batch_count": batch_count, "batch_size": args.batch_size,
        "grade_records_sha256": report.get("grade_records_sha256"),
        "status": report["status"]}
    (phase_dir / "run42-final-summary.json").write_text(json.dumps(final_summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in {"requests_prepared_not_graded", "pilot_compared", "grading_complete"} else 2

if __name__ == "__main__":
    raise SystemExit(main())
