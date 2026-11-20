# Core Prime Run 42 Grading pilot — 2026-11-17

## Status

**Pilot only; the Grading gate remains blocked.** This report records a single-pass assistant assessment of 30 public benchmark responses: six named cases for each of five pinned teacher revisions. It is not a completed 900-response grading report and does not qualify any teacher.

The embedded case rubrics were applied criterion by criterion. A criterion receives credit only when the response visibly demonstrates it. Truncated or unfinished responses do not receive credit for requirements they never demonstrate. No keyword-overlap score was used.

## Scope and evidence binding

Workflow run: `43820188813`, Run 42. Source branch: `add-qwen25-7b-to-expanded-intake`; source commit: `6f9157b8a4e2150dac6a8d777ed0a8057c795251`. This is not PR #73's branch.

Each score is bound to the candidate's Run 42 ZIP artifact and immutable revision:

| Candidate | Immutable revision | Artifact ID | ZIP SHA-256 |
|---|---|---:|---|
| Granite 4.2 3B | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | `14222803141` | `088e3dbee15c26627cc97d6cb09d46bca0a37340cc5a5ae08af86e4ccebcb45e` |
| LFM2.5 2.6B | `7141b56cd4650af95c7c7b86983443aed050c96a` | `14262556692` | `f6502425a369cd3b86347c311445c729793f45f438e4f4aa4a6f155406216e64` |
| Phi-4-mini-instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | `14280614317` | `9b34e52ef661236741bae16b7de0ce9b04b065fdb223e2aec3bfb4d812cbac4c` |
| Granite 3.1 3B-A800M | `a02780686e08a03fe0d2679a293b5c74a90efa89` | `14207923899` | `8d799a9c015ab6728079fe1f54bf8a6557d0c011d84fd4b826dbbd23e69a81fd` |
| MiniCPM5 2B | `42433e90dad95123ab87729fd7011e7110629556` | `14230880744` | `8375eb2eb02192c07c5fdebdf661bda4c9eeb54d852f40679a3863f1210e94d4` |

All five ZIPs were downloaded in this turn. Their SHA-256 digests were recomputed from the downloaded bytes and match the GitHub artifact metadata.

## Pilot results

Scores are criterion-level passes over the rubric criteria for each case. The order of candidate columns is Granite 4.2, LFM2.5, Phi-4, Granite 3.1, MiniCPM5.

| Case | Criteria | Granite 4.2 | LFM2.5 | Phi-4 | Granite 3.1 | MiniCPM5 |
|---|---:|---:|---:|---:|---:|---:|
| `prime-reasoning-001` | 4 | 2/4 | 3/4 | 4/4 | 3/4 | 3/4 |
| `prime-reasoning-002` | 3 | 3/3 | 0/3 | 0/3 | 3/3 | 3/3 |
| `prime-math-001` | 4 | 2/4 | 4/4 | 4/4 | 4/4 | 2/4 |
| `prime-knowledge-001` | 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `prime-instruction-001` | 4 | 3/4 | 0/4 | 4/4 | 1/4 | 3/4 |
| `prime-synthesis-001` | 4 | 4/4 | 4/4 | 2/4 | 2/4 | 2/4 |
| **Pilot total** | **22** | **17/22** | **14/22** | **17/22** | **16/22** | **16/22** |

These are descriptive pilot results only. Six public cases are not a sufficient basis for teacher ranking or selection.

## Material findings

- **Logical inference:** LFM2.5 and Phi-4 incorrectly conclude that panel members must have submitted comments. The premises do not establish that; Granite 4.2, Granite 3.1 and MiniCPM5 answer correctly.
- **Arithmetic:** Phi-4, LFM2.5 and Granite 3.1 return the correct 7,740 result. Granite 4.2 and MiniCPM5 stop before completing the final addition in their sampled outputs.
- **Instruction following:** Phi-4 satisfies the four-bullet and word-limit constraints in the sampled response. Granite 3.1 uses a numbered list and exceeds the word limit in its final item. LFM2.5 emits planning/self-referential text instead of a completed four-bullet answer.
- **Comparison:** Granite 4.2 and LFM2.5 identify B as cheaper and A as faster. Phi-4, Granite 3.1 and MiniCPM5 misidentify at least one of those comparisons.
- All five sampled answers to the future Olympics question avoid inventing a winner.

## Full-artifact generation observations

Across all 180 responses per candidate, generation-cap hits were:

| Candidate | Token-limit responses | Rate |
|---|---:|---:|
| Granite 3.1 3B-A800M | 90/180 | 50.0% |
| Granite 4.2 3B | 103/180 | 57.2% |
| MiniCPM5 2B | 52/180 | 28.9% |
| LFM2.5 2.6B | 163/180 | 90.6% |
| Phi-4-mini-instruct | 63/180 | 35.0% |

These are generation-completion statistics, not rubric grades. The high cap-hit rate, especially for LFM2.5, warrants a controlled follow-up with an appropriate generation budget before interpreting capability.

## Coverage and release gate

- Responses in the five artifacts: 900.
- Responses graded in this pilot: 30.
- Responses not yet graded: 870.
- Coverage: 30/900 (3.33%).
- Per-candidate Grading coverage: 6/180.
- Grading status: `pending`; not `passed`.
- No teacher is qualified by this report. No foundation is selected. No training is authorized or started.

The remaining 870 outputs must be graded against their embedded rubrics and the full report digest recorded before the Grading gate can pass. Separate licensing, output-generation permission, safety, corpus, protected-holdout and foundation approval gates remain outstanding.

## Assessment method and limitations

This is a single-pass assistant rubric assessment of public benchmark outputs, not an independent human review, private holdout evaluation, or source-verified factuality audit. It is intentionally limited to the six cases listed above. The rubric criteria are those embedded in the Run 42 evaluation records. No reviewer-count, reviewer-independence, agreement-threshold or adjudication requirement was added to this Grading pilot.

The assessment does not establish license compliance, rights-holder permission, generalization, resistance to benchmark contamination, or teacher suitability.
