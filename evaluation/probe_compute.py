#!/usr/bin/env python3
"""Capture observed compute hardware from the current notebook/runner session.

This probe reports the machine visible to the process. It cannot prove that a
provider's quota will remain available or that a user's account is eligible.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def command_output(command: list[str]) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def detect_environment() -> list[str]:
    markers = {
        "github_actions": os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
        "kaggle": bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE") or os.environ.get("KAGGLE_URL_BASE")),
        "colab": bool(os.environ.get("COLAB_RELEASE_TAG") or os.path.exists("/content")),
        "modal": bool(os.environ.get("MODAL_TASK_ID")),
        "lightning": bool(os.environ.get("LIGHTNING_CLOUD_PROJECT_ID") or os.environ.get("LIGHTNING_STUDIO_NAME")),
    }
    return [name for name, present in markers.items() if present]


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("compute-observation.json"))
    args = parser.parse_args(argv)
    try:
        import psutil
        memory = {"total_bytes": psutil.virtual_memory().total, "available_bytes": psutil.virtual_memory().available}
    except ImportError:
        memory = None
    record: dict[str, Any] = {
        "schema_version": "vectolith-compute-observation/1.0",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "process_session": "active_session_observed",
        "environment_markers": detect_environment(),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "system_memory": memory,
        "nvidia_smi": command_output(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader"]),
        "provider_quota": "not_observable_from_generic_process",
        "account_eligibility": "not_verified",
        "billing_state": "not_verified",
        "free_capacity_status": "not_verified",
    }
    try:
        import torch
        record["pytorch"] = {
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count(),
            "devices": [
                {"name": torch.cuda.get_device_name(index), "total_memory_bytes": torch.cuda.get_device_properties(index).total_memory}
                for index in range(torch.cuda.device_count())
            ],
        }
    except ImportError:
        record["pytorch"] = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
