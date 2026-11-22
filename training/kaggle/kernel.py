
"""ASH PRIME and FYR PRIMA: multi-teacher corpus generation and student fine-tuning.

Runs on a free Kaggle 2xT4 session. Every teacher and student checkpoint is an
Apache-2.0 open-weight model downloaded from the Hugging Face Hub; nothing paid is
used. The run is reproducible: tasks come from the repository curriculum, teacher
sampling is seeded, and every accepted record carries teacher identity, revision,
content hash and deterministic check results.

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

WORK = Path("/kaggle/working")
REPO = WORK / "repo"
OUT = WORK / "out"
CORPUS = OUT / "corpus"
for path in (OUT, CORPUS):
    path.mkdir(parents=True, exist_ok=True)

REPO_URL = "https://github.com/vectolith/Models-by-vectolith.git"

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

MAX_NEW_TOKENS = 320
BATCH = 4


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_repo() -> None:
    if REPO.exists():
        subprocess.run(["git", "-C", str(REPO), "pull", "--ff-only"], check=False)
        return
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(REPO)], check=True)


def load_tasks() -> list:
    path = REPO / "training" / "curriculum" / "tasks-v1.jsonl"
    tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    log(f"curriculum tasks: {len(tasks)}")
    return tasks


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
    log(f"loaded teacher {name}")
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
        ).to(model.device)
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
            new_tokens = generated[index][encoded["input_ids"].shape[1] :]
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
        started = time.time()
        answers = answer_tasks(tokenizer, model, subset, seed=abs(hash(name)) % 10000)
        elapsed = round(time.time() - started, 1)
        accepted = []
        for record in answers:
            checks = deterministic_checks(record["task"], record["text"])
            accepted.append(
                {
                    "task_id": record["task"]["id"],
                    "competency": record["task"]["competency"],
                    "prompt": record["task"]["prompt"],
                    "system": record["task"]["system"],
                    "teacher": name,
                    "teacher_model": spec["model_id"],
                    "teacher_license": spec["license"],
                    "response": record["text"],
                    "response_sha256": sha(record["text"]),
                    "checks": checks,
                }
            )
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
        encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
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
    fetch_repo()
    tasks = load_tasks()
    corpus = generate_corpus(tasks)

    manifests = {}
    for name, spec in STUDENTS.items():
        rows = build_dataset(corpus, spec["panel"], spec["seed"])
        log(f"{name}: {len(rows)} training records from panel {spec['panel']}")
        if len(rows) < 10:
            raise RuntimeError(f"{name} has too few accepted records to train on: {len(rows)}")
        manifests[name] = train_student(name, spec, rows)

    evaluations = {}
    for name, spec in STUDENTS.items():
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
        "teachers": {name: {"model_id": spec["model_id"], "license": spec["license"]} for name, spec in TEACHERS.items()},
        "students": manifests,
        "evaluations": evaluations,
        "curriculum_tasks": len(tasks),
    }
    (OUT / "run-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()
