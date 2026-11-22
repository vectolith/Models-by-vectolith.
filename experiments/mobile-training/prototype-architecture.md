# Mobile training prototype architecture

This note is a design sketch, not an implementation or compatibility claim.

## Runtime separation
- **Inference engine:** runs the frozen base checkpoint and exposes a supported forward path.
- **Training engine:** differentiable forward path for the selected modules; must prove gradient propagation on device.
- **Adapter:** LoRA matrices and their optimizer state only.
- **Data:** local, explicit, inspectable training examples; no collection or telemetry.
- **Checkpointing:** atomic local adapter save, metadata and SHA-256; recover after interruption.
- **Evaluation:** baseline and adapted comparison with a fixed test suite.

## LoRA concept
For a frozen linear projection W, train the low-rank update:
\[
W' = W + (\alpha/r)BA
\]
where A and B are the only trainable parameters in the first experiment. Verify that the implementation's actual tensor dimensions, target modules and scaling match the selected model architecture.

## Mobile safety constraints
- Keep the initial experiment tiny and bounded.
- Explicitly surface memory allocation failure and stop rather than retrying indefinitely.
- Respect iOS suspension/backgrounding; checkpoints must tolerate interruptions.
- Do not claim that device temperature or battery health is safe based on incomplete telemetry.
- Keep training data and adapter artifacts local unless the user explicitly exports them.

## Implementation decision gate
Choose a framework only after confirming that it supports:
1. iOS deployment and Apple-device acceleration.
2. Gradient/autodiff for the necessary tensor operations.
3. Optimizer state and parameter mutation.
4. Access to the model layers/weights without opaque inference-only interfaces.
5. Adapter save/load and compatible inference.
6. No cloud service or paid license requirement.

A runtime that only supports inference does not satisfy this experiment.
