# VELNOR data-connection download budget

**Status:** Active operating constraint for the current evaluation phase  
**Effective date:** 2026-11-16

## User-authorized connection budget

The available main data allowance is **25 GB**. The operating ceiling for VELNOR-related downloads is **20 GB total**, with **5 GB held back as a protected reserve** for ordinary connectivity and unplanned usage.

This is a hard ceiling, not a target. Do not spend the reserve.

## Download controls

1. **No model-weight downloads by default.** Continue repository work, metadata inspection, source/license checks, manifest generation, compatibility preparation, and evaluation design without fetching full checkpoints.
2. **No download may start unless its expected transfer size is known** from a pinned repository revision and selected file layout. Do not use repository-wide totals when they include duplicate formats, alternative quantizations, or parallel weight layouts.
3. **Count actual network transfer, not just nominal file size.** Include model shards, tokenizer/config files, dependencies, retries, partial transfers, and any other assets downloaded for the run.
4. **Cumulative transfer must remain at or below 20 GB.** Before each transfer, reserve enough headroom for overhead and retries. If the projected cumulative transfer could exceed 20 GB, do not start it.
5. **No automatic or background model downloads.** Any workflow or script that fetches model weights must be explicitly selected for the approved run. Do not launch broad teacher-panel jobs or full-snapshot jobs under this budget.
6. **Prefer the smallest useful artifact.** Use metadata-only requests first; if a real inference test is later approved, select one small, relevant model and a single quantized checkpoint where supported. Verify the exact file list and total before downloading.
7. **Stop safely.** If transfer accounting is unavailable, unexpected shards appear, retries grow, or the remaining budget cannot be established, stop before downloading further data.
8. **No budget increase by inference.** The separate bonus-data balance is not included in this 25 GB authorization. Do not assume bonus data is eligible for model downloads or increase the ceiling based on it.

## Approval gate for any model download

Before a download, record all of the following in the run manifest:

- candidate ID, source repository, and immutable revision;
- exact files and selected format/quantization;
- expected transfer size, including required tokenizer/config assets;
- cumulative transfer already used under this budget;
- projected total after the run and protected reserve;
- execution location (local device, mobile connection, or hosted runner);
- explicit approval for that specific download.

If any field is unknown, the download remains blocked.

## Execution-location distinction

GitHub-hosted Actions jobs download assets using the hosted runner's network, not the user's phone/mobile-data connection. They may still consume CI time and hosted-runner resources. Local downloads use the user's connection and must obey the 20 GB ceiling. Never describe a hosted-runner transfer as mobile-data usage, or assume a local transfer is free.

The repository currently contains inference workflows that fetch model checkpoints when triggered by matching evaluation changes. Avoid triggering those workflows while performing documentation-only or metadata-only work. Any future workflow change that can initiate weight downloads must preserve an explicit, controlled run gate.

## Current permitted work

- GitHub documentation and code changes that do not trigger model downloads;
- Hugging Face repository metadata, pinned revision, license, and file-inventory checks;
- compatibility and evaluation preparation that does not fetch weights;
- static tests that do not invoke model-loading or snapshot-download paths.

**Current model-weight download authorization: 0 GB.** The 20 GB ceiling is available only for a later, individually approved, measured download; it is not blanket permission to consume the full amount.
