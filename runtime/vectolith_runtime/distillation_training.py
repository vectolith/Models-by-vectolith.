"""Reproducible, leakage-resistant supervised distillation training.

Training is opt-in. This module validates all evidence before loading model
weights, keeps prompt groups disjoint across train/validation, and records the
exact run configuration and data lineage.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from .training_preflight import validate_training_preflight


def split_dataset_by_prompt_group(
    rows: list[dict[str, Any]], *, validation_fraction: float = 0.1, seed: int = 42,
    minimum_validation_groups: int = 2,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Deterministically split by prompt digest to prevent teacher-answer leakage.

    All responses to the same prompt are assigned to one side. The training
    partition must retain at least one example from every teacher. A dataset
    too small to provide a meaningful held-out prompt set is rejected.
    """
    if not 0.05 <= validation_fraction <= 0.30:
        raise ValueError("validation_fraction must be between 0.05 and 0.30")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if minimum_validation_groups < 1:
        raise ValueError("minimum_validation_groups must be positive")
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        prompt = row.get("prompt")
        response = row.get("response")
        teacher = row.get("teacher_id")
        if not isinstance(prompt, str) or not prompt.strip() or not isinstance(response, str) or not response.strip():
            raise ValueError("every training row requires a non-empty prompt and response")
        if not isinstance(teacher, str) or not teacher.strip():
            raise ValueError("every training row requires a teacher identity")
        key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        groups.setdefault(key, []).append(row)
    if len(groups) < minimum_validation_groups + 1:
        raise ValueError(
            f"need at least {minimum_validation_groups + 1} distinct prompts for a disjoint validation split"
        )
    all_teachers = {row["teacher_id"] for row in rows}
    teacher_group_counts = {
        teacher: sum(any(row["teacher_id"] == teacher for row in values) for values in groups.values())
        for teacher in all_teachers
    }
    target = max(minimum_validation_groups, math.ceil(len(groups) * validation_fraction))
    target = min(target, len(groups) - 1)
    ranked = sorted(groups, key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    validation_keys: list[str] = []
    for key in ranked:
        if len(validation_keys) >= target:
            break
        candidate_teachers = {row["teacher_id"] for row in groups[key]}
        # Keep at least one prompt group for every teacher in the training side.
        if any(teacher_group_counts[teacher] <= 1 for teacher in candidate_teachers):
            continue
        validation_keys.append(key)
        for teacher in candidate_teachers:
            teacher_group_counts[teacher] -= 1
    if len(validation_keys) < minimum_validation_groups:
        raise ValueError(
            "cannot create the required validation split while retaining every teacher in training; "
            "collect more independent prompts per teacher"
        )
    validation_set = set(validation_keys)
    train_rows = [row for key, values in groups.items() if key not in validation_set for row in values]
    validation_rows = [row for key, values in groups.items() if key in validation_set for row in values]
    if not train_rows or not validation_rows:
        raise ValueError("training and validation partitions must both be non-empty")
    train_prompt_hashes = {hashlib.sha256(row["prompt"].encode()).hexdigest() for row in train_rows}
    validation_prompt_hashes = {hashlib.sha256(row["prompt"].encode()).hexdigest() for row in validation_rows}
    if train_prompt_hashes & validation_prompt_hashes:
        raise AssertionError("prompt leakage detected between training and validation")
    if {row["teacher_id"] for row in train_rows} != all_teachers:
        raise AssertionError("a teacher was removed entirely from the training partition")
    metadata = {
        "schema_version": "vectolith-training-data-split/1.0",
        "seed": seed,
        "validation_fraction_requested": validation_fraction,
        "distinct_prompt_groups": len(groups),
        "training_prompt_groups": len(train_prompt_hashes),
        "validation_prompt_groups": len(validation_prompt_hashes),
        "training_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "training_prompt_sha256": sorted(train_prompt_hashes),
        "validation_prompt_sha256": sorted(validation_prompt_hashes),
        "teacher_ids_in_training": sorted(all_teachers),
        "teacher_ids_in_validation": sorted({row["teacher_id"] for row in validation_rows}),
    }
    return train_rows, validation_rows, metadata


def _tokenize_batch(batch: dict[str, list[str]], tokenizer: Any, max_seq_length: int) -> dict[str, Any]:
    inputs, labels = [], []
    for prompt, response in zip(batch["prompt"], batch["response"]):
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ]
        if getattr(tokenizer, "chat_template", None):
            prompt_text = tokenizer.apply_chat_template(
                messages[:1], tokenize=False, add_generation_prompt=True
            )
            full_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        else:
            prompt_text = "### Instruction\n" + prompt + "\n\n### Response\n"
            full_text = prompt_text + response + tokenizer.eos_token
        prompt_ids = tokenizer(prompt_text, truncation=True, max_length=max_seq_length)["input_ids"]
        full_ids = tokenizer(full_text, truncation=True, max_length=max_seq_length)
        input_ids = list(full_ids["input_ids"])
        if len(input_ids) <= len(prompt_ids) or input_ids[:len(prompt_ids)] != prompt_ids:
            raise ValueError(
                "prompt tokens are not a strict prefix of the full example or the response was truncated; "
                "review the tokenizer chat template or increase max_seq_length"
            )
        label_ids = list(input_ids)
        label_ids[:len(prompt_ids)] = [-100] * len(prompt_ids)
        inputs.append(input_ids)
        labels.append(label_ids)
    return {
        "input_ids": inputs,
        "attention_mask": [[1] * len(ids) for ids in inputs],
        "labels": labels,
    }


