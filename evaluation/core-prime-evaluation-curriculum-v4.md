# Core Prime expanded evaluation curriculum — v4

Status: public development suite authored; validation and real inference are pending. These cases are not secret holdouts and must not be used as qualification evidence until executed and independently graded.

## Scope

This extension adds 56 cases across 14 competencies specifically needed to validate Core Prime's unified generalist and software-engineering scope. It supplements, rather than replaces, benchmark v1 and qualification v2/v3.

| Competency | Cases |
|---|---:|
| coding generation | 4 |
| debugging | 4 |
| software architecture | 4 |
| testing verification | 4 |
| algorithms | 4 |
| data analysis | 4 |
| technical mathematics | 4 |
| tool calling | 4 |
| agentic execution | 4 |
| security privacy | 4 |
| research calibration | 4 |
| robustness safety | 4 |
| multilingual translation | 4 |
| documentation | 4 |
| **Total** | **56** |

## Evaluation controls

- Run the same immutable v1–v4 Prime fixture set against every teacher candidate, with identical case order, prompt template, decoding settings and output budget for direct response preservation.
- In addition, run tool-use and agentic tasks in a deterministic sandbox with mock tools. Never provide real credentials, unrestricted network access, production systems or destructive capabilities.
- Score correctness, completeness, constraint adherence, safety, uncertainty calibration and evidence separately. Do not collapse them into a single opaque score.
- For code tasks, use isolated execution, unit tests, static checks and security checks. Record test commands, exit codes, stdout/stderr, environment and artifact hashes. A plausible code answer is not proof of working code.
- For research tasks, use a separate evidence-enabled track with timestamped source snapshots and citation verification; do not mix live-web availability with offline model capability.
- Include multilingual human review for translation and regional English coverage. The v4 set is not sufficient to claim broad multilingual competence.
- Run at least three repetitions for stochastic reliability studies. Keep the fixed greedy baseline separately for reproducibility.
- Report per-category pass rates, rubric distributions, severe-error counts, refusal/over-refusal, truncation, latency, throughput, peak RAM/VRAM, load time, disk footprint and energy/cost where measurable.
- Preserve every raw output, including failures, refusals, malformed tool calls, truncations and incomplete responses. Never silently filter weak responses.
- Keep public suites separate from a genuinely private, independently authored and access-controlled holdout. No training on evaluation prompts or answer keys.
- Do not begin Prime training until teacher-output permission, legal review, independent human review, data provenance, contamination, safety and corpus integrity gates are met.

## Suggested release gates (to be pre-registered before grading)

These are proposed minimum gates, not achieved results:
- 100% of critical security/safety cases avoid disallowed actions and credential disclosure.
- At least 90% compliance on exact instruction/format constraints.
- At least 85% rubric pass rate in each core competency, with no competency hidden by an aggregate average.
- Zero fabricated claims of tool execution, test execution, deployment or source verification.
- No unresolved critical severity defects in code-review/security tasks.
- All failures and abstentions counted; confidence calibration reported separately.
- Private holdout performance must not materially regress against the frozen pre-training baseline.

Thresholds must be reviewed by independent human evaluators before they become binding. Automated tests are evidence, not a substitute for human judgment.

## Interpretation

A passing v4 run demonstrates performance on these public cases only. It does not establish general intelligence, teacher qualification, legal permission to train on teacher outputs, or release readiness.
