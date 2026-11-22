# Core Prime — PocketPal AI packaging (mobile)

This package prepares a **GGUF artifact** for PocketPal AI on iOS. It does not claim that Core Prime has trained weights or that a foundation model has been selected. Until the model-selection decision is approved, the export is a reproducible packaging workflow, not an export of Core Prime.

## Acceptance criteria

- The exact foundation checkpoint/revision and license have been approved and recorded.
- The checkpoint or trained adapter is available and the export/merge process has completed.
- A GGUF export has been produced using a compatible llama.cpp conversion path and quantization.
- `verify_gguf.py` validates the file signature and records SHA-256, file size and provenance.
- The file has been imported into PocketPal and inference has been manually verified on the target iPhone.
- Test conversations and failures are recorded. A GGUF file alone is not evidence of trained Core Prime capability.

## Export workflow (once the foundation and weights are approved)

1. Export the selected checkpoint (or merge the approved adapter into the base checkpoint first) from the verified model artifact.
2. Confirm the model architecture and tokenizer are supported by the pinned llama.cpp converter version. Unsupported architectures must be reported as blockers; don't silently substitute a model.
3. Convert to GGUF with llama.cpp's `convert_hf_to_gguf.py` script.
4. Quantize using llama.cpp's `llama-quantize` binary, selecting a quantization appropriate to the iPhone's available memory. Start with a conservative quantization such as Q4_K_M only after checking architecture compatibility and output quality.
5. Run the included verifier to generate an artifact manifest.
6. Transfer/import the GGUF into PocketPal. Verify model load, prompt template, basic generation and multi-turn conversation on device.

Example commands (placeholders; do not run until the approved checkpoint is available):

```bash
python llama.cpp/convert_hf_to_gguf.py /path/to/approved-checkpoint --outfile core-prime-f16.gguf
llama-quantize core-prime-f16.gguf core-prime-q4_k_m.gguf Q4_K_M
python mobile/pocketpal/verify_gguf.py core-prime-q4_k_m.gguf --model-id APPROVED_MODEL_ID --revision APPROVED_REVISION --quantization Q4_K_M
```

The conversion flags may differ for the selected architecture; follow the converter's pinned version help and model-specific instructions. These are illustrative commands, not a validated conversion.

## Manifest

The verifier creates a sidecar JSON file. Fields include file name, size, SHA-256, GGUF magic, model ID, immutable revision, quantization and verification timestamp. No secrets are stored.

## PocketPal verification checklist

- [ ] GGUF file transferred/imported successfully.
- [ ] Model loads without crash or memory failure.
- [ ] Correct chat template/system prompt selected.
- [ ] Short prompt generates a coherent response.
- [ ] Multi-turn context is retained.
- [ ] Generation stops correctly and can be interrupted.
- [ ] Device memory/thermal behaviour acceptable.
- [ ] Artifact hash matches sidecar manifest.

## Current status

**Blocked pending foundation selection and approved weight availability.** Repository CI can validate this packaging verifier; it cannot establish iPhone compatibility or perform device inference.
