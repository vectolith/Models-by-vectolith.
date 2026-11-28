
"""ASH PRIME and FYR PRIMA: multi-teacher corpus generation and student fine-tuning.

Runs on a free Kaggle 2xT4 session. Every teacher and student checkpoint is an
Apache-2.0 open-weight model downloaded from the Hugging Face Hub; nothing paid is
used. The run is reproducible: tasks come from the repository curriculum, teacher
sampling is seeded, and every accepted record carries teacher identity, revision,
content hash and deterministic check results.

Two corpus sources, in priority order:

  * a pre-graded Run 42 corpus mounted under /kaggle/input/ash-prime-run42-corpus
    (built by training/build_run42_corpus.py from the graded responses). Only
    responses whose every rubric criterion passed are used, so the panel is the
    five verified Run 42 candidates instead of live teacher generation.
  * otherwise the in-kernel teacher panel below generates the corpus.

Stages:
  1. fetch the repository and the curriculum
  2. ask each teacher in the panel to answer its assigned tasks
  3. apply deterministic acceptance checks
  4. build one dataset per student from its own panel
  5. fine-tune ASH PRIME and FYR PRIMA separately
  6. evaluate each adapter on the persona suite and write evidence
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
import traceback
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

WORK = Path(os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working"))
REPO = WORK / "repo"
OUT = WORK / "out"
CORPUS = OUT / "corpus"


def prepare_paths() -> None:
    """Create the output tree. Deferred out of import time so the module stays
    importable (and testable) on machines that have no /kaggle/working."""
    for path in (OUT, CORPUS):
        path.mkdir(parents=True, exist_ok=True)


REPO_URL = "https://github.com/vectolith/Models-by-vectolith..git"

# Pre-graded Run 42 corpus. When this directory exists the kernel trains from
# graded responses instead of generating a fresh corpus on the GPU.
GRADED_CORPUS_DIR = Path(os.environ.get("ASH_PRIME_CORPUS_DIR", "/kaggle/input/ash-prime-run42-corpus"))
GRADED_CORPUS_FILE = "run42-graded-corpus.jsonl"
GRADED_CORPUS_MANIFEST = "run42-graded-corpus.manifest.json"

# License evidence for each Run 42 candidate, from evidence/teacher-rights-register.json.
GRADED_TEACHER_LICENSES = {
    "granite-3.1-3b-a800m": "apache-2.0",
    "granite-4.2-3b": "apache-2.0",
    "minicpm5-2b": "apache-2.0",
    "lfm2.5-2.6b": "lfm-open-license",
    "phi-4-mini-instruct": "mit",
}

GRADED_REQUIRED_FIELDS = (
    "case_id",
    "teacher",
    "teacher_revision",
    "source_artifact_sha256",
    "system",
    "prompt",
    "response",
    "response_sha256",
    "accepted",
)

TEACHERS = {
    "granite-4.2-8b": {
        "model_id": "ibm-granite/granite-4.2-8b",
        "license": "apache-2.0",
        "four_bit": True,
        "competencies": ["reasoning", "mathematics", "engineering", "writing"],
    },
    "qwen2.5-coder-7b": {
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "license": "apache-2.0",
        "four_bit": True,
        "competencies": ["coding", "engineering", "mathematics"],
    },
    "qwen3-4b-instruct": {
        "model_id": "Qwen/Qwen3-4B-Instruct-2507",
        "license": "apache-2.0",
        "four_bit": False,
        "competencies": ["conversation", "personality_more", "personality_consistency", "writing"],
    },
}

STUDENTS = {
    "ash-prime": {
        "model_id": "Qwen/Qwen3-4B-Instruct-2507",
        "panel": ["granite-4.2-8b", "qwen2.5-coder-7b", "qwen3-4b-instruct"],
        "epochs": 2,
        "learning_rate": 1.5e-4,
        "seed": 11,
    },
    "fyr-prima": {
        "model_id": "Qwen/Qwen3-1.7B",
        "panel": ["granite-4.2-8b", "qwen3-4b-instruct"],
        "epochs": 2,
        "learning_rate": 2e-4,
        "seed": 29,
    },
}

# Panels used when training from the pre-graded Run 42 corpus: the teacher keys
# are Run 42 candidate IDs, not the in-kernel generation panel above.
GRADED_STUDENTS = {
    "ash-prime": {
        "model_id": "Qwen/Qwen3-4B-Instruct-2507",
        "panel": ["granite-3.1-3b-a800m", "granite-4.2-3b", "minicpm5-2b", "lfm2.5-2.6b", "phi-4-mini-instruct"],
        "epochs": 2,
        "learning_rate": 1.5e-4,
        "seed": 11,
    },
    "fyr-prima": {
        "model_id": "Qwen/Qwen3-1.7B",
        "panel": ["granite-4.2-3b", "minicpm5-2b", "phi-4-mini-instruct"],
        "epochs": 2,
        "learning_rate": 2e-4,
        "seed": 29,
    },
}

MAX_NEW_TOKENS = 320
BATCH = 4

REQUIRED_TASK_FIELDS = ("id", "competency", "system", "prompt")
REQUIRED_CORPUS_FIELDS = (
    "task_id",
    "competency",
    "prompt",
    "system",
    "teacher",
    "teacher_model",
    "teacher_revision",
    "teacher_license",
    "response",
    "response_sha256",
    "checks",
)

# Filled during corpus generation: teacher name -> immutable Hub revision.
REVISIONS: dict = {}

# Durable persistence. A free Colab or Kaggle VM is recycled without notice, and
# everything under /content or /kaggle/working dies with it. Every artifact is
# mirrored the moment it is written, so a recycled VM costs a rerun of one stage
# and never the adapters themselves.
RUN_ID = os.environ.get("ASH_PRIME_RUN_ID") or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
MIRROR_DIR_ENV = "ASH_PRIME_MIRROR_DIR"
OFFSITE_DIR = WORK / "offsite"
_DURABLE: list = []  # one-element cache: [Path | None]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_stats(path: Path) -> tuple:
    if path.is_file():
        return 1, path.stat().st_size
    files = [item for item in path.rglob("*") if item.is_file()]
    return len(files), sum(item.stat().st_size for item in files)


def _mount_drive() -> Path | None:
    """Mount Google Drive and return MyDrive, or None when unavailable."""
    drive = Path("/content/drive")
    try:
        if not (drive / "MyDrive").is_dir():
            from google.colab import drive as colab_drive  # type: ignore

            log("mounting Google Drive for durable artifact storage")
            colab_drive.mount(str(drive), force_remount=False, timeout_ms=180000)
    except Exception as exc:  # noqa: BLE001 - no Drive is a supported mode
        log(f"drive mount unavailable: {type(exc).__name__}: {exc}")
        return None
    return drive / "MyDrive" if (drive / "MyDrive").is_dir() else None


def durable_root() -> Path | None:
    """Persistent mirror root, or None when this host has no durable storage."""
    if _DURABLE:
        return _DURABLE[0]
    root = None
    override = os.environ.get(MIRROR_DIR_ENV)
    if override:
        root = Path(override)
    if root is None:
        my_drive = _mount_drive()
        if my_drive is not None:
            root = my_drive / "ash-prime-runs"
    if root is None and Path("/kaggle/working").is_dir():
        root = Path("/kaggle/working") / "persisted"
    if root is not None:
        try:
            (root / RUN_ID).mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            log(f"mirror root unusable: {type(exc).__name__}: {exc}")
            root = None
    _DURABLE.append(root)
    log(f"durable mirror: {root if root is not None else 'NONE'}")
    return root


def _offsite_copy(path: Path) -> None:
    """Upload an artifact to an anonymous host as a last-resort durable copy."""
    archive = OFFSITE_DIR / f"{path.stem}-{RUN_ID}.tar.gz"
    try:
        OFFSITE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.make_archive(str(archive)[: -len(".tar.gz")], "gztar", root_dir=str(path.parent), base_dir=path.name)
        completed = subprocess.run(
            ["curl", "-s", "-m", "600", "-F", f"file=@{archive}", "https://tmpfiles.org/api/v1/upload"],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(completed.stdout or "{}")
        url = (payload.get("data") or {}).get("url")
        if url:
            log(f"OFFSITE {path.name}: {url}")
            (OFFSITE_DIR / "urls.txt").open("a", encoding="utf-8").write(f"{path.name} {url}\n")
        else:
            log(f"offsite upload of {path.name} failed: {completed.stdout[:200]}")
    except Exception:  # noqa: BLE001 - offsite copy is best effort
        traceback.print_exc()


def persist(label: str, *paths: Path) -> dict:
    """Copy artifacts to durable storage now, then verify the copy."""
    root = durable_root()
    record = {"run_id": RUN_ID, "label": label, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "artifacts": {}}
    for path in paths:
        files, size = _tree_stats(path)
        record["artifacts"][path.name] = {
            "files": files,
            "bytes": size,
            "sha256": _sha256_file(path) if path.is_file() else None,
        }
        if root is None:
            _offsite_copy(path)
            continue
        target = root / RUN_ID / path.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if path.is_file():
            shutil.copy2(path, target)
        else:
            shutil.copytree(path, target)
        got_files, got_bytes = _tree_stats(target)
        if got_files != files or got_bytes != size:
            raise RuntimeError(f"mirror of {path.name} incomplete: {got_files}/{files} files, {got_bytes}/{size} bytes")
        if path.is_file() and _sha256_file(target) != record["artifacts"][path.name]["sha256"]:
            raise RuntimeError(f"mirror of {path.name} failed its checksum")
        log(f"persisted {label} -> {target}")
    record["mirror"] = str(root) if root is not None else None
    line = json.dumps(record) + "\n"
    targets = [WORK / "persist-log.jsonl"]
    if root is not None:
        targets.append(root / RUN_ID / "persist-log.jsonl")
    for log_path in targets:
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except Exception:  # noqa: BLE001 - logging must never kill a run
            pass
    return record


class PersistCallback(TrainerCallback):
    """Mirror the LoRA adapter to durable storage during training, not only at the end."""

    def __init__(self, name: str, adapter_dir: Path, every: int = 25):
        self.name = name
        self.adapter_dir = adapter_dir
        self.every = max(1, every)
        self.last_step = 0

    def on_step_end(self, args, state, control, model=None, **kwargs):  # noqa: ANN001, ARG002
        if model is None or state.global_step - self.last_step < self.every:
            return control
        self.last_step = state.global_step
        try:
            snapshot = self.adapter_dir.parent / f"{self.adapter_dir.name}-step{state.global_step}"
            snapshot.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(str(snapshot))
            persist(snapshot.name, snapshot)
            for stale in sorted(self.adapter_dir.parent.glob(f"{self.adapter_dir.name}-step*"))[:-2]:
                shutil.rmtree(stale, ignore_errors=True)
        except Exception:  # noqa: BLE001 - checkpoint mirroring is best effort
            traceback.print_exc()
        return control


def package_run() -> Path:
    """Zip the whole output tree so it can be downloaded or mirrored as one file."""
    archive = WORK / "ash-prime-out.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for item in sorted(OUT.rglob("*")):
            if item.is_file() and item != archive:
                bundle.write(item, item.relative_to(WORK))
    log(f"packaged {archive} ({archive.stat().st_size} bytes)")
    return archive


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def ensure_bitsandbytes(min_version: str = "0.46.1") -> str:
    """Guarantee a bitsandbytes new enough for transformers 4-bit loading.

    The Kaggle image ships a build older than the 0.46.1 floor transformers
    enforces, so upgrade it and reload in place instead of trusting the
    notebook's pip cell (which runs against a different site-packages).
    """
    def _version(mod) -> tuple:
        parts = []
        for piece in mod.__version__.split(".")[:3]:
            digits = re.sub(r"\D", "", piece)
            parts.append(int(digits) if digits else 0)
        return tuple(parts)

    want = tuple(int(p) for p in min_version.split("."))
    try:
        import bitsandbytes as _bnb

        if _version(_bnb) >= want:
            log(f"bitsandbytes {_bnb.__version__} ok")
            return _bnb.__version__
    except Exception:
        pass

    log(f"upgrading bitsandbytes to >={min_version}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "--no-cache-dir",
            "--upgrade",
            f"bitsandbytes>={min_version}",
        ],
        check=False,
    )
    import importlib
    import site

    for extra in list(site.getsitepackages()) + [site.getusersitepackages()]:
        if extra and extra not in sys.path and os.path.isdir(extra):
            sys.path.insert(0, extra)
    importlib.invalidate_caches()
    import bitsandbytes as bnb

    importlib.reload(bnb)
    if _version(bnb) < want:
        raise RuntimeError(
            f"bitsandbytes {bnb.__version__} still below {min_version} after upgrade"
        )
    log(f"bitsandbytes {bnb.__version__} installed")
    return bnb.__version__


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seed_for(name: str) -> int:
    """Process-independent sampling seed for one teacher.

    Python randomises str hashing per interpreter (PYTHONHASHSEED), so
    hash(name) would give a different seed on every run and break the
    reproducibility the run summary claims. Derive the seed from the
    content hash instead.
    """
    return int(sha(name)[:8], 16) % 10000


def validate_task(task: dict, competencies: set) -> None:
    missing = [field for field in REQUIRED_TASK_FIELDS if field not in task]
    if missing:
        raise ValueError(f"curriculum task {task.get('id')!r} missing fields {missing}")
    if task["competency"] not in competencies:
        raise ValueError(
            f"curriculum task {task['id']!r} uses competency {task['competency']!r} "
            "that no teacher in TEACHERS is assigned"
        )


def validate_corpus_row(row: dict) -> None:
    missing = [field for field in REQUIRED_CORPUS_FIELDS if field not in row]
    if missing:
        raise ValueError(f"teacher record {row.get('task_id')!r} missing fields {missing}")
    if row["response_sha256"] != sha(row["response"]):
        raise ValueError(f"teacher record {row['task_id']!r} has a mismatched response hash")


def fetch_repo() -> None:
    if REPO.exists():
        subprocess.run(["git", "-C", str(REPO), "pull", "--ff-only"], check=False)
        return
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(REPO)], check=True)


def load_tasks() -> list:
    path = REPO / "training" / "curriculum" / "tasks-v1.jsonl"
    tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    competencies = {competency for spec in TEACHERS.values() for competency in spec["competencies"]}
    for task in tasks:
        validate_task(task, competencies)
    covered = {task["competency"] for task in tasks}
    log(f"curriculum tasks: {len(tasks)} across {len(covered)} competencies")
    return tasks


def load_graded_corpus() -> list:
    """Load the pre-graded Run 42 corpus, or return [] when it is not mounted.

    Every row must carry its provenance and an all-criteria-passed verdict;
    rows that were rejected during grading are never trained on.
    """
    path = GRADED_CORPUS_DIR / GRADED_CORPUS_FILE
    if not path.is_file():
        log(f"no graded corpus at {path}; falling back to in-kernel generation")
        return []
    manifest_path = GRADED_CORPUS_DIR / GRADED_CORPUS_MANIFEST
    if not manifest_path.is_file():
        raise RuntimeError(f"graded corpus at {path} has no manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("corpus_sha256") != sha(path.read_text(encoding="utf-8")):
        raise RuntimeError("graded corpus content does not match its manifest digest")

    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        missing = [field for field in GRADED_REQUIRED_FIELDS if field not in row]
        if missing:
            raise ValueError(f"graded corpus row {row.get('case_id')!r} missing fields {missing}")
        if row["response_sha256"] != sha(row["response"]):
            raise ValueError(f"graded corpus row {row['case_id']!r} has a mismatched response hash")
        if row.get("rejection_reason"):
            continue
        if not row.get("accepted"):
            continue
        if row.get("teacher") not in GRADED_TEACHER_LICENSES:
            raise ValueError(f"graded corpus row {row['case_id']!r} has unknown teacher {row['teacher']!r}")
        rows.append(row)
    log(f"graded corpus: {len(rows)} accepted responses from {len({r['teacher'] for r in rows})} teachers")
    return rows


def build_graded_dataset(rows: list, panel: list, seed: int) -> list:
    """Turn accepted graded responses into chat SFT rows for one student."""
    dataset = []
    for row in rows:
        if row["teacher"] not in panel:
            continue
        dataset.append(
            {
                "messages": [
                    {"role": "system", "content": row["system"]},
                    {"role": "user", "content": row["prompt"]},
                    {"role": "assistant", "content": row["response"]},
                ],
                "teacher": row["teacher"],
                "teacher_model": row["teacher"],
                "teacher_revision": row["teacher_revision"],
                "teacher_license": GRADED_TEACHER_LICENSES[row["teacher"]],
                "task_id": row["case_id"],
                "response_sha256": row["response_sha256"],
                "grade_total": (row.get("grade") or {}).get("total"),
            }
        )
    dataset.sort(key=lambda item: sha(item["task_id"] + item["teacher"] + str(seed)))
    return dataset


def load_teacher(name: str, spec: dict):
    quant = None
    if spec["four_bit"]:
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    tokenizer = AutoTokenizer.from_pretrained(spec["model_id"], padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        spec["model_id"],
        quantization_config=quant,
        torch_dtype=torch.float16 if quant is None else None,
        device_map="auto",
    )
    model.eval()
    revision = getattr(getattr(model, "config", None), "_commit_hash", None)
    if revision:
        REVISIONS[name] = revision
        log(f"loaded teacher {name} at revision {revision}")
    else:
        log(f"loaded teacher {name} (no immutable revision available from the checkpoint config)")
    return tokenizer, model


def render(tokenizer, system: str, user: str) -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


@torch.inference_mode()
def answer_tasks(tokenizer, model, tasks: list, seed: int) -> list:
    torch.manual_seed(seed)
    records = []
    for start in range(0, len(tasks), BATCH):
        chunk = tasks[start : start + BATCH]
        prompts = [render(tokenizer, task["system"], task["prompt"]) for task in chunk]
        encoded = tokenizer(
            prompts, return_tensors="pt", padding=True, truncation=True, max_length=1536
        )
        encoded.pop("token_type_ids", None)
        input_len = encoded["input_ids"].shape[1]
        encoded = encoded.to(model.device)
        generated = model.generate(
            **encoded,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=0.7,
            top_p=0.92,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.pad_token_id,
        )
        for index, task in enumerate(chunk):
            new_tokens = generated[index][input_len:]
            text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            records.append({"task": task, "text": text})
        log(f"  answered {min(start + BATCH, len(tasks))}/{len(tasks)}")
    return records


def deterministic_checks(task: dict, text: str) -> dict:
    reasons = []
    if len(text) < 60:
        reasons.append("too_short")
    if len(text) > 6000:
        reasons.append("too_long")
    lowered = text.lower()
    for marker in ("as an ai language model", "i cannot assist with that request."):
        if marker in lowered:
            reasons.append("boilerplate_refusal")
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if task["competency"] == "coding" and blocks:
        for block in blocks:
            if "def " not in block:
                continue
            try:
                compile(block, "<teacher>", "exec")
            except SyntaxError:
                reasons.append("python_syntax_error")
                break
    return {"accepted": not reasons, "reasons": reasons}


def generate_corpus(tasks: list) -> dict:
    corpus = {}
    for name, spec in TEACHERS.items():
        subset = [task for task in tasks if task["competency"] in spec["competencies"]]
        if not subset:
            log(f"teacher {name} has no assigned competencies; skipping")
            continue
        cached = CORPUS / f"teacher-{name}.jsonl"
        if cached.exists() and cached.stat().st_size > 0:
            cached_rows = []
            cache_ok = True
            for line in cached.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    validate_corpus_row(row)
                except Exception:
                    cache_ok = False
                    break
                cached_rows.append(row)
            if cache_ok and cached_rows:
                corpus[name] = cached_rows
                log(f"teacher {name}: reused {len(cached_rows)} cached records from {cached}")
                continue
            log(f"teacher {name}: cached corpus at {cached} unusable; regenerating")

        tokenizer, model = load_teacher(name, spec)
        revision = REVISIONS.get(name)
        started = time.time()
        answers = answer_tasks(tokenizer, model, subset, seed=seed_for(name))
        elapsed = round(time.time() - started, 1)
        accepted = []
        for record in answers:
            checks = deterministic_checks(record["task"], record["text"])
            row = {
                "task_id": record["task"]["id"],
                "competency": record["task"]["competency"],
                "prompt": record["task"]["prompt"],
                "system": record["task"]["system"],
                "teacher": name,
                "teacher_model": spec["model_id"],
                "teacher_revision": revision,
                "teacher_license": spec["license"],
                "response": record["text"],
                "response_sha256": sha(record["text"]),
                "checks": checks,
            }
            validate_corpus_row(row)
            accepted.append(row)
        corpus[name] = accepted
        path = CORPUS / f"teacher-{name}.jsonl"
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in accepted), encoding="utf-8")
        log(f"teacher {name}: {len(accepted)} records, {sum(r['checks']['accepted'] for r in accepted)} accepted, {elapsed}s")
        del model
        torch.cuda.empty_cache()
    return corpus


def build_dataset(corpus: dict, panel: list, seed: int) -> list:
    rows = []
    for teacher in panel:
        for record in corpus.get(teacher, []):
            if not record["checks"]["accepted"]:
                continue
            rows.append(
                {
                    "messages": [
                        {"role": "system", "content": record["system"]},
                        {"role": "user", "content": record["prompt"]},
                        {"role": "assistant", "content": record["response"]},
                    ],
                    "teacher": record["teacher"],
                    "teacher_model": record["teacher_model"],
                    "teacher_revision": record["teacher_revision"],
                    "teacher_license": record["teacher_license"],
                    "task_id": record["task_id"],
                    "response_sha256": record["response_sha256"],
                }
            )
    rows.sort(key=lambda row: sha(row["task_id"] + row["teacher"] + str(seed)))
    return rows


class ChatCollator:
    def __init__(self, tokenizer, max_length: int = 1536):
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __call__(self, features):
        texts = [
            self.tokenizer.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=False)
            for row in features
        ]
        prompts = [
            self.tokenizer.apply_chat_template(row["messages"][:-1], tokenize=False, add_generation_prompt=True)
            for row in features
        ]
        batch = self.tokenizer(
            texts, return_tensors="pt", padding=True, truncation=True, max_length=self.max_length
        )
        labels = batch["input_ids"].clone()
        for index, prompt in enumerate(prompts):
            prompt_len = len(self.tokenizer(prompt, truncation=True, max_length=self.max_length)["input_ids"])
            labels[index, :prompt_len] = -100
        labels[batch["input_ids"] == self.tokenizer.pad_token_id] = -100
        batch["labels"] = labels
        return batch


def train_student(name: str, spec: dict, rows: list) -> dict:
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    dataset_path = OUT / f"{name}-sft.jsonl"
    dataset_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")

    tokenizer = AutoTokenizer.from_pretrained(spec["model_id"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(spec["model_id"], quantization_config=quant, device_map="auto")
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    adapter_dir = OUT / f"{name}-adapter"
    steps_per_epoch = max(1, math.ceil(len(rows) / (2 * 4)))
    total_steps = max(1, steps_per_epoch * math.ceil(spec["epochs"]))
    warmup_steps = max(1, int(0.03 * total_steps))
    arguments = TrainingArguments(
        output_dir=str(WORK / f"train-{name}"),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=spec["epochs"],
        learning_rate=spec["learning_rate"],
        lr_scheduler_type="cosine",
        warmup_steps=warmup_steps,
        logging_steps=5,
        save_strategy="no",
        report_to=[],
        seed=spec["seed"],
        fp16=True,
        optim="paged_adamw_8bit",
        remove_unused_columns=False,
    )
    persist_callback = PersistCallback(name, adapter_dir, every=max(5, total_steps // 4))
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=Dataset.from_list(rows),
        data_collator=ChatCollator(tokenizer),
        callbacks=[persist_callback],
    )
    started = time.time()
    result = trainer.train()
    elapsed = round(time.time() - started, 1)
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    persist(f"{name}-adapter", adapter_dir)

    manifest = {
        "student": name,
        "foundation": spec["model_id"],
        "foundation_license": "apache-2.0",
        "panel": spec["panel"],
        "records": len(rows),
        "epochs": spec["epochs"],
        "learning_rate": spec["learning_rate"],
        "seed": spec["seed"],
        "train_seconds": elapsed,
        "train_loss": result.training_loss,
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05},
        "dataset_sha256": sha(dataset_path.read_text(encoding="utf-8")),
    }
    manifest_path = OUT / f"{name}-training-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    persist(f"{name}-manifest", manifest_path, OUT / f"{name}-sft.jsonl")
    log(f"trained {name}: loss {result.training_loss:.4f} in {elapsed}s")

    del model, trainer
    torch.cuda.empty_cache()
    return manifest


def evaluate_student(name: str, spec: dict) -> dict:
    from peft import PeftModel

    cases_path = REPO / "training" / "evaluation" / "persona-cases-v1.jsonl"
    if not cases_path.exists():
        return {"student": name, "status": "no_cases"}
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    tokenizer = AutoTokenizer.from_pretrained(spec["model_id"], padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(spec["model_id"], torch_dtype=torch.float16, device_map="auto")
    model = PeftModel.from_pretrained(base, str(OUT / f"{name}-adapter"))
    model.eval()

    outputs = []
    for case in cases:
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": case["system"]}, {"role": "user", "content": case["prompt"]}],
            tokenize=False,
            add_generation_prompt=True,
        )
        encoded = tokenizer(prompt, return_tensors="pt")
        encoded.pop("token_type_ids", None)
        encoded = encoded.to(model.device)
        with torch.inference_mode():
            generated = model.generate(
                **encoded, max_new_tokens=200, do_sample=False, pad_token_id=tokenizer.pad_token_id
            )
        text = tokenizer.decode(generated[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True).strip()
        outputs.append({"case_id": case["id"], "prompt": case["prompt"], "response": text, "sha256": sha(text)})

    report = {
        "student": name,
        "foundation": spec["model_id"],
        "cases": len(cases),
        "outputs": outputs,
        "human_review_status": "pending",
        "note": "Deterministic checks only. Promotion requires blinded human grading per release policy.",
    }
    report_path = OUT / f"{name}-evaluation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    persist(f"{name}-evaluation", report_path)
    del model, base
    torch.cuda.empty_cache()
    return {"student": name, "cases": len(cases)}


def main() -> None:
    started = time.time()
    ensure_bitsandbytes()
    prepare_paths()
    fetch_repo()
    graded_rows = load_graded_corpus()
    tasks: list = []
    corpus: dict = {}
    if graded_rows:
        students = GRADED_STUDENTS
        corpus_source = "graded_run42"
    else:
        students = STUDENTS
        corpus_source = "in_kernel_generation"
        tasks = load_tasks()
        corpus = generate_corpus(tasks)

    manifests = {}
    for name, spec in students.items():
        if graded_rows:
            rows = build_graded_dataset(graded_rows, spec["panel"], spec["seed"])
        else:
            rows = build_dataset(corpus, spec["panel"], spec["seed"])
        log(f"{name}: {len(rows)} training records from panel {spec['panel']}")
        if len(rows) < 10:
            log(f"{name}: only {len(rows)} accepted records, skipping this student")
            manifests[name] = {"student": name, "status": "insufficient_records", "records": len(rows)}
            continue
        try:
            manifests[name] = train_student(name, spec, rows)
        except Exception as error:  # one student failing must not kill the other
            traceback.print_exc()
            log(f"{name}: training failed with {type(error).__name__}: {error}")
            manifests[name] = {"student": name, "status": "failed", "error": f"{type(error).__name__}: {error}"}
            torch.cuda.empty_cache()

    evaluations = {}
    for name, spec in students.items():
        try:
            evaluations[name] = evaluate_student(name, spec)
        except Exception:
            traceback.print_exc()
            evaluations[name] = {"student": name, "status": "failed"}

    summary = {
        "run": {
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
            "seconds": round(time.time() - started, 1),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            "gpu_count": torch.cuda.device_count(),
            "torch": torch.__version__,
        },
        "teachers": {
            name: {
                "model_id": spec["model_id"],
                "revision": REVISIONS.get(name),
                "license": spec["license"],
            }
            for name, spec in TEACHERS.items()
        },
        "students": manifests,
        "evaluations": evaluations,
        "corpus_source": corpus_source,
        "graded_corpus_responses": len(graded_rows),
        "curriculum_tasks": len(tasks),
    }
    summary_path = OUT / "run-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    archive = package_run()
    persist("run-summary", summary_path)
    persist("ash-prime-out", archive)
    root = durable_root()
    where = str(root / RUN_ID) if root is not None else "LOCAL ONLY - see the offsite links above"
    log(f"artifacts: {where}")
    log("done")


if __name__ == "__main__":
    main()
