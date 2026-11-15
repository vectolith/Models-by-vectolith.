#!/usr/bin/env python3
"""Run JSONL prompt suites against any OpenAI-compatible chat-completions endpoint.

This runner records observations; it does not pretend that model outputs have
been automatically graded. Keep API credentials in environment variables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

SCHEMA_VERSION = "vectolith-evaluation-result/1.0"


@dataclass(frozen=True)
class RunConfig:
    base_url: str
    model: str
    role: str
    candidate_id: str
    revision: str
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 2048
    timeout_seconds: float = 180.0
    api_key: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def endpoint_url(base_url: str) -> str:
    """Normalize a server root or /v1 URL to its chat-completions endpoint."""
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def safe_endpoint(base_url: str) -> str:
    """Return endpoint origin/path without credentials, query, or fragment."""
    parsed = urlsplit(endpoint_url(base_url))
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            try:
                case = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(case, dict):
                raise ValueError(f"{path}:{line_number}: each case must be a JSON object")
            if not isinstance(case.get("id"), str) or not case["id"].strip():
                raise ValueError(f"{path}:{line_number}: case requires a non-empty id")
            if not isinstance(case.get("messages"), list) or not case["messages"]:
                raise ValueError(f"{path}:{line_number}: case requires non-empty messages")
            for message in case["messages"]:
                if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant"}:
                    raise ValueError(f"{path}:{line_number}: invalid chat message")
                if not isinstance(message.get("content"), str):
                    raise ValueError(f"{path}:{line_number}: message content must be text")
            cases.append(case)
    if not cases:
        raise ValueError(f"{path}: no evaluation cases found")
    return cases


def run_case(
    case: dict[str, Any],
    config: RunConfig,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    started_at = utc_now()
    messages_json = json.dumps(case["messages"], ensure_ascii=False, sort_keys=True)
    prompt_hash = hashlib.sha256(messages_json.encode("utf-8")).hexdigest()
    payload = {
        "model": config.model,
        "messages": case["messages"],
        "temperature": config.temperature,
        "top_p": config.top_p,
        "max_tokens": config.max_tokens,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    request = urllib.request.Request(
        endpoint_url(config.base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    try:
        with opener(request, timeout=config.timeout_seconds) as response:
            status_code = getattr(response, "status", 200)
            body = response.read()
        decoded = json.loads(body.decode("utf-8"))
        choices = decoded.get("choices") or []
        if not choices:
            raise ValueError("server response contains no choices")
        choice = choices[0]
        message = choice.get("message") or {}
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "schema_version": SCHEMA_VERSION,
            "recorded_at": utc_now(),
            "started_at": started_at,
            "benchmark_case_id": case["id"],
            "category": case.get("category", "uncategorized"),
            "role": config.role,
            "candidate_id": config.candidate_id,
            "model_requested": config.model,
            "model_revision": config.revision,
            "endpoint": safe_endpoint(config.base_url),
            "prompt_sha256": prompt_hash,
            "http_status": status_code,
            "latency_ms": elapsed_ms,
            "finish_reason": choice.get("finish_reason"),
            "response_text": message.get("content"),
            "tool_calls": message.get("tool_calls"),
            "refusal": message.get("refusal"),
            "usage": decoded.get("usage"),
            "rubric": case.get("rubric"),
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        detail = exc.read(2000).decode("utf-8", errors="replace")
        return _error_record(case, config, started_at, elapsed_ms, f"HTTP {exc.code}: {detail}", exc.code, prompt_hash)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _error_record(case, config, started_at, elapsed_ms, f"{type(exc).__name__}: {exc}", None, prompt_hash)


def _error_record(
    case: dict[str, Any],
    config: RunConfig,
    started_at: str,
    elapsed_ms: float,
    error: str,
    status_code: int | None,
    prompt_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": utc_now(),
        "started_at": started_at,
        "benchmark_case_id": case["id"],
        "category": case.get("category", "uncategorized"),
        "role": config.role,
        "candidate_id": config.candidate_id,
        "model_requested": config.model,
        "model_revision": config.revision,
        "endpoint": safe_endpoint(config.base_url),
        "prompt_sha256": prompt_hash,
        "http_status": status_code,
        "latency_ms": elapsed_ms,
        "finish_reason": None,
        "response_text": None,
        "tool_calls": None,
        "refusal": None,
        "usage": None,
        "rubric": case.get("rubric"),
        "error": error,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, type=Path, help="JSONL evaluation suite")
    parser.add_argument("--output", required=True, type=Path, help="JSONL evidence output")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--role", choices=("core_prime", "core_prima"), required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--revision", required=True, help="Immutable model revision SHA")
    parser.add_argument("--api-key-env", default="VECTOLITH_INFERENCE_API_KEY")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args(argv)

    if len(args.revision) < 7 or args.revision.lower() in {"main", "latest"}:
        parser.error("--revision must identify an immutable checkpoint revision, not main/latest")
    if args.max_tokens < 1 or args.timeout <= 0:
        parser.error("--max-tokens and --timeout must be positive")
    if not 0 <= args.temperature <= 2 or not 0 < args.top_p <= 1:
        parser.error("--temperature must be 0..2 and --top-p must be in (0, 1]")

    try:
        cases = load_cases(args.suite)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    config = RunConfig(
        base_url=args.base_url,
        model=args.model,
        role=args.role,
        candidate_id=args.candidate_id,
        revision=args.revision,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
        api_key=os.environ.get(args.api_key_env),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with args.output.open("w", encoding="utf-8") as output:
        for case in cases:
            record = run_case(case, config)
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            output.flush()
            if record["error"]:
                failures += 1
            print(f"{case['id']}: {'ERROR' if record['error'] else str(record['latency_ms']) + ' ms'}", file=sys.stderr)
    print(f"Recorded {len(cases)} cases; {failures} request failures; output={args.output}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
