.PHONY: install test selfcheck audit runtime-tests evaluation-tests

install:
	python -m pip install -e ./runtime

test: runtime-tests evaluation-tests audit

runtime-tests:
	python -m unittest discover -s runtime/tests -v

evaluation-tests:
	python -m unittest discover -s evaluation/tests -v

audit:
	python tools/repo_audit.py

selfcheck:
	python -m vectolith_runtime.cli selfcheck
