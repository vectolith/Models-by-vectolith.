# Local toy LoRA training proof

This Swift prototype trains a low-rank adapter on a frozen scalar linear layer using synthetic data. It is intentionally model-agnostic and is **not** Qwen training, Core Prime training, or evidence that MLX/Qwen kernels work on iOS.

## Run
Open the Swift package in Xcode on an Apple platform or run it with Swift installed:
`swift run`

## Demonstration
- frozen base weight stays constant
- adapter factors A and B are the only updated parameters
- loss decreases on a bounded synthetic dataset
- outputs, metrics and base-weight preservation are printed

The prototype establishes a small executable training loop to test in the iPhone environment before adding model-specific frameworks. It does not use cloud compute.
