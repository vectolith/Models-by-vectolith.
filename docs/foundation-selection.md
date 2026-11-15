# Foundation model selection

**Status: OPEN — no foundation selected.** Do not begin expensive training until comparative evaluation and approval are complete.

## Current candidate research

See [Foundation Candidate Research — 2026-11-15](foundation-candidate-research-2026-11-15.md) for the current evidence-based shortlist, role-specific candidate priorities, architecture and deployment risks, and the reproducible evaluation protocol.

Initial priority batch:
- Qwen3.5-9B
- IBM Granite 4.2 8B
- Google Gemma 4 E4B

Mistral Small 4 remains a high-capability reference candidate subject to infrastructure feasibility. These are research priorities, not selections or endorsements.

## Required comparison

Evaluate reasoning, coding, structured tool use, global-English quality, multilingual robustness, latency, peak VRAM/RAM, serving cost, license obligations, deployment ecosystem, context behaviour, quantization, and training-harness compatibility.

Use common prompts, decoding settings where applicable, evaluation data, hardware, and reporting conventions. Include repeated-run variance or confidence intervals when practical. Keep Prime and Prima scorecards separate.

## Selection gates

A candidate requires:
1. exact model ID and immutable full revision SHA;
2. verified license and model-card provenance;
3. role-specific capability report with baselines and limitations;
4. measured memory and latency profile;
5. confirmed trainer compatibility or a scoped engineering plan;
6. documented selection rationale and approval.

Prime and Prima may use different foundations. Choose independently for capability/cost fit. Store evidence under `evaluations/foundation/<candidate>/<revision>/`. Never train from mutable tags such as `main` or `latest`.

No candidate has passed these gates yet. No foundation-specific inference adapter or expensive training should begin until the evidence supports a recorded selection.
