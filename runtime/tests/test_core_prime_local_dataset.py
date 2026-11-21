"""Synthetic split-tool tests."""
import importlib.util,json,tempfile
from pathlib import Path
S=Path(__file__).resolve().parents[2]/"scripts"/"core_prime_local_dataset.py"
sp=importlib.util.spec_from_file_location("splitter",S);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def test_audit_duplicate_ids():
 with tempfile.TemporaryDirectory() as t:
  p=Path(t)/"d.jsonl";p.write_text('{"id":"a"}\n{"id":"a"}\n')
  assert any("duplicate id" in x for x in m.audit(p)["errors"])
def test_split_deterministic_and_disjoint():
 rows=[{"id":str(i),"text":"x"} for i in range(100)];key=b"k"*32
 x=m.split(rows,key,.2,.1);y=m.split(rows,key,.2,.1)
 assert x==y
 ids=[{r["id"] for r in x[k]} for k in x]
 assert not(ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2])
 assert sum(map(len,x.values()))==len(rows)
def test_audit_valid():
 with tempfile.TemporaryDirectory() as t:
  p=Path(t)/"d.jsonl";p.write_text('{"id":"a","text":"hello"}\n')
  assert m.audit(p)["errors"]==[]
