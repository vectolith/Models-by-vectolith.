# NVIDIA Nemotron specialist teacher research note

**Status: research reference only. No teacher qualification or output permission is granted.**

NVIDIA's Nemotron teacher family provides specialized checkpoints intended for synthetic-data generation, response grading and multi-teacher on-policy distillation. This aligns with vectolith's planned task/domain-based teacher routing, verified multi-teacher distillation and independent Prime/Prima evaluation. It is a reference for evaluation and orchestration design, not a dependency or architecture to copy wholesale.

## Specialist roles

| Checkpoint | Primary documented role | Potential vectolith evaluation domain |
|---|---|---|
| `NVIDIA-Nemotron-Labs-Teacher-STEM` | Math, code, natural sciences, humanities, knowledge QA and reasoning traces | STEM/math reasoning and source-grounded technical explanations |
| `NVIDIA-Nemotron-Labs-Teacher-General-Reasoning` | General reasoning, logic and multi-step problems | General reasoning and planning |
| `NVIDIA-Nemotron-Labs-Teacher-Instruction-Following` | Constraint satisfaction, structured output and format adherence | Instruction compliance and output contracts |
| `NVIDIA-Nemotron-Labs-Teacher-Competition-Coding` | Competitive programming, algorithms and verified coding traces | Coding and algorithmic reasoning |
| `NVIDIA-Nemotron-Labs-Teacher-Chat` | Multi-turn conversation, helpfulness, tone and preference alignment | Conversational quality and response style |

The published cards describe these checkpoints as 550B total / 55B active LatentMoE models, up to 1M context, with a stated minimum GPU profile around 4xGB200/4xB200 or 8xH100 depending on checkpoint. They use the custom OpenMDW License Agreement 1.1. The active-parameter count must not be mistaken for total checkpoint memory or hardware requirements.

## Implications for vectolith

1. Treat each checkpoint as a specialist teacher candidate with its own task eligibility, exact revision, license record, generation configuration and evaluation results.
2. Route only tasks matching the verified specialization. A STEM teacher must not silently become the default coding, conversational or safety teacher.
3. Require evidence-bound outputs: exact teacher revision, request/response digests, rubric and verification results, source provenance and explicit output-generation rights.
4. Use deterministic verifiers, executable tests and source checks wherever possible. Teacher consensus is not a substitute for independent verification.
5. Keep ASH PRIME and FYR PRIMA evaluation independent; do not allow the teacher pool to grade itself without a separate evaluation boundary.
6. Compare remote inference and self-hosting costs before selecting any 550B-total checkpoint for routine generation. A 55B active count does not make the full model small to store or load.

## Qualification status

These models are not part of Run 42's five-candidate, 900-response population. No exact immutable revisions, license-file digests, legal approvals, project-specific output permissions, inference artifacts or qualification manifests are recorded here. They do not count toward the minimum four qualified teachers. Any future inclusion requires a separate controlled run and complete evidence package.

## Sources

- [NVIDIA Nemotron 3.5 Super and Lightning release](https://research.nvidia.com/labs/nemotron/Nemotron-3.5-Super-and-Lightning/)
- [Teacher-STEM](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-STEM)
- [Teacher-General-Reasoning](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-General-Reasoning)
- [Teacher-Instruction-Following](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Instruction-Following)
- [Teacher-Competition-Coding](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Competition-Coding)
- [Teacher-Chat](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Chat)
- [Nemotron 3.5 Lightning training recipe](https://docs.nvidia.com/nemotron/nightly/nemotron/lightning35/README.html)
