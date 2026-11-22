# Local toy LoRA training proof

This Swift package is a small, executable proof of adapter-only optimization on synthetic data. It is deliberately not Qwen, Core Prime, or an iOS device validation.

Run from this directory with `swift test` and `swift run`.

It demonstrates a frozen scalar base weight and trained low-rank factors, loss reduction, and unit tests. No cloud services or pretrained weights are used.
