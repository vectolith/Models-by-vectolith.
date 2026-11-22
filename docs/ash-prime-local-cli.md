# ASH PRIME local CLI

This CLI is a **local checkpoint runner**, not a claim that trained ASH PRIME weights are currently available.

Install the runtime from the repository's runtime directory:

```powershell
cd runtime
python -m pip install -e .
python -m pip install -e ".[training]"
```

Launch against an existing local checkpoint (no model download is performed):

```powershell
ash-prime --checkpoint "C:\\path\\to\\checkpoint"
```

Single-prompt mode:

```powershell
ash-prime --checkpoint "C:\\path\\to\\checkpoint" --prompt "Explain what you can do."
```

Options include `--max-new-tokens` (default 512) and `--max-context-tokens` (default 4096). The runner trims older conversation items to fit the input budget while retaining the system prompt and newest request. For dispatched models it places inputs at the input-embedding device when available.

The loader uses local-only Transformers loading and does not enable remote model code. It requires a valid Transformers-compatible checkpoint directory and suitable local hardware/dependencies. It cannot run the experiment's student before student weights exist.

Commands in interactive mode: `/reset` clears chat history; `/exit` or `/quit` exits.
