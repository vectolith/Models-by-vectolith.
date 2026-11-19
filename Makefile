.PHONY: install test selfcheck runtime-tests evaluation-tests

install:
	python -m pip install -e ./runtime

test: runtime-tests evaluation-tests

runtime-tests:
	python -m unittest discover -s runtime/tests -v

evaluation-tests:
	python -m unittest discover -s evaluation/tests -v

selfcheck:
	python -m vectolith_runtime.cli selfcheck
