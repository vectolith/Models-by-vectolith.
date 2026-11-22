# Mobile framework evidence (initial research)

Date: 2026-11-22

## Findings
- **MLX Swift** is a credible investigation path: the upstream mlx-swift repository documents an iOS-compatible Swift API and examples including MNISTTrainer that runs on iOS and macOS.
- The upstream examples list a **LoRATrainingExample for macOS**, not iOS. This is evidence that LoRA training examples exist, but not evidence that the LLM LoRA example can be run on iPhone.
- MLX provides composable automatic differentiation and MLXOptimizers. iOS platform support is documented upstream, but the specific model, gradient path, adapter implementation and resource envelope still require an on-device proof.
- **Qwen3.5-2B-Base** model card states Apache-2.0 and identifies the 2B model as pre-trained weights intended for fine-tuning/in-context experiments. It uses a hybrid Gated DeltaNet and attention architecture. That makes architecture-specific implementation and support validation a critical gate.
- The 2B checkpoint in the Hugging Face repository is several GB even before considering training gradients, optimizer state, activations, temporary tensors and checkpoint copies. A phone's usable memory budget is therefore not determined by file size alone.

## Source links
- MLX Swift upstream: https://github.com/ml-explore/mlx-swift/
- MLX Swift examples: https://github.com/ml-explore/mlx-swift-examples
- Qwen3.5-2B-Base model card: https://huggingface.co/Qwen/Qwen3.5-2B-Base
- Qwen3.5-2B model card: https://huggingface.co/Qwen/Qwen3.5-2B

## Decision
Investigate MLX Swift for a small on-device differentiable prototype first. Do not claim iPhone Qwen LoRA training is already supported. The upstream LoRA LLM example is macOS-only as listed; porting, model support, memory feasibility and iOS execution must be proven. This research does not approve Qwen as Core Prime's foundation and does not authorize training.

