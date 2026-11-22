# iPhone 16 Pro mobile fine-tuning feasibility experiment

**Status: feasibility design; no training started, no foundation selected, no model weights downloaded.**

## Goal
Determine whether genuine parameter updates to a small Qwen-family checkpoint can be performed locally on an iPhone 16 Pro, with a measurable and reproducible result, without paid services or cloud compute.

This is an exploratory experiment, not a Core Prime training approval. Qwen is a candidate only; verify exact model revision, license, architecture support and mobile framework support before proceeding.

## Reality check
- iOS inference support is not proof that training is supported.
- Full-model training is out of scope for this device.
- Adapter-only training (LoRA) is the sole initial target.
- A custom iOS app/runtime may be needed; PocketPal is currently an inference/import target, not assumed to expose training.
- Memory, thermal throttling, compute kernels, gradient support, storage, and iOS background execution may be limiting.
- Do not use private/compromised evaluation data or claim model quality from a tiny feasibility set.

## Proposed stages and hard gates

### 0. Candidate and license gate
- Identify a small base checkpoint (initial target: Qwen 3.5 2B only if the exact released artifact is verified).
- Record immutable revision, license and training/derivative terms.
- Confirm tokenizer, model architecture and tensor layout.
- If this fails, stop and report; don't substitute silently.

### 1. Mobile framework proof
- Investigate on-device Swift/Metal or another genuinely iOS-supported stack with automatic differentiation.
- Confirm that gradients and optimizer updates are supported for the chosen operations on-device.
- Benchmark inference and peak memory first.
- No dependency on CUDA, desktop-only Python, remote GPU, paid service or hidden cloud.

### 2. Tiny synthetic adapter proof
- Use a toy/synthetic dataset (not intended for model capability claims).
- Freeze all base weights.
- Train a small LoRA adapter on a single supported layer or small subset.
- Record trainable parameter count, gradient norms, loss before/after, optimizer, steps, elapsed time, memory estimate and device thermal state if accessible.
- Save and reload adapter; demonstrate that output changes attributable to adapter can be observed.
- Ensure reproducibility and integrity hashes.

### 3. Scaling test
- Only after stage 2 succeeds, incrementally increase sequence length, batch size and adapter coverage.
- Stop on memory/thermal instability. No uncontrolled long-running loop.

### 4. Evaluation and Core Prime decision
- Evaluate adapter against an untouched baseline with a fixed, small, disclosed test set and deterministic checks.
- Separate feasibility evidence from quality evidence.
- Do not merge an experimental adapter into Core Prime or authorize training until project gates (rights, approved foundation, protected holdout, grading, compute, preflight and explicit approval) are met.

## Acceptance criteria
- Training is demonstrably occurring on-device (no remote compute).
- Base weights remain frozen.
- At least one adapter parameter is updated by the optimizer.
- Loss and update evidence are recorded, with safeguards against trivial leakage.
- Adapter is saved, reloaded and produces the expected effect.
- Test script or repeatable device procedure, hashes and environment details are documented.
- Limitations and failures are disclosed.

## Immediate work items
1. Validate current Qwen 3.5 releases, model card, license and tokenizer/architecture details.
2. Research current mobile autodiff/training capabilities for iOS/Metal, using authoritative sources.
3. Create a minimal architecture and resource-budget prototype plan before committing to app implementation.
4. Do not start training or downloading weights until candidate/licensing gate is satisfied.
