# Core Prime expanded evaluation curriculum — v4

Status: public development suite validated. The 56-case fixture has four cases in each of 14 competencies, three rubric criteria per case, unique IDs, and no ID collisions with v1-v3. Real v1-v4 CPU response artifacts are preserved for the three existing Core Prime teachers plus LFM2.5-2.6B and Phi-4 Mini across [workflow run #40](https://github.com/vectolith/Models-by-vectolith./actions/runs/43796213917), [run #42](https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813), and [latest run #43](https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671). These are raw public-suite responses, not human grades or teacher-qualification evidence. The suite is not a secret holdout.

## Validation evidence

- Fixture inspection: 56 cases, 14 competencies, exactly four cases per competency; every case has three rubric criteria; IDs are unique and do not collide with v1-v3.
- GitHub Actions: [Core Prime runtime and evaluation tests #520](https://github.com/vectolith/Models-by-vectolith./actions/runs/44311872306) passed 110 tests (3 skipped), including both v4-specific tests. [Vectolith Runtime #349](https://github.com/vectolith/Models-by-vectolith./actions/runs/44311872304) passed 84 tests.
- Real public-suite inference: [runs #40](https://github.com/vectolith/Models-by-vectolith./actions/runs/43796213917), [#42](https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813), and [#43](https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671) each captured 180 records per successful teacher/candidate across v1 (12), v2 (20), v3 (92), and v4 (56). Fifteen response artifacts are preserved for five additive contributors across three runs; each workflow's overall failure was caused by the separate SmolLM3 snapshot job failing its license-file gate.
- Raw outputs remain ungraded. Token-cap responses are incomplete evidence and must not be treated as completed answers. No teacher is qualified by this validation.

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
