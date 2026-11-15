# Prime and Prima teacher qualification plan

**Status: candidate pools defined; zero teachers qualified or appointed yet.**

The non-negotiable requirement is **at least four distinct, qualified teacher models for Core Prime and at least four for Core Prima**. The panels may overlap, but each student must independently meet the four-teacher requirement. A model appearing in a shortlist does not count as a teacher.

## Candidate pools

The machine-readable pool is `evaluation/fixtures/teacher_panel_candidates_v1.json`. It intentionally contains more than four candidates per student so a model that fails quality, permission, efficiency, or availability checks can be replaced without lowering the standard.

### Core Prime

| Candidate | Purpose | Main qualification risk |
|---|---|---|
| Qwen3.5-9B | Broad reasoning, multilingual and general capability | Hybrid architecture, deployment/training compatibility |
| Gemma 4 E4B | Efficient generalist and multimodal comparator | Full weight/PLE memory, serving compatibility |
| Granite 4.2 8B | Dense reasoning and tool-use comparator | Memory/throughput relative to quality |
| gpt-oss-20b | MoE reasoning and instruction-following | 21B total weight storage; Harmony format |
| Qwen2.5-7B-Instruct | User-requested replacement comparator | Must demonstrate quality and efficiency against newer candidates |
| Devstral Small 2 24B | Independent cross-family reserve | Dense 24B memory footprint |

### Core Prima

| Candidate | Purpose | Main qualification risk |
|---|---|---|
| Qwen3-Coder-Next | Coding-agent specialist | 80B total weights despite 3B active parameters |
| Granite 4.2 8B | Coding, reasoning and tool-use | Must prove repository-level correctness |
| gpt-oss-20b | Reasoning and structured tool-use | Code correctness and Harmony tool-call fidelity |
| Gemma 4 E4B | Efficient technical and multimodal comparator | Must prove software-engineering quality |
| Qwen2.5-Coder-7B-Instruct | Compact code-specialist comparator | Older generation; verify exact license and quality |
| Devstral Small 2 24B | Repository-level software engineering specialist | 24B dense footprint and zero-cost availability |

These are **qualification candidates**, not the final four. The candidate pool remains extensible; discovery must admit better models and additional families.

## How the final four are selected

No model is selected by parameter count, provider reputation, public benchmark claims, or model-family diversity alone. Each candidate must pass the same versioned qualification harness for the competencies it is expected to teach.

Hard gates:

1. Resolve and retain the exact immutable checkpoint revision, tokenizer revision, model configuration, chat template, license file and hashes.
2. Verify the exact model license and any provider/inference terms. Apache-2.0 model weights do not, by themselves, prove that a hosted provider permits output reuse for student training.
3. Obtain documented, reviewed permission for the generated outputs to be used to train the intended student. If this is not established, the model cannot be appointed.
4. Run the complete role-specific suite with raw outputs, reproducible settings and independent grading. Rubric keyword matching alone is not a qualification.
5. Measure quality by competency, factuality, uncertainty calibration, instruction adherence, multilingual performance, tool-call validity, repeated-run variance and failure rate.
6. Measure actual operating efficiency: peak RAM/VRAM, total checkpoint footprint, KV-cache growth, cold-start/load time, time-to-first-token, p50/p95 latency, tokens/sec, throughput, accepted examples/tokens per unit of compute, and cost per accepted training token.
7. Verify that the exact checkpoint can be run on genuinely free compute available to the project. Free-to-download weights, promotional credits and an unverified free-tier claim do not count as available compute.
8. Generate a pilot contribution shard, cross-review it, apply deterministic/executable checks where possible, and prove the teacher contributes useful accepted examples.
9. Run leave-one-teacher-out ablation. A teacher that adds no measurable held-out capability is replaced, even if that would otherwise leave four; qualification is not a headcount exercise.

The final panel should be a quality/efficiency Pareto choice: retain candidates that add meaningful capability at acceptable measured resource cost. Prefer independent model families where the quality and cost are comparable, but do not choose a weaker model solely to diversify providers.

## Role-specific qualification suites

**Prime:** general reasoning, factual knowledge and calibration, instruction following, long-form writing, synthesis, planning, ambiguity handling, global English and World Englishes, multilingual comprehension/code-switching, and safe everyday assistance.

**Prima:** repository-level issue resolution, multi-file coding, debugging, test creation and execution, code review, secure coding, mathematics, structured tool calls, tool failure recovery, and evidence-based completion reporting. Use isolated sandboxes; never execute arbitrary model-generated code on the runner host.

Each task must have an objective or human-reviewed rubric. Keep public starter tasks separate from a private holdout. Track performance per competency; do not collapse all results into one opaque aggregate score.

## Efficiency and zero-budget policy

- Compare multiple sizes within each model family where practical.
- Compare dense and MoE models using both total weight footprint and active compute; active parameters do not eliminate weight storage.
- Evaluate full precision and explicitly identified quantized variants as separate artifacts. Never compare one candidate's BF16 weights with another candidate's quantized weights without recording the difference.
- Do not pay for APIs, GPU time, storage, or credits. Promotional trials are not recurring free compute.
- If a candidate cannot be evaluated with verified free resources, mark it **blocked by compute availability**, not qualified and not failed on model quality.
- Do not begin student training until the foundation is selected and four teachers per student have passed all gates.

## Current decision

The manifest records six candidates for each student. **The number of qualified teachers is currently zero for Prime and zero for Prima.** Qwen2.5-7B-Instruct remains in Prime's evaluation pool as requested; it does not automatically displace newer models or become a teacher without passing the same tests.

Next execution is to resolve immutable revisions and license snapshots for the complete pools, expand the role-specific qualification suites, and run real evaluations on verified no-cost compute. Once evidence exists, appoint the best four or more for each student, create contribution shards, and require positive per-teacher ablation before accepting the panel.
