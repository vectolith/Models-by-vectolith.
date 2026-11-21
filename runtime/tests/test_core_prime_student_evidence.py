import importlib.util,math
from pathlib import Path
S=Path(__file__).resolve().parents[2]/"scripts"/"core_prime_student_evidence.py"
sp=importlib.util.spec_from_file_location("student",S);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def record():
 return {"model_id":"fixture","revision":"r1","license_id":"TEST","license_evidence_sha256":"a"*64,"tokenizer_revision":"tok1","benchmark_dataset_sha256":"b"*64,"hardware":"synthetic fixture","runtime":"synthetic fixture","peak_memory_mb":1,"tokens_per_second":1,"quality_score":1,"quality_method":"fixture","reviewer":"fixture","timestamp":"2026-01-01","artifact_sha256":"c"*64,"cost_usd":0}
def test_valid_structure():assert m.validate({"candidates":[record()]})==[]
def test_paid_cost_blocks():
 r=record();r["cost_usd"]=0.01
 assert any("zero-budget" in e for e in m.validate({"candidates":[r]}))
def test_digest_invalid_blocks():
 r=record();r["artifact_sha256"]="bad"
 assert any("invalid artifact_sha256" in e for e in m.validate({"candidates":[r]}))
def test_duplicate_model_blocks():
 r=record()
 assert any("duplicate model_id" in e for e in m.validate({"candidates":[r,r]}))
def test_nan_infinity_block():
 for field,value in (("quality_score",math.nan),("cost_usd",math.inf),("peak_memory_mb",math.nan),("tokens_per_second",math.inf)):
  r=record();r[field]=value
  assert m.validate({"candidates":[r]})
def test_empty_identifiers_block():
 r=record();r["model_id"]=" "
 assert any("model_id" in e for e in m.validate({"candidates":[r]}))
