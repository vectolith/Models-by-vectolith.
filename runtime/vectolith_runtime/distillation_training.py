"""Optional supervised distillation fine-tuning for student checkpoints.

Install the training extra before use. This module never starts training merely
by being imported; callers must explicitly invoke train_student().
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def train_student(
    *,
    foundation_model: str,
    foundation_revision: str,
    dataset_path: str,
    output_dir: str,
    max_seq_length: int = 4096,
    epochs: float = 1.0,
    learning_rate: float = 2e-5,
    per_device_batch_size: int = 1,
    gradient_accumulation_steps: int = 8,
    use_lora: bool = True,
) -> dict[str, Any]:
    """Run supervised fine-tuning on accepted teacher examples."""
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

    source = Path(dataset_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("accepted") is not True or not row.get("teacher_id") or not row.get("response"):
            raise ValueError("training dataset contains an unaccepted or provenance-free row")
        rows.append(row)
    if not rows:
        raise ValueError("training dataset is empty")
    teacher_ids = {row["teacher_id"] for row in rows}
    if len(teacher_ids) < 4:
        raise ValueError("student training requires accepted examples from at least four distinct teachers")
    counts = {teacher_id: sum(row["teacher_id"] == teacher_id for row in rows) for teacher_id in teacher_ids}
    if any(count == 0 for count in counts.values()):
        raise ValueError("every selected teacher must contribute accepted examples")

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

    dataset = Dataset.from_list([
        {"prompt": row["prompt"], "response": row["response"]}
        for row in rows
    ])

    def tokenize(batch: dict[str, list[str]]) -> dict[str, Any]:
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
            label_ids = list(full_ids["input_ids"])
            prefix = min(len(prompt_ids), len(label_ids))
            label_ids[:prefix] = [-100] * prefix
            inputs.append(full_ids["input_ids"])
            labels.append(label_ids)
        # Dynamic padding is delegated to DataCollatorForSeq2Seq.
        return {"input_ids": inputs, "attention_mask": [
            [1] * len(ids) for ids in inputs
        ], "labels": labels}

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["prompt", "response"])
    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        learning_rate=learning_rate,
        per_device_train_batch_size=per_device_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        logging_steps=10,
        save_strategy="epoch",
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100),
    )
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    return {
        "foundation_model": foundation_model,
        "foundation_revision": foundation_revision,
        "student_checkpoint": output_dir,
        "training_examples": len(rows),
        "teacher_ids": sorted(teacher_ids),
        "accepted_examples_by_teacher": counts,
        "accepted_tokens_by_teacher": token_counts,
        "training_method": "LoRA-SFT" if use_lora else "full-parameter-SFT",
    }
