# Student model benchmark evidence

Record only real benchmark runs; fixture data in tests is synthetic. This validator checks the completeness and structure of candidate records and blocks nonzero declared cost. It does not authenticate records or verify the hardware, licenses, benchmark, model revision, quality or free quota.

Candidate fields include exact revision/tokenizer, license evidence hash, benchmark dataset hash, hardware/runtime, peak memory, throughput, quality result and method, reviewer/time, artifact hash, and cost. Keep source/license documents and raw benchmark outputs in controlled evidence storage. Run `python scripts/core_prime_student_evidence.py candidates.json`.

Zero budget is strict: `cost_usd` must be exactly 0. The validator does not permit paid services or compute and cannot establish actual free-tier availability. No model runs are initiated by this utility.
