# ASH PRIME fail-closed preflight

Run `python scripts/ash_prime_preflight.py /path/to/readiness-manifest.json` before any training launch.

The readiness manifest is kept with its evidence in a controlled location. Each required gate must be explicitly `verified`, have a reviewer and timestamp, and cite one or more artifacts by relative path and SHA-256. Paths must remain inside the manifest directory. All eight gates are required; authorization must explicitly be true and include an authorization ID. The template is intentionally pending and blocks.

This script checks presence, local artifact integrity and structure. It cannot authenticate reviewers or independently establish rights, legal review, grading quality, holdout custody, provider quota, or authorization. It does not run training. The launch process must independently enforce this preflight and must not permit bypass flags.
