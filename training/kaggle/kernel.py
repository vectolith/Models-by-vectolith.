
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
import os
import re
import subprocess
import time
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


REPO_URL = "https://github.com/vectolith/Models-by-vectolith.git"

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


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


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
    arguments = TrainingArguments(
        output_dir=str(WORK / f"train-{name}"),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=spec["epochs"],
        learning_rate=spec["learning_rate"],
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=5,
        save_strategy="no",
        report_to=[],
        seed=spec["seed"],
        fp16=True,
        optim="paged_adamw_8bit",
    )
    trainer = Trainer(model=model, args=arguments, train_dataset=rows, data_collator=ChatCollator(tokenizer))
    started = time.time()
    result = trainer.train()
    elapsed = round(time.time() - started, 1)
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

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
    (OUT / f"{name}-training-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
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
    (OUT / f"{name}-evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    del model, base
    torch.cuda.empty_cache()
    return {"student": name, "cases": len(cases)}


def main() -> None:
    started = time.time()
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
            raise RuntimeError(f"{name} has too few accepted records to train on: {len(rows)}")
        manifests[name] = train_student(name, spec, rows)

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
    (OUT / "run-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()
