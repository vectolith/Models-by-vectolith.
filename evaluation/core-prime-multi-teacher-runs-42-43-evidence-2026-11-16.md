# Core Prime follow-up inference evidence — runs 42 and 43 — 2026-11-16

## Scope and current workflow state

These are pre-existing GitHub Actions runs discovered during the live repository inspection; this work did not dispatch either inference run.

- Run 42: https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813
  - Source branch: \`add-qwen25-7b-to-expanded-intake\`
  - Head SHA: \`6f9157b8a4e2150dac6a8d777ed0a8057c795251\`
  - As last inspected, overall workflow remained \`in_progress\` because Phi-4 job 133549417510 remained \`in_progress\`.
- Run 43: https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671
  - Source branch: \`audit-candidate-weight-memory-2026-11-16\`
  - Head SHA: \`fbe20c9095cbf01b12a7c35b4eae94bed1f5b1ba\`
  - Workflow completed with overall failure because SmolLM3 failed its missing-LICENSE gate; Phi-4 job 133444059471 completed successfully and uploaded artifact 14261964529.

In both runs, Granite 3.1, Granite 4.2, MiniCPM5, and LFM2.5 jobs completed successfully with real 180-case response artifacts. The SmolLM3 snapshot job failed because the downloaded snapshot had no LICENSE file. Its inference step was skipped. Its upload step reported that no files were found, so no SmolLM3 artifact was produced. Run 42 Phi-4 job 133549417510 remains in_progress and has no artifact. Run 43 Phi-4 job 133444059471 completed successfully and produced a verified 180-case artifact.

These branches predate the PR #39 snapshot-manifest correction. The failed SmolLM3 attempt in these runs did not preserve a snapshot manifest. PR #39 adds that behavior and tests it; do not attribute the later fix to these older run artifacts.

## Candidate job and artifact register

Every successful artifact was downloaded and inspected. Its JSON result array matches its JSONL records, it contains 180 unique case IDs, per-response candidate/revision/run provenance matches the top-level record, and it reports zero inference errors.

| Run | Candidate | Job ID | Artifact ID | Cases | Errors | 256-token cap hits |
|---|---|---:|---:|---:|---:|---:|
| 42 | Granite 3.1 3B-A800M | 133141260775 | 14207923899 | 180 | 0 | 90 |
| 42 | Granite 4.2 3B | 133174330091 | 14222803141 | 180 | 0 | 103 |
| 42 | MiniCPM5 2B | 133275261975 | 14230880744 | 180 | 0 | 52 |
| 42 | LFM2.5-2.6B | 133332287803 | 14262556692 | 180 | 0 | 163 |
| 43 | Granite 3.1 3B-A800M | 133143953242 | 14208733041 | 180 | 0 | 93 |
| 43 | Granite 4.2 3B | 133178581513 | 14223262221 | 180 | 0 | 103 |
| 43 | MiniCPM5 2B | 133277594971 | 14231498894 | 180 | 0 | 52 |
| 43 | LFM2.5-2.6B | 133347523890 | 14245324681 | 180 | 0 | 162 |
| 43 | Phi-4-mini-instruct | 133444059471 | 14261964529 | 180 | 0 | 69 |

The three existing teachers remain additive. LFM2.5 remains discovery-only. These are additional run-specific response sets; none replaces the run 40 response set and none has been graded or ranked.

## Immutable model revisions and execution observations

| Candidate | Immutable revision | Transformers | CPU capability in run 42 / run 43 | Peak RSS run 42 / run 43 | Mean case latency run 42 / run 43 |
|---|---|---|---|---:|---:|
| Granite 3.1 | \`a02780686e08a03fe0d2679a293b5c74a90efa89\` | 4.57.1 | AVX512 / AVX2 | 7208568 / 7101844 KiB | 27.80 / 28.73 s |
| Granite 4.2 | \`4e9c275e232f10211ec88644d106a1f6a1b60e06\` | 5.0.0 | AVX512 / AVX512 | 7824760 / 7799152 KiB | 67.34 / 65.69 s |
| MiniCPM5 | \`42433e90dad95123ab87729fd7011e7110629556\` | 4.57.1 | AVX512 / AVX2 | 5515692 / 5480056 KiB | 35.62 / 42.99 s |
| LFM2.5 | \`7141b56cd4650af95c7c7b86983443aed050c96a\` | 5.0.0 | AVX512 / AVX512 | 5944736 / 5939748 KiB | 115.48 / 50.25 s |
| Phi-4-mini | \`cfbefacb99257ffa30c83adab238a50856ac3083\` | 4.57.1 | — / AVX512 | — / 8089804 KiB | — / 62.23 s |

All nine completed candidate jobs used four visible CPUs and CPU-only PyTorch 2.8.0. The hosted runner system RAM was approximately 15.3–15.6 GiB. CPU capability and hosted machine type varied, so latency and RSS figures are per-run observations, not a controlled ranking. All runs used greedy BF16 decoding, chat template enabled, thinking disabled, and a 256-new-token limit.

Cap-hit counts are incomplete/truncated execution metadata, not correctness scores or human grades.

## Artifact integrity register

ZIP, JSON and JSONL digests were recomputed from downloaded artifacts. Artifact ZIPs are preserved by GitHub Actions; retention is 90 days.

| Run / candidate | Artifact name | ZIP SHA-256 | JSON SHA-256 | JSONL SHA-256 |
|---|---|---|---|---|
| 42 Granite 3.1 | \`prime-teacher-granite-3.1-3b-a800m\` | \`8d799a9c015ab6728079fe1f54bf8a6557d0c011d84fd4b826dbbd23e69a81fd\` | \`65b5e355da0f52f274a2104a28345420ac68e538de484ff8c2241329e9e0b137\` | \`d021c07ce5f5762056f1595f5da6e6ebf34b2db60a3addb594bc49937d7b55f5\` |
| 42 Granite 4.2 | \`prime-teacher-granite-4.2-3b\` | \`088e3dbee15c26627cc97d6cb09d46bca0a37340cc5a5ae08af86e4ccebcb45e\` | \`4930db1ce9da0ae25697572e5895b1809bb5a18f60afb67eccc6464e54f9e929\` | \`38e6a97ce518196d9c509c6b8ec2ee28889d08833d342b0f9338f487770c7a39\` |
| 42 MiniCPM5 | \`prime-teacher-minicpm5-2b\` | \`8375eb2eb02192c07c5fdebdf661bda4c9eeb54d852f40679a3863f1210e94d4\` | \`4314d4b5a64d61ad6270ed6eeed003d1ef917030c36ef9c6e3745ee83b09fbc6\` | \`d8be112a1336d4681a60d3758390d60fa88c582a8f9b400b2907b44786704748\` |
| 42 LFM2.5 | \`prime-teacher-lfm2.5-2.6b\` | \`f6502425a369cd3b86347c311445c729793f45f438e4f4aa4a6f155406216e64\` | \`eb784cf48513ef9d52df7c5d73025062a8bf3be1311edd3484d7a2a157e96833\` | \`b6cf6e140f354e36d56b1588ea1c653f71ef590e6881c7b1a1ac13793df66808\` |
| 43 Granite 3.1 | \`prime-teacher-granite-3.1-3b-a800m\` | \`3e3e6d563c1deeb696f7004195de09172e4e2f2f49a2229a9c4d8d82d5218c05\` | \`fb87fdbf14e2967c44eaeb02e70fdd985dad6eeb9dba3f396d8911b9654a8122\` | \`db11e1c6b980a33cb7427771571b79d9713f28f95b6a910afdc44c9bb68ea5de\` |
| 43 Granite 4.2 | \`prime-teacher-granite-4.2-3b\` | \`a3781ef0dd5240eca4f223a44f69c39f641bb20d9adf6d2bb7f4efb3b44c2739\` | \`90026164949b4eb58cd2c082e20a205806eab3a1cc087fd994de55448120d5cd\` | \`06652a1b6afc7955bc5b14ded5283c5b9f20a93e602c16cca23ac49ccfece6fe\` |
| 43 MiniCPM5 | \`prime-teacher-minicpm5-2b\` | \`109c2f235ab8edde59b2beeeedf778f6ae3babf309e70952c62febf09cf93acb\` | \`d14d818dcbb1938e0caa3d8507fee64e3b70d587921027e97102c149543470a9\` | \`a2053c0ecdbcfbb339c1c8aefbc4e7323421b2eeb34756750eee124978fbc0f6\` |
| 43 LFM2.5 | \`prime-teacher-lfm2.5-2.6b\` | \`7130d8c7f4754e689f4652951a12f09e70df43f7c7e67ecc27dfb1a1fea192ca\` | \`3b9b6dd658baee431f72beb9090992449684d83e39b58a3187d046b043628355\` | \`ea8e5aa4292b0c953f03f087303723993027e5b449921b4c64a174a8d2fde0bf\` |
| 43 Phi-4-mini | \`prime-teacher-phi-4-mini-instruct\` | \`584ac7979398db27234870b72e3c94c65ff79749828e78ba388db198c68df50f\` | \`0910b02c67b0bb11993a34f50ba075e6c1b44d0ce157211458d060cb366b80ff\` | \`b229dfae12981680547b5f3f28cb2f37a05299d81014a7553a3fcd6574dbdb69\` |

Artifact links:

- Run 42 Granite 3.1: https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813/artifacts/14207923899
- Run 42 Granite 4.2: https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813/artifacts/14222803141
- Run 42 MiniCPM5: https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813/artifacts/14230880744
- Run 42 LFM2.5: https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813/artifacts/14262556692
- Run 43 Granite 3.1: https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671/artifacts/14208733041
- Run 43 Granite 4.2: https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671/artifacts/14223262221
- Run 43 MiniCPM5: https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671/artifacts/14231498894
- Run 43 LFM2.5: https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671/artifacts/14245324681
- Run 43 Phi-4-mini: https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671/artifacts/14261964529

## Candidate and training disposition

- Granite 3.1, Granite 4.2 and MiniCPM5 remain the three existing additive Core Prime teachers.
- LFM2.5 remains discovery-only despite repeated successful inference. Its 90%–90.6% cap-hit rate remains a major completeness concern; legal review and separate written training-output permission remain outstanding.
- Phi-4 run 42 remains in progress without an artifact. Phi-4 run 43 completed successfully and produced 180 responses; it remains discovery-only and unqualified.
- SmolLM3 remains blocked by the missing LICENSE file. No response artifact exists from either run.
- Qwen3.5-2B and Gemma 4 E2B IT remain discovery-only. Nemotron 3 Nano 4B remains deferred.
- No human grades were created. No candidate was qualified, ranked, or selected. No response was overwritten or discarded.
- Core Prima remains paused. No training has started.


### LFM2.5 and Phi-4 snapshot manifest digests

Both LFM2.5 artifacts include the 11-file immutable snapshot inventory. The LICENSE file digest is unchanged across both snapshots. These are snapshot-presence/inventory facts only; legal review and training-output permission remain pending.

- Run 42 manifest SHA-256: \`61f3b506ee8482260bab96d6a46814b52a21c23e66d0d1bb758eebb7c0582b71\`
- Run 43 manifest SHA-256: \`7af841740157d4aa89c3f19f14d99913174c279999e8b32d1786969a846a12c9\`
- LICENSE SHA-256 in both: \`4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c\`


- Run 43 Phi-4 snapshot manifest SHA-256: \`837c68404e8ccce17fbe7d1c88c23d58731021805663ecea2ba78f06bcd0a1c9\`; 21 files, 7,694,054,130 bytes.
- Run 43 Phi-4 LICENSE SHA-256: \`fa8235e5b48faca34e3ca98cf4f694ef08bd216d28b58071a1f85b1d50cb814d\`.

- Run 43 Phi-4 manifest SHA-256: `837c68404e8ccce17fbe7d1c88c23d58731021805663ecea2ba78f06bcd0a1c9`; 21 files, 7,694,054,130 bytes.
- Run 43 Phi-4 LICENSE SHA-256: `fa8235e5b48faca34e3ca98cf4f694ef08bd216d28b58071a1f85b1d50cb814d`.
