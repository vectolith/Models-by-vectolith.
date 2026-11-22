"""Collect a no-download, no-training hardware probe for ASH PRIME.

Run inside a Kaggle notebook after selecting the free GPU accelerator.
This script never downloads model weights, installs packages, or starts training.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _memory_bytes() -> dict[str, int | None]:
    total = available = None
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        values: dict[str, int] = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, _, raw = line.partition(":")
            parts = raw.strip().split()
            if len(parts) >= 2 and parts[1] == "kB":
                values[key] = int(parts[0]) * 1024
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
    if total is None:
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            total = page_size * os.sysconf("SC_PHYS_PAGES")
            available = page_size * os.sysconf("SC_AVPHYS_PAGES")
        except (AttributeError, OSError, ValueError):
            pass
    return {"total_bytes": total, "available_bytes": available}


def _gpu_devices() -> list[dict[str, Any]]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.free,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    devices = []
    for row in csv.reader(result.stdout.splitlines(), skipinitialspace=True):
        if len(row) != 4:
            continue
        try:
            total_mib, free_mib = int(row[1]), int(row[2])
        except ValueError:
            continue
        devices.append({
            "name": row[0].strip(),
            "total_vram_bytes": total_mib * 1024 * 1024,
            "free_vram_bytes": free_mib * 1024 * 1024,
            "driver_version": row[3].strip(),
        })
    return devices


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def collect_resource_probe(storage_path: str | Path | None = None) -> dict[str, Any]:
    target = Path(storage_path or ("/kaggle/working" if Path("/kaggle/working").is_dir() else Path.cwd()))
    target.mkdir(parents=True, exist_ok=True)
    disk = shutil.disk_usage(target)
    memory = _memory_bytes()
    gpus = _gpu_devices()
    kaggle_environment = {
        key: os.environ.get(key)
        for key in ("KAGGLE_KERNEL_RUN_TYPE", "KAGGLE_KERNEL_ID", "KAGGLE_URL_BASE", "KAGGLE_USER_SECRETS_TOKEN")
        if os.environ.get(key) is not None
    }
    # Never serialize credential-bearing environment values.
    kaggle_environment.pop("KAGGLE_USER_SECRETS_TOKEN", None)
    payload: dict[str, Any] = {
        "schema_version": "vectolith-ash-prime-resource-probe/1.0",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "provider": "kaggle" if Path("/kaggle").exists() or "KAGGLE_KERNEL_ID" in os.environ else "unknown",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or None,
            "cpu_count": os.cpu_count(),
            "kaggle": kaggle_environment,
        },
        "memory": memory,
        "storage": {
            "path": str(target.resolve()),
            "total_bytes": disk.total,
            "available_bytes": disk.free,
        },
        "accelerators": {
            "gpu_count": len(gpus),
            "devices": gpus,
            "total_vram_bytes": sum(item["total_vram_bytes"] for item in gpus),
            "aggregate_free_vram_bytes": sum(item["free_vram_bytes"] for item in gpus),
            "largest_single_gpu_free_vram_bytes": max((item["free_vram_bytes"] for item in gpus), default=0),
        },
        "software_versions": {
            "torch": _package_version("torch"),
            "transformers": _package_version("transformers"),
            "datasets": _package_version("datasets"),
            "peft": _package_version("peft"),
            "accelerate": _package_version("accelerate"),
        },
        "account_and_cost": {
            "quota_remaining_hours": None,
            "quota_must_be_verified_in_kaggle_account_settings": True,
            "zero_cost_status": "requires_user_confirmation",
            "billing_or_paid_compute_enabled": None,
        },
        "safety": {
            "model_weights_downloaded": False,
            "inference_started": False,
            "training_started": False,
            "network_requests_made": False,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload["resource_probe_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="ash-prime-resource-probe.json")
    parser.add_argument("--storage-path", default=None)
    args = parser.parse_args()
    report = collect_resource_probe(args.storage_path)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Saved resource probe: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
