#!/usr/bin/env python3
"""Run JSONL prompt suites against any OpenAI-compatible chat-completions endpoint.

This runner records observations; it does not pretend that model outputs have
been automatically graded. Keep API credentials in environment variables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

SCHEMA_VERSION = "vectolith-evaluation-result/1.0"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
IMMUTABLE_REVISION = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", re.IGNORECASE)


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


def runner_source_sha256() -> str:
    """Fingerprint the evaluator implementation for detached evidence reproducibility."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def endpoint_url(base_url: str) -> str:
    """Normalize a server root or /v1 URL to its chat-completions endpoint."""
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def validated_endpoint_url(base_url: str) -> str:
    """Reject unsafe or ambiguous endpoint URL forms before sending credentials."""
    if not isinstance(base_url, str) or not base_url or any(ch.isspace() or ord(ch) < 32 for ch in base_url):
        raise ValueError("base URL must be a non-empty URL without whitespace or control characters")
    parsed = urlsplit(base_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("base URL scheme must be HTTP or HTTPS")
    if not parsed.hostname:
        raise ValueError("base URL must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("base URL must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain a query or fragment")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("base URL contains an invalid port") from exc
    return endpoint_url(base_url)


def safe_endpoint(base_url: str) -> str:
    """Return the normalized endpoint without credentials, query, or fragment."""
    try:
        supplied = urlsplit(base_url)
        if supplied.scheme.lower() not in {"http", "https"} or not supplied.hostname:
            return "[invalid endpoint]"
        host = supplied.hostname
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        port = supplied.port
        if port is not None:
            host = f"{host}:{port}"
        sanitized_base = urlunsplit((supplied.scheme, host, supplied.path, "", ""))
        parsed = urlsplit(endpoint_url(sanitized_base))
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except (TypeError, ValueError):
        return "[invalid endpoint]"


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
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
            if case["id"] in seen_case_ids:
                raise ValueError(f"{path}:{line_number}: duplicate case id: {case['id']}")
            seen_case_ids.add(case["id"])
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


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Fail closed on redirects so evaluation API credentials stay at the chosen endpoint."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects(request: urllib.request.Request, timeout: float):
    opener = urllib.request.build_opener(_NoRedirectHandler)
    return opener.open(request, timeout=timeout)


def _sanitize_error(error: Any, api_key: str | None) -> str:
    text = str(error)
    if api_key:
        text = text.replace(api_key, "[redacted]")
    text = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer [redacted]", text)
    text = re.sub(r"(?i)([?&](?:token|api[_-]?key|key|secret|password)=)[^&#\s]+", r"\1[redacted]", text)
    return text[:2000]


def run_case(
    case: dict[str, Any],
    config: RunConfig,
    opener: Callable[..., Any] | None = None,
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
    started = time.perf_counter()
    try:
        request = urllib.request.Request(
            validated_endpoint_url(config.base_url),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with (opener or _open_without_redirects)(request, timeout=config.timeout_seconds) as response:
            status_code = getattr(response, "status", 200)
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} byte limit")
        decoded = json.loads(body.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("server response must be a JSON object")
        choices = decoded.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ValueError("server response contains no valid choices")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ValueError("first choice contains no valid message")
        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise ValueError("message content must be text or null")
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
            "response_sha256": hashlib.sha256(body).hexdigest(),
            "http_status": status_code,
            "latency_ms": elapsed_ms,
            "finish_reason": choice.get("finish_reason"),
            "response_text": content,
            "tool_calls": message.get("tool_calls"),
            "refusal": message.get("refusal"),
            "usage": decoded.get("usage"),
            "rubric": case.get("rubric"),
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        status_code = exc.code
        exc.close()
        return _error_record(case, config, started_at, elapsed_ms, f"HTTP {status_code}: response body omitted", status_code, prompt_hash)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _error_record(case, config, started_at, elapsed_ms, exc, None, prompt_hash)


def _error_record(
    case: dict[str, Any],
    config: RunConfig,
    started_at: str,
    elapsed_ms: float,
    error: Any,
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
        "response_sha256": None,
        "http_status": status_code,
        "latency_ms": elapsed_ms,
        "finish_reason": None,
        "response_text": None,
        "tool_calls": None,
        "refusal": None,
        "usage": None,
        "rubric": case.get("rubric"),
        "error": _sanitize_error(error, config.api_key),
    }


def write_records(
    cases: list[dict[str, Any]],
    config: RunConfig,
    output_path: Path,
    opener: Callable[..., Any] | None = None,
) -> int:
    """Capture JSONL to a private temporary file, then atomically publish without overwrite."""
    output_path = Path(output_path)
    if os.path.lexists(output_path):
        raise FileExistsError(f"output already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        canonical_suite = json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        canonical_suite_sha256 = hashlib.sha256(canonical_suite).hexdigest()
        runner_sha256 = runner_source_sha256()
        config_snapshot = {
            "endpoint": safe_endpoint(config.base_url),
            "model": config.model,
            "role": config.role,
            "candidate_id": config.candidate_id,
            "revision": config.revision,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "timeout_seconds": config.timeout_seconds,
            "runner_sha256": runner_sha256,
        }
        run_config_sha256 = hashlib.sha256(
            json.dumps(config_snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        run_id = uuid.uuid4().hex
        failures = 0
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            fd = None
            for case in cases:
                record = run_case(case, config, opener=opener)
                record.update({
                    "run_id": run_id,
                    "canonical_suite_sha256": canonical_suite_sha256,
                    "run_config_sha256": run_config_sha256,
                    "runner_sha256": runner_sha256,
                    "suite_case_count": len(cases),
                })
                output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                if record["error"]:
                    failures += 1
                print(
                    f"{case['id']}: {'ERROR' if record['error'] else str(record['latency_ms']) + ' ms'}",
                    file=sys.stderr,
                )
            output.flush()
            os.fsync(output.fileno())
        # A hard link creates the final name atomically and refuses to overwrite
        # an existing file or symlink. The temp file is in the same directory.
        os.link(temporary_path, output_path)
        temporary_path.unlink()
        if os.name == "posix":
            directory_fd = os.open(output_path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        return failures
    finally:
        if fd is not None:
            os.close(fd)
        temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, type=Path, help="JSONL evaluation suite")
    parser.add_argument("--output", required=True, type=Path, help="JSONL evidence output (must not already exist)")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--role", choices=("core_prime", "core_prima"), required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--revision", required=True, help="Immutable 40- or 64-character model revision SHA")
    parser.add_argument("--api-key-env", default="VECTOLITH_INFERENCE_API_KEY")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args(argv)

    if not IMMUTABLE_REVISION.fullmatch(args.revision):
        parser.error("--revision must be a 40- or 64-character hexadecimal immutable SHA")
    if args.max_tokens < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--max-tokens must be positive and --timeout finite and positive")
    if not math.isfinite(args.temperature) or not 0 <= args.temperature <= 2 or not math.isfinite(args.top_p) or not 0 < args.top_p <= 1:
        parser.error("--temperature must be finite and 0..2 and --top-p finite and in (0, 1]")

    try:
        validated_endpoint_url(args.base_url)
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
    try:
        failures = write_records(cases, config, args.output)
    except OSError as exc:
        parser.error(f"evidence output failed: {exc}")
    print(f"Recorded {len(cases)} cases; {failures} request failures; output={args.output}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
