# Teacher rights evidence audit

This ledger is a **fail-closed evidence inventory**, not a legal opinion or permission grant. Verify written rights with the actual rights holder and an independent reviewer. Record exact model revision and scope, not generic permission statements.

Each source requires:
- Provider, model, immutable revision, license identifier, scope description.
- Explicit flags for training use, output use and retention use.
- Independent reviewer, review timestamp, rights-holder identity.
- A controlled evidence file and SHA-256 digest.

Example structure (fixture only):
```json
{"schema_version":"teacher-rights-evidence/1.0","sources":[{"source_id":"source-id","provider":"provider","model_name":"model","revision":"revision","license_id":"license","scope_description":"exact scope","reviewer":"reviewer-id","rights_holder":"holder-id","reviewed_at":"ISO-8601","permissions":{"training_use":false,"output_use":false,"retention_use":false},"evidence":{"path":"permission-record.txt","sha256":"64-hex"}}]}
```
Run `python scripts/core_prime_rights_audit.py rights-ledger.json`. Evidence files must reside inside the ledger's directory and digest-match. Missing or false flags block. Do not place confidential agreements, secrets, personal information, or copyrighted corpus content in the public repository. Keep the ledger and evidence in a controlled local/private location. Passing checks establishes only structure and integrity; it does not authenticate legal authority, interpret licenses, or replace independent legal review.
