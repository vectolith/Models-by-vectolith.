# Teacher candidate efficiency review

**Status:** preliminary screening only; no teacher has been appointed.

This review narrows the initial teacher search toward capable models with practical inference profiles. It is not a benchmark ranking, a foundation selection, or approval to spend money. Model cards and published scores are vendor-reported and use different evaluation methods; they must not be treated as directly comparable.

## Selection principle

A teacher is efficient only when its measured quality is strong relative to its complete operating cost. Active parameter count alone is not enough: total parameter storage, precision, KV cache, context length, concurrency, host memory, network latency, batching, and provider pricing all matter.

Every candidate must be tested on the same vectolith teacher suite and measured in the actual deployment mode. Record at least:
- task-quality score by competency and uncertainty calibration;
- accepted training examples and accepted tokens per dollar;
- p50/p95 latency, tokens per second, throughput and failure rate;
- total weight footprint at the exact serving precision, peak VRAM/RAM and KV-cache growth;
- context length under the tested configuration;
- serving-engine compatibility and reproducibility;
- exact checkpoint revision, license, and explicit permission for generated outputs to be used in student training.

Reject a candidate that is cheap but produces weak or low-quality targets. Reject a candidate whose total storage or serving requirements make its claimed active-parameter efficiency impractical for the chosen host.

## Candidates for Core Prime

| Candidate | Evidence from official model card | Why evaluate it | Main cost or risk |
|---|---|---|---|
| OpenAI gpt-oss-20b | Apache 2.0; 21B total / 3.6B active; described for lower latency and local or specialized use | Efficient general reasoning and instruction-following teacher candidate | Requires Harmony formatting; validate actual reasoning and global-English quality |
| Google Gemma 4 26B A4B | Apache 2.0; 25.2B total / 3.8B active; multimodal, 256K context | Low active compute with broad reasoning, function calling and multilingual support | Total weights still need storage; validate teacher-output terms and deployment precision |
| Qwen Qwen3.8-27B | Apache 2.0; 27B dense; 262K native context; published coding, agentic and instruction-following evaluations | Broad generalist, long-horizon reasoning and cross-domain teacher | Dense 27B memory footprint; vendor-reported scores require reproduction |
| DeepSeek V4.1 Flash | MIT license; official card exposes Transformers, vLLM and SGLang paths | Independent reasoning and multimodal perspective | Full memory/precision requirements and training-output terms must be verified from exact revision |

## Candidates for Core Prima

| Candidate | Evidence from official model card | Why evaluate it | Main cost or risk |
|---|---|---|---|
| Qwen Qwen3.8-27B | Apache 2.0; dense 27B; published terminal coding, repository coding and agentic results | Strong technical reasoning, coding and tool-oriented task demonstrations | Dense weight footprint; reproduce results with our own repository tasks |
| Z.ai GLM-5.3-Flash | MIT license; 320B total / 18B active; supports vLLM, SGLang, Transformers, TokenSpeed and KTransformers | Coding and agentic teacher candidate with sparse/linear attention design | Very large total model; active parameters do not remove weight-storage cost |
| DeepSeek V4.1 Flash | MIT license; Transformers, vLLM and SGLang deployment paths | Independent code, math and tool-use candidate | Verify full weight footprint, precision, provider terms and actual serving performance |
| OpenAI gpt-oss-20b | Apache 2.0; 21B total / 3.6B active; lower-latency/specialized positioning | Lower-cost independent reasoning and code-review perspective | Must verify code-generation quality on our tests; Harmony format required |

These are candidate pools, not a predetermined four-teacher panel. The final four or more teachers for each student must be selected from measured results and may differ from these lists. Additional specialist models should be added when they materially improve competency coverage.

## Preliminary efficiency observations

1. **gpt-oss-20b is a high-priority efficiency candidate.** Its official card explicitly positions it for lower latency and local or specialized workloads and reports 21B total / 3.6B active parameters. The larger gpt-oss-120b is not the default teacher choice simply because it is larger.
2. **Gemma 4 26B A4B deserves a Prime teacher trial.** Its 3.8B active parameters are attractive, but its 25.2B total parameters still matter for storage and deployment.
3. **Qwen3.8-27B is a cross-role candidate.** Its official card reports 27B dense parameters, 262K native context, and vendor-published coding/agentic results. It is a strong candidate to test, not a guaranteed winner.
4. **GLM-5.3-Flash illustrates the active-parameter trap.** The official card reports 320B total and 18B active parameters. Its compute profile may be efficient, but it is not a small-weight local model.
5. **DeepSeek V4.1 Flash remains provisional.** Serving paths are documented, but exact weight footprint, precision, hardware needs and terms must be captured before any panel appointment.

## Teacher panel selection gates

For each student, run the same versioned qualification harness against the candidate pool. Select at least four distinct models only after:
- every selected teacher clears a minimum quality threshold for its assigned competencies;
- the combined panel covers all required competencies;
- measured latency, memory and reliability fit the approved deployment resource envelope;
- output-training permissions and license conditions are confirmed for the exact revision;
- a pilot proves the contribution can be reviewed, accepted and traced into the student's dataset.

Each teacher must then pass per-teacher ablation: removing its accepted contribution must measurably reduce at least one relevant held-out capability without causing unacceptable regressions elsewhere. If it does not, replace it rather than counting it to satisfy the four-teacher minimum.

## Sources

Official model cards:
- OpenAI gpt-oss-20b: https://huggingface.co/openai/gpt-oss-20b
- Google Gemma 4 26B A4B: https://huggingface.co/google/gemma-4-26B-A4B-it
- Qwen Qwen3.8-27B: https://huggingface.co/Qwen/Qwen3.8-27B
- DeepSeek V4.1 Flash: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash
- Z.ai GLM-5.3-Flash: https://huggingface.co/zai-org/GLM-5.3-Flash

All claims must be rechecked against the exact immutable revision and terms at appointment time. Published benchmark results are not vectolith evaluations.
