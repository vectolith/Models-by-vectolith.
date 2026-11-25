.PHONY: install test selfcheck audit runtime-tests evaluation-tests kaggle-kernel-tests

install:
	python -m pip install -e ./runtime

test: runtime-tests evaluation-tests kaggle-kernel-tests audit

runtime-tests:
	python -m unittest discover -s runtime/tests -v

evaluation-tests:
	python -m unittest discover -s evaluation/tests -v

kaggle-kernel-tests:
	python -m py_compile training/kaggle/kernel.py training/kaggle/test_kernel_cpu.py training/build_run42_corpus.py
	python -m unittest training/kaggle/test_kernel_cpu.py -v
	python -m unittest training.tests.test_build_run42_corpus -v

audit:
	python tools/repo_audit.py

selfcheck:
	python -m vectolith_runtime.cli selfcheck
