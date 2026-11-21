"""Synthetic tests for rights-evidence validator; no actual rights claimed."""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
S=Path(__file__).resolve().parents[2]/"scripts"/"core_prime_rights_audit.py"
sp=importlib.util.spec_from_file_location("rights",S);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def setup(root):
 f=root/"permission.txt";f.write_text("synthetic permission evidence fixture")
 h=hashlib.sha256(f.read_bytes()).hexdigest()
 return {"schema_version":"teacher-rights-evidence/1.0","sources":[{"source_id":"fixture","provider":"test","model_name":"fixture","revision":"rev1","license_id":"TEST","scope_description":"synthetic","reviewer":"independent","rights_holder":"provider","reviewed_at":"2026-01-01","permissions":{"training_use":True,"output_use":True,"retention_use":True},"evidence":{"path":"permission.txt","sha256":h}}]}
def write(root,d):
 p=root/"ledger.json";p.write_text(json.dumps(d));return p
def test_complete_synthetic_structure():
 with tempfile.TemporaryDirectory() as t:assert m.validate(write(Path(t),setup(Path(t))))==[]
def test_permission_absent_blocks():
 with tempfile.TemporaryDirectory() as t:
  d=setup(Path(t));d["sources"][0]["permissions"]["training_use"]=False
  assert any("not explicitly verified" in x for x in m.validate(write(Path(t),d)))
def test_digest_tamper_blocks():
 with tempfile.TemporaryDirectory() as t:
  d=setup(Path(t));d["sources"][0]["evidence"]["sha256"]="0"*64
  assert any("digest mismatch" in x for x in m.validate(write(Path(t),d)))
def test_path_escape_blocks():
 with tempfile.TemporaryDirectory() as t:
  d=setup(Path(t));d["sources"][0]["evidence"]["path"]="../escape"
  assert any("escapes" in x for x in m.validate(write(Path(t),d)))
def test_reviewer_conflict_blocks():
 with tempfile.TemporaryDirectory() as t:
  d=setup(Path(t));d["sources"][0]["reviewer"]=d["sources"][0]["rights_holder"]
  assert any("reviewer cannot" in x for x in m.validate(write(Path(t),d)))
