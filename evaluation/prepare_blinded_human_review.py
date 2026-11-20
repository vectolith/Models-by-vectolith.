#!/usr/bin/env python3
"""Build identity-separated human review packages from immutable Core Prime evidence."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import secrets
import zipfile
from pathlib import Path
from typing import Any

BLIND_SCHEMA = "vectolith-blind-review/1.0"
RUN40_ARTIFACTS = {
    "prime-teacher-granite-3.1-3b-a800m.zip": {
        "workflow_run_id": "43796213917", "artifact_id": 14199574383, "job_id": 133093491281,
        "sha256": "3f7fc738edef49a7347c50c906a4c3fd2e8a71bde7815de47f65dc03464ebc68",
    },
    "prime-teacher-granite-4.2-3b.zip": {
        "workflow_run_id": "43796213917", "artifact_id": 14213985732, "job_id": 133109238158,
        "sha256": "f5b4a223cdd77c89c32b5c8ccf759f7a7c8d41b8e488395d2b51ebcb1f335834",
    },
    "prime-teacher-minicpm5-2b.zip": {
        "workflow_run_id": "43796213917", "artifact_id": 14223103259, "job_id": 133213797403,
        "sha256": "3e16583a0f6746b8b4f324b7468f8364283d02dd2c5064531de2f5fd1af990ff",
    },
    "prime-teacher-lfm2.5-2.6b.zip": {
        "workflow_run_id": "43796213917", "artifact_id": 14238638626, "job_id": 133281032019,
        "sha256": "a52addbe9aabdde9cbee0543d203cd100e3bf25a84fe4ccda2acd2cc5b9a9d11",
    },
    "prime-teacher-phi-4-mini-instruct.zip": {
        "workflow_run_id": "43796213917", "artifact_id": 14260316025, "job_id": 133404486950,
        "sha256": "ffb3ce18c6c966b4a2914dc3b9393cedc95585f89b41f2ce7067c677131b34d8",
    },
}
RUN42_43_ARTIFACTS = {
    "run42-prime-granite-3.1-3b-a800m.zip": {
        "workflow_run_id": "43820188813", "artifact_id": 14207923899, "job_id": 133141260775,
        "sha256": "8d799a9c015ab6728079fe1f54bf8a6557d0c011d84fd4b826dbbd23e69a81fd",
    },
    "run42-prime-granite-4.2-3b.zip": {
        "workflow_run_id": "43820188813", "artifact_id": 14222803141, "job_id": 133174330091,
        "sha256": "088e3dbee15c26627cc97d6cb09d46bca0a37340cc5a5ae08af86e4ccebcb45e",
    },
    "run42-prime-minicpm5-2b.zip": {
        "workflow_run_id": "43820188813", "artifact_id": 14230880744, "job_id": 133275261975,
        "sha256": "8375eb2eb02192c07c5fdebdf661bda4c9eeb54d852f40679a3863f1210e94d4",
    },
    "run42-prime-lfm2.5-2.6b.zip": {
        "workflow_run_id": "43820188813", "artifact_id": 14262556692, "job_id": 133332287803,
        "sha256": "f6502425a369cd3b86347c311445c729793f45f438e4f4aa4a6f155406216e64",
    },
    "run42-prime-phi-4-mini-instruct.zip": {
        "workflow_run_id": "43820188813", "artifact_id": 14280614317, "job_id": 133549417510,
        "sha256": "9b34e52ef661236741bae16b7de0ce9b04b065fdb223e2aec3bfb4d812cbac4c",
    },
    "run43-prime-granite-3.1-3b-a800m.zip": {
        "workflow_run_id": "43821046671", "artifact_id": 14208733041, "job_id": 133143953242,
        "sha256": "3e3e6d563c1deeb696f7004195de09172e4e2f2f49a2229a9c4d8d82d5218c05",
    },
    "run43-prime-granite-4.2-3b.zip": {
        "workflow_run_id": "43821046671", "artifact_id": 14223262221, "job_id": 133178581513,
        "sha256": "a3781ef0dd5240eca4f223a44f69c39f641bb20d9adf6d2bb7f4efb3b44c2739",
    },
    "run43-prime-minicpm5-2b.zip": {
        "workflow_run_id": "43821046671", "artifact_id": 14231498894, "job_id": 133277594971,
        "sha256": "109c2f235ab8edde59b2beeeedf778f6ae3babf309e70952c62febf09cf93acb",
    },
    "run43-prime-lfm2.5-2.6b.zip": {
        "workflow_run_id": "43821046671", "artifact_id": 14245324681, "job_id": 133347523890,
        "sha256": "7130d8c7f4754e689f4652951a12f09e70df43f7c7e67ecc27dfb1a1fea192ca",
    },
    "run43-prime-phi-4-mini-instruct.zip": {
        "workflow_run_id": "43821046671", "artifact_id": 14261964529, "job_id": 133444059471,
        "sha256": "584ac7979398db27234870b72e3c94c65ff79749828e78ba388db198c68df50f",
    },
}
ARTIFACT_PROVENANCE = {**RUN40_ARTIFACTS, **RUN42_43_ARTIFACTS}
BLIND_GRADE_SCHEMA = "vectolith-blind-human-grade/1.0"
GRADE_SCHEMA = "vectolith-human-grading/1.0"
SCORE_ANCHORS = {
    0: "Incorrect, unsafe, fabricated, or materially non-responsive",
    1: "Major errors; most of the criterion is unmet",
    2: "Partially correct; material omissions or defects remain",
    3: "Meets the criterion; only minor defects",
    4: "Fully meets the criterion with no material defect",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl_bytes(data: bytes, label: str) -> list[dict[str, Any]]:
    rows = []
    for line_no, raw in enumerate(data.decode("utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{label}:{line_no}: expected a JSON object")
        rows.append(item)
    return rows


def load_suites(paths: list[Path]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for path in paths:
        rows = read_jsonl_bytes(path.read_bytes(), str(path))
        for case in rows:
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id:
                raise ValueError(f"{path}: case has no non-empty id")
            if case_id in cases:
                raise ValueError(f"duplicate suite case id: {case_id}")
            if not isinstance(case.get("messages"), list) or not case["messages"]:
                raise ValueError(f"{case_id}: missing original messages")
            rubric = case.get("rubric")
            if (not isinstance(rubric, list) or not rubric
                    or any(not isinstance(x, str) or not x.strip() for x in rubric)
                    or len(rubric) != len(set(rubric))):
                raise ValueError(f"{case_id}: invalid original rubric")
            cases[case_id] = case
    if not cases:
        raise ValueError("no suite cases loaded")
    return cases


def load_evidence_archive(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    archive_bytes = path.read_bytes()
    hashes = {"archive_sha256": sha256_bytes(archive_bytes)}
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            json_names = [n for n in names if n.startswith("evaluations/") and n.endswith(".json")]
            if len(json_names) != 1:
                raise ValueError(f"{path}: expected exactly one evaluations/*.json file")
            json_name = json_names[0]
            record_bytes = archive.read(json_name)
            record = json.loads(record_bytes)
            jsonl_name = json_name[:-5] + ".jsonl"
            if jsonl_name not in names:
                raise ValueError(f"{path}: missing paired raw JSONL {jsonl_name}")
            jsonl_bytes = archive.read(jsonl_name)
            rows = read_jsonl_bytes(jsonl_bytes, f"{path}:{jsonl_name}")
    except zipfile.BadZipFile as exc:
        raise ValueError(f"{path}: expected a GitHub Actions artifact ZIP") from exc
    if not isinstance(record, dict) or not isinstance(record.get("results"), list):
        raise ValueError(f"{path}: JSON artifact has no results array")
    if rows != record["results"]:
        raise ValueError(f"{path}: JSON results and JSONL evidence differ")
    hashes["results_json_sha256"] = sha256_bytes(record_bytes)
    hashes["results_jsonl_sha256"] = sha256_bytes(jsonl_bytes)
    return record, rows, hashes


def _identity(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("candidate_id", "")),
        str(row.get("model_revision", "")),
        str(row.get("run_id", "")),
        str(row.get("started_at", "")),
    )


def build_review_packages(
    evidence_paths: list[Path],
    suite_paths: list[Path],
    output_dir: Path,
    reviewer_count: int = 2,
    expected_artifacts: int = 5,
    expected_cases: int = 180,
    workflow_run_id: str = "43796213917",
) -> dict[str, Any]:
    if reviewer_count < 2:
        raise ValueError("at least two independent reviewer packages are required")
    if len(evidence_paths) != expected_artifacts:
        raise ValueError(f"expected {expected_artifacts} evidence artifacts, received {len(evidence_paths)}")
    if workflow_run_id == "43796213917" and {path.name for path in evidence_paths} != set(RUN40_ARTIFACTS):
        raise ValueError("run 40 requires the exact five published source artifact files")
    if len({path.name for path in evidence_paths}) != len(evidence_paths):
        raise ValueError("source artifact filenames must be unique")
    suites = load_suites(suite_paths)
    artifacts: list[dict[str, Any]] = []
    seen_execution_ids = set()
    source_register = []
    for path in evidence_paths:
        record, rows, hashes = load_evidence_archive(path)
        pinned = ARTIFACT_PROVENANCE.get(path.name)
        if pinned and hashes["archive_sha256"] != pinned["sha256"]:
            raise ValueError(f"{path}: archive SHA-256 does not match the published artifact digest")
        candidate = record.get("candidate_id")
        revision = record.get("immutable_revision")
        run_id = record.get("run_id")
        if not all(isinstance(x, str) and x for x in (candidate, revision, run_id)):
            raise ValueError(f"{path}: missing candidate, immutable revision, or run id")
        execution_id = (candidate, revision, run_id)
        if execution_id in seen_execution_ids:
            raise ValueError(f"duplicate candidate execution artifact: {execution_id}")
        seen_execution_ids.add(execution_id)
        if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision.lower()):
            raise ValueError(f"{path}: model revision is not an immutable 40-character SHA")
        if record.get("role") not in (None, "core_prime") or any(r.get("role") != "core_prime" for r in rows):
            raise ValueError(f"{path}: evidence is not Core Prime")
        if len(rows) != expected_cases:
            raise ValueError(f"{path}: expected {expected_cases} responses, received {len(rows)}")
        seen_cases = set()
        for row in rows:
            case_id = row.get("benchmark_case_id") or row.get("case_id")
            if case_id not in suites:
                raise ValueError(f"{path}: response references case absent from supplied original suites: {case_id}")
            if case_id in seen_cases:
                raise ValueError(f"{path}: duplicate response for case {case_id}")
            seen_cases.add(case_id)
            case = suites[case_id]
            if row.get("rubric") != case.get("rubric"):
                raise ValueError(f"{path}:{case_id}: response rubric differs from original suite rubric")
            if row.get("category") != case.get("category"):
                raise ValueError(f"{path}:{case_id}: response category differs from original suite")
            if row.get("candidate_id") != candidate or row.get("model_revision") != revision or row.get("run_id") != run_id:
                raise ValueError(f"{path}:{case_id}: per-response provenance disagrees with artifact metadata")
            if row.get("role") != "core_prime":
                raise ValueError(f"{path}:{case_id}: expected role core_prime")
        if seen_cases != set(suites):
            missing = sorted(set(suites) - seen_cases)
            raise ValueError(f"{path}: suite coverage mismatch; missing {missing[:5]}")
        source_run_id = pinned["workflow_run_id"] if pinned and pinned.get("workflow_run_id") else workflow_run_id
        item = {"record": record, "rows": rows, "hashes": hashes, "path": path, "workflow_run_id": source_run_id, "provenance": pinned}
        artifacts.append(item)
        source_register.append({
            "candidate_id": candidate,
            "model_revision": revision,
            "run_id": run_id,
            "artifact_file": path.name,
            "workflow_run_id": source_run_id,
            "artifact_id": pinned["artifact_id"] if pinned else None,
            "workflow_job_id": pinned["job_id"] if pinned else None,
            **hashes,
        })

    candidate_names = sorted({item["record"]["candidate_id"] for item in artifacts})
    case_sets = [
        {r.get("benchmark_case_id") or r.get("case_id") for r in item["rows"]}
        for item in artifacts
    ]
    if any(case_set != case_sets[0] for case_set in case_sets[1:]):
        raise ValueError("candidate response sets do not cover identical case IDs")

    salt = secrets.token_hex(32)
    private_records: dict[str, Any] = {}
    review_rows = []
    for item in artifacts:
        record = item["record"]
        candidate = record["candidate_id"]
        source_run_id = item["workflow_run_id"]
        provenance = item["provenance"]
        for row in item["rows"]:
            case_id = row.get("benchmark_case_id") or row.get("case_id")
            started_at = row.get("started_at", "")
            identity = "\0".join((candidate, record["immutable_revision"], record["run_id"], case_id, started_at))
            blind_id = "blind-" + hashlib.sha256((salt + "\0" + identity).encode()).hexdigest()[:24]
            response = row.get("response_text")
            error = row.get("error")
            gradeable = not error and isinstance(response, str) and bool(response.strip())
            private_records[blind_id] = {
                "candidate_id": candidate,
                "model_revision": record["immutable_revision"],
                "run_id": record["run_id"],
                "evidence_started_at": started_at,
                "benchmark_case_id": case_id,
                "role": "core_prime",
                "category": row["category"],
                "rubric": list(suites[case_id]["rubric"]),
                "gradeable": gradeable,
                "source_artifact": item["path"].name,
                "source_artifact_sha256": item["hashes"]["archive_sha256"],
                "workflow_run_id": source_run_id,
                "artifact_id": provenance.get("artifact_id") if provenance else None,
                "workflow_job_id": provenance.get("job_id") if provenance else None,
                "prompt_sha256": row.get("prompt_sha256"),
                "generation_status": row.get("generation_status"),
                "generation_cap_reached": bool(row.get("generation_cap_reached")),
                "generated_tokens": row.get("generated_tokens"),
                "max_new_tokens": row.get("max_new_tokens"),
                "error": error,
            }
            review_rows.append({
                "blind_id": blind_id,
                "case_id": case_id,
                "category": row["category"],
                "messages": suites[case_id]["messages"],
                "rubric": list(suites[case_id]["rubric"]),
                "response_text": response,
                "response_metadata": {
                    "generation_status": row.get("generation_status"),
                    "token_cap_reached": bool(row.get("generation_cap_reached")),
                    "generated_tokens": row.get("generated_tokens"),
                    "max_new_tokens": row.get("max_new_tokens"),
                    "error_present": bool(error),
                    "error_class": str(error).split(":", 1)[0] if error else None,
                    "gradeable": gradeable,
                },
            })

    output_dir.mkdir(parents=True, exist_ok=True)
    private_dir = output_dir / "private"
    private_dir.mkdir(exist_ok=True)
    private_key = {
        "schema_version": "vectolith-blind-review-identity-key/1.0",
        "warning": "RESTRICTED: never distribute this file to reviewers. It reverses candidate blinding.",
        "created_with_random_salt": salt,
        "sources": source_register,
        "records": private_records,
    }
    (private_dir / "identity-key.json").write_text(
        json.dumps(private_key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    aliases = [f"Candidate {letter}" for letter in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
    package_register = []
    for reviewer_index in range(1, reviewer_count + 1):
        reviewer_id = f"reviewer-{reviewer_index:02d}"
        rng = random.SystemRandom()
        shuffled_aliases = rng.sample(aliases, len(candidate_names))
        alias_by_candidate = dict(zip(candidate_names, shuffled_aliases))
        shuffled = list(review_rows)
        rng.shuffle(shuffled)
        items = []
        grades = []
        for row in shuffled:
            private = private_records[row["blind_id"]]
            candidate = private["candidate_id"]
            items.append({
                "schema_version": BLIND_SCHEMA,
                "blinded_response_id": row["blind_id"],
                "candidate_alias": alias_by_candidate[candidate],
                "benchmark_case_id": row["case_id"],
                "category": row["category"],
                "messages": row["messages"],
                "rubric": row["rubric"],
                "response_text": row["response_text"],
                "response_metadata": row["response_metadata"],
                "review_disposition": "gradeable" if private["gradeable"] else "not_gradeable_error",
            })
            if private["gradeable"]:
                grades.append({
                    "schema_version": BLIND_GRADE_SCHEMA,
                    "blinded_response_id": row["blind_id"],
                    "benchmark_case_id": row["case_id"],
                    "evaluator_id": "",
                    "evaluator_version": "core-prime-rubric-v1",
                    "rubric_scores": [
                        {"criterion": criterion, "score": None, "notes": ""}
                        for criterion in row["rubric"]
                    ],
                    "unblinding_observed": False,
                    "unblinding_notes": "",
                })
        package_manifest = {
            "schema_version": BLIND_SCHEMA,
            "package_id": reviewer_id,
            "item_count": len(items),
            "gradeable_count": len(grades),
            "not_gradeable_error_count": len(items) - len(grades),
            "review_items_sha256": sha256_bytes(
                ("\n".join(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in items) + "\n").encode()
            ),
            "grade_template_sha256": sha256_bytes(
                ("\n".join(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in grades) + "\n").encode()
            ),
            "identity_key_included": False,
        }
        readme = (
            "# Core Prime blinded response review\n\n"
            "Do not attempt to identify model providers. Candidate aliases are randomized independently in each reviewer package. "
            "Review every gradeable response against the supplied original prompt and rubric. Do not discuss scores with other reviewers before submission. "
            "If a response appears to identify its provider, set unblinding_observed=true and explain without guessing a score from provider identity.\n\n"
            "Score every rubric criterion from 0 to 4 using the same anchors:\n\n"
            + "\n".join(f"- **{score}** — {anchor}" for score, anchor in SCORE_ANCHORS.items())
            + "\n\n"
            "Preserve this package and the completed grade-template.jsonl unchanged. Record evaluator_id as a stable, unique human reviewer identifier. "
            "Do not grade entries marked not_gradeable_error. No package or score constitutes teacher qualification.\n"
        )
        zip_path = output_dir / f"{reviewer_id}-blind-review.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("README.md", readme)
            archive.writestr("review-items.jsonl", "\n".join(
                json.dumps(x, ensure_ascii=False, sort_keys=True) for x in items
            ) + "\n")
            archive.writestr("grade-template.jsonl", "\n".join(
                json.dumps(x, ensure_ascii=False, sort_keys=True) for x in grades
            ) + ("\n" if grades else ""))
            archive.writestr("manifest.json", json.dumps(package_manifest, indent=2) + "\n")
        package_register.append({
            "reviewer_package": zip_path.name,
            "item_count": len(items),
            "gradeable_count": len(grades),
            "sha256": sha256_bytes(zip_path.read_bytes()),
        })

    summary = {
        "schema_version": "vectolith-blind-review-build/1.0",
        "workflow_run_id": workflow_run_id,
        "candidate_artifact_count": len(artifacts),
        "unique_candidate_count": len(candidate_names),
        "suite_case_count": len(suites),
        "response_count": len(review_rows),
        "gradeable_response_count": sum(1 for x in private_records.values() if x["gradeable"]),
        "error_response_count": sum(1 for x in private_records.values() if not x["gradeable"]),
        "reviewer_package_count": reviewer_count,
        "reviewer_packages": package_register,
        "private_identity_key": "private/identity-key.json",
        "qualification_decision": "not_made",
    }
    (output_dir / "build-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def unblind_grade_files(
    private_key_path: Path,
    grade_paths: list[Path],
) -> list[dict[str, Any]]:
    key = json.loads(private_key_path.read_text(encoding="utf-8"))
    if key.get("schema_version") != "vectolith-blind-review-identity-key/1.0":
        raise ValueError("unsupported or invalid private identity key")
    identity = key.get("records")
    if not isinstance(identity, dict) or not identity:
        raise ValueError("private identity key has no response mapping")
    expected = {blind_id for blind_id, row in identity.items() if row.get("gradeable")}
    if len(grade_paths) < 2:
        raise ValueError("at least two independent reviewer grade files are required")
    canonical = []
    evaluator_ids = set()
    for grade_path in grade_paths:
        grades = read_jsonl_bytes(grade_path.read_bytes(), str(grade_path))
        if not grades:
            raise ValueError(f"{grade_path}: no grades supplied")
        file_evaluators = {g.get("evaluator_id") for g in grades}
        if len(file_evaluators) != 1 or not all(isinstance(x, str) and x.strip() for x in file_evaluators):
            raise ValueError(f"{grade_path}: one stable non-empty evaluator_id is required per reviewer file")
        evaluator_id = next(iter(file_evaluators))
        if evaluator_id in evaluator_ids:
            raise ValueError("reviewer files must have distinct evaluator_id values")
        evaluator_ids.add(evaluator_id)
        seen = set()
        for number, grade in enumerate(grades, 1):
            if grade.get("schema_version") != BLIND_GRADE_SCHEMA:
                raise ValueError(f"{grade_path}:{number}: unsupported blinded grade schema")
            blind_id = grade.get("blinded_response_id")
            if blind_id not in expected:
                raise ValueError(f"{grade_path}:{number}: unknown or non-gradeable blinded response")
            if blind_id in seen:
                raise ValueError(f"{grade_path}:{number}: duplicate blinded response grade")
            seen.add(blind_id)
            source = identity[blind_id]
            if grade.get("benchmark_case_id") != source["benchmark_case_id"]:
                raise ValueError(f"{grade_path}:{number}: case ID does not match blinded evidence")
            if grade.get("unblinding_observed") not in (True, False):
                raise ValueError(f"{grade_path}:{number}: unblinding_observed must be boolean")
            if not isinstance(grade.get("unblinding_notes", ""), str):
                raise ValueError(f"{grade_path}:{number}: unblinding_notes must be text")
            version = grade.get("evaluator_version")
            if not isinstance(version, str) or not version.strip():
                raise ValueError(f"{grade_path}:{number}: evaluator_version is required")
            scores = grade.get("rubric_scores")
            expected_criteria = source.get("rubric")
            if not isinstance(scores, list) or not isinstance(expected_criteria, list):
                raise ValueError(f"{grade_path}:{number}: rubric scores or private rubric mapping missing")
            score_map = {}
            for item in scores:
                if not isinstance(item, dict):
                    raise ValueError(f"{grade_path}:{number}: rubric score must be an object")
                criterion = item.get("criterion")
                score = item.get("score")
                notes = item.get("notes", "")
                if criterion not in expected_criteria or criterion in score_map:
                    raise ValueError(f"{grade_path}:{number}: unknown or duplicate rubric criterion")
                if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 4:
                    raise ValueError(f"{grade_path}:{number}: every criterion score must be numeric 0..4")
                if not isinstance(notes, str):
                    raise ValueError(f"{grade_path}:{number}: notes must be text")
                score_map[criterion] = {"criterion": criterion, "score": score, "notes": notes}
            if set(score_map) != set(expected_criteria):
                raise ValueError(f"{grade_path}:{number}: every original rubric criterion must be scored")
            canonical.append({
                "schema_version": GRADE_SCHEMA,
                "benchmark_case_id": source["benchmark_case_id"],
                "evidence_started_at": source["evidence_started_at"],
                "candidate_id": source["candidate_id"],
                "model_revision": source["model_revision"],
                "role": source["role"],
                "category": source["category"],
                "run_id": source["run_id"],
                "evaluator_id": evaluator_id,
                "evaluator_version": version,
                "rubric_scores": [score_map[c] for c in expected_criteria],
                "unblinding_observed": grade["unblinding_observed"],
                "unblinding_notes": grade.get("unblinding_notes", ""),
            })
        if seen != expected:
            missing = len(expected - seen)
            extra = len(seen - expected)
            raise ValueError(f"{grade_path}: incomplete review; missing {missing}, unexpected {extra}")
    return canonical


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build separate blinded reviewer ZIPs and a restricted identity key")
    build.add_argument("--evidence", action="append", type=Path, required=True)
    build.add_argument("--suite", action="append", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--reviewers", type=int, default=2)
    build.add_argument("--expected-artifacts", type=int, default=5)
    build.add_argument("--expected-cases", type=int, default=180)
    build.add_argument("--workflow-run-id", default="43796213917")
    unblind = sub.add_parser("unblind", help="validate complete independent grades and restore evidence identity")
    unblind.add_argument("--identity-key", type=Path, required=True)
    unblind.add_argument("--grades", action="append", type=Path, required=True)
    unblind.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        result = build_review_packages(
            args.evidence, args.suite, args.output_dir, args.reviewers,
            args.expected_artifacts, args.expected_cases, args.workflow_run_id,
        )
        print(json.dumps(result, indent=2))
        return 0
    grades = unblind_grade_files(args.identity_key, args.grades)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in grades) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "grade_records": len(grades),
        "distinct_reviewers": len({row["evaluator_id"] for row in grades}),
        "qualification_decision": "not_made",
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