def train_student(
    *,
    foundation_model: str,
    foundation_revision: str,
    dataset_path: str,
    output_dir: str,
    foundation_selection_manifest: str,
    teacher_qualification_manifest_dir: str,
    holdout_deployment_manifest: str,
    holdout_evaluation_results_dir: str,
    training_execution_manifest: str,
    training_code_revision: str,
    max_seq_length: int = 4096,
    epochs: float = 1.0,
    learning_rate: float = 2e-5,
    per_device_batch_size: int = 1,
    gradient_accumulation_steps: int = 8,
    validation_fraction: float = 0.1,
    seed: int = 42,
    use_lora: bool = True,
) -> dict[str, Any]:
    """Run evidence-gated SFT with deterministic validation and run provenance."""
    if not re.fullmatch(r"[0-9a-f]{40}", training_code_revision):
        raise ValueError("training_code_revision must be an immutable 40-character commit SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", foundation_revision):
        raise ValueError("foundation_revision must be an immutable 40-character commit SHA")
    if max_seq_length < 128 or epochs <= 0 or learning_rate <= 0:
        raise ValueError("max_seq_length, epochs and learning_rate must be positive and usable")
    if per_device_batch_size < 1 or gradient_accumulation_steps < 1:
        raise ValueError("batch size and gradient accumulation must be positive")

    training_config = {
        "max_seq_length": max_seq_length, "epochs": epochs, "learning_rate": learning_rate,
        "per_device_batch_size": per_device_batch_size,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "validation_fraction": validation_fraction, "seed": seed, "use_lora": use_lora,
    }
    rows, preflight = validate_training_preflight(
        dataset_path=dataset_path,
        foundation_model=foundation_model,
        foundation_revision=foundation_revision,
        foundation_selection_path=foundation_selection_manifest,
        teacher_manifest_dir=teacher_qualification_manifest_dir,
        holdout_deployment_manifest_path=holdout_deployment_manifest,
        holdout_evaluation_results_dir=holdout_evaluation_results_dir,
        training_execution_manifest_path=training_execution_manifest,
        training_code_revision=training_code_revision,
        training_config=training_config,
    )
    train_rows, validation_rows, split = split_dataset_by_prompt_group(
        rows, validation_fraction=validation_fraction, seed=seed
    )
    teacher_ids = {row["teacher_id"] for row in rows}
    counts = {teacher_id: sum(row["teacher_id"] == teacher_id for row in rows) for teacher_id in teacher_ids}
    output_path = Path(output_dir)
    if output_path.exists() and any(output_path.iterdir()):
        raise FileExistsError(f"refusing to train into a non-empty output directory: {output_path}")
    output_path.mkdir(parents=True, exist_ok=True)
    preflight_path = output_path / "training-preflight.json"
    run_manifest_path = output_path / "training-run-manifest.json"
    if preflight_path.exists() or run_manifest_path.exists():
        raise FileExistsError("training provenance files already exist; use a new output directory")

    run_manifest = {
        "schema_version": "vectolith-training-run/1.0",
        "training_code_revision": training_code_revision,
        "foundation_model": foundation_model,
        "foundation_revision": foundation_revision,
        "foundation_selection_manifest_sha256": preflight["foundation_selection_sha256"],
        "dataset_sha256": preflight["dataset_sha256"],
        "teacher_manifest_sha256": preflight["teacher_manifest_sha256"],
        "protected_holdout_deployment_sha256": preflight["protected_holdout_deployment_sha256"],
        "training_execution_manifest_sha256": preflight["training_execution_manifest_sha256"],
        "training_run_id": preflight["training_run_id"],
        "teacher_ids": sorted(teacher_ids),
        "accepted_examples_by_teacher": counts,
        "training_split": split,
        "configuration": training_config,
        "evaluation_policy": {
            "strategy": "epoch", "metric": "eval_loss", "load_best_model_at_end": True,
            "note": "Validation loss is a training diagnostic, not a substitute for independent capability evaluation.",
        },
    }
    preflight_path.write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    try:
        try:
            from datasets import Dataset
            from transformers import (
                AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq,
                Trainer, TrainingArguments,
            )
            from peft import LoraConfig, get_peft_model
        except ImportError as exc:
            raise RuntimeError(
                "training dependencies missing; install vectolith-runtime[training]"
            ) from exc
    
        tokenizer = AutoTokenizer.from_pretrained(foundation_model, revision=foundation_revision)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(
            foundation_model, revision=foundation_revision, device_map="auto"
        )
        token_counts = {
            teacher_id: sum(
                len(tokenizer(row["response"], add_special_tokens=False)["input_ids"])
                for row in rows if row["teacher_id"] == teacher_id
            )
            for teacher_id in teacher_ids
        }
        if use_lora:
            model = get_peft_model(model, LoraConfig(
                r=16, lora_alpha=32, lora_dropout=0.05,
                target_modules="all-linear", task_type="CAUSAL_LM",
            ))
    
        train_dataset = Dataset.from_list([
            {"prompt": row["prompt"], "response": row["response"]} for row in train_rows
        ])
        validation_dataset = Dataset.from_list([
            {"prompt": row["prompt"], "response": row["response"]} for row in validation_rows
        ])
        tokenize = lambda batch: _tokenize_batch(batch, tokenizer, max_seq_length)
        train_tokenized = train_dataset.map(tokenize, batched=True, remove_columns=["prompt", "response"])
        validation_tokenized = validation_dataset.map(tokenize, batched=True, remove_columns=["prompt", "response"])
        args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            learning_rate=learning_rate,
            per_device_train_batch_size=per_device_batch_size,
            per_device_eval_batch_size=per_device_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            save_total_limit=2,
            seed=seed,
            data_seed=seed,
            report_to=[],
            remove_unused_columns=False,
        )
        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=train_tokenized,
            eval_dataset=validation_tokenized,
            data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100),
        )
        trainer.train()
        evaluation = trainer.evaluate()
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)
        run_manifest["final_evaluation"] = evaluation
        run_manifest["status"] = "completed"
        run_manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return {
            "foundation_model": foundation_model,
            "foundation_revision": foundation_revision,
            "student_checkpoint": output_dir,
            "training_examples": len(train_rows),
            "validation_examples": len(validation_rows),
            "teacher_ids": sorted(teacher_ids),
            "accepted_examples_by_teacher": counts,
            "accepted_tokens_by_teacher": token_counts,
            "training_method": "LoRA-SFT" if use_lora else "full-parameter-SFT",
            "training_preflight": preflight,
            "training_preflight_manifest": str(preflight_path),
            "training_run_manifest": str(run_manifest_path),
            "final_evaluation": evaluation,
        }
    except Exception as exc:
        run_manifest["status"] = "failed"
        run_manifest["failure"] = {
            "exception_type": type(exc).__name__,
            "recorded_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        run_manifest_path.write_text(
            json.dumps(run_manifest, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        raise
