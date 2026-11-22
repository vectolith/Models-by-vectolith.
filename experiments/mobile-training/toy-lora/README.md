# Local toy LoRA training proof

This small Swift package demonstrates adapter-only optimization on a synthetic scalar example. It is deliberately **not** Qwen, Core Prime, a pretrained-model adapter, or an iPhone/device validation.

Run from this directory with `swift test` and `swift run`.

The test suite demonstrates synthetic loss reduction, deterministic results, a frozen scalar base value, bounded step behavior, and invalid learning-rate rejection. No cloud services or pretrained weights are used.

The GitHub workflow uses a Linux Swift container to validate the package. That test does not prove iOS, Metal, MLX Swift, model architecture, memory, thermal, or on-device gradient support. Those require a separate device proof.
