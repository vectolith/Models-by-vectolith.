# Training and promotion

## Training prerequisites

Core Prime training is blocked until its foundation is selected and pinned to an immutable revision; licenses are reviewed; data provenance and splits are documented; trainer compatibility is proven; baselines are complete; and an approved execution environment with measured capacity is available. No execution may begin without explicit approval of the exact environment and run configuration. A reproducible configuration, rollback plan and explicit owner authorization are also required.

Do not launch expensive jobs on smoke-test data or unverified hardware assumptions.

## Independent runs

Every active model has its own run ID, configuration, dataset, checkpoint, evaluation report and promotion decision. Core Prima is paused and has no active run. Every Core Prime run records model and tokenizer revisions, dataset hashes, training-code commit, hyperparameters, seed, hardware/runtime versions, logs, checkpoints and limitations.

## Promotion gates

A release must pass training integrity/reproducibility, held-out role-specific capability tests, regressions against foundation and previous release, safety/instruction hierarchy, tool-use/serialization conformance, family identity/interoperability, latency/memory/deployment smoke tests, and license/artifact/model-card completeness.

A failed gate blocks promotion. Training loss alone is never sufficient. Future specialist models may be promoted independently under their own release gates.
