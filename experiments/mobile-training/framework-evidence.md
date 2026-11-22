# Mobile framework evidence (read-only research snapshot)

Date: 2026-11-22. No device build, model download, inference or training performed.

## Verified upstream facts

- **MLX Swift** is an Apple-silicon array framework. Its upstream examples include MNIST training on iOS/macOS, which proves a general differentiable training example exists on iOS but does not prove LLM LoRA training is supported there.
- The upstream **mlx-swift-examples** README currently lists `LoRATrainingExample` as a macOS example. Do not infer iOS LLM training from the package's iOS platform support or from MNIST.
- **mlx-swift-lm** includes LoRA training code and its Swift package manifest declares iOS 17. However, the example app listed upstream is macOS-only. We still need a target-specific iOS app build and on-device gradient/update proof.
- **Qwen3.5-2B-Base** model card declares Apache-2.0 and describes a 2B causal language model with a vision encoder and hybrid Gated DeltaNet/attention layout. The model card describes pretraining weights intended for research/fine-tuning, not an iOS/MLX training compatibility guarantee. Its exact immutable revision, tokenizer, conversion/layout and target-module compatibility remain unverified.
- The candidate is multimodal and hybrid. A text-only conversion, quantization, adapter-target mapping or architecture substitution must not be silently assumed.
- Checkpoint file size alone does not establish training feasibility: gradients, optimizer state, activations, temporaries, memory pressure, storage, thermals and iOS process limits must be measured on the target device.

## Source references

- MLX Swift: https://github.com/ml-explore/mlx-swift/
- MLX Swift examples (official list of MNIST and macOS LoRA example): https://github.com/ml-explore/mlx-swift-examples
- MLX Swift LM (LoRA training code; package/platform support is not device validation): https://github.com/ml-explore/mlx-swift-lm
- MLX Swift LM LoRA reference: https://github.com/ml-explore/mlx-swift-lm/blob/main/skills/mlx-swift-lm/references/lora-adapters.md
- Qwen3.5-2B-Base model card: https://huggingface.co/Qwen/Qwen3.5-2B-Base

## Decision

MLX Swift remains a research path, not a selected training stack. The package-level iOS support and LoRA code are promising, but the official LLM LoRA example is macOS-only. Qwen3.5-2B-Base remains an unapproved candidate: model-card license text is not independent legal review or written Core Prime output-training permission. Do not download weights, run inference, or train before the explicit gates.
