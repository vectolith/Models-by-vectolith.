import json, unittest
from pathlib import Path
from models.runtime.capability_registry import validate_registry,route,delegation_targets,RegistryError

REG=Path(__file__).parents[2]/"registry"/"registry.json"

class RegistryTests(unittest.TestCase):
 def setUp(self): self.registry=json.loads(REG.read_text())
 def test_registry_validates(self): validate_registry(self.registry)
 def test_route_uses_explicit_availability(self):
  result=route(self.registry,["code_review"],available_ids=["core-code"])
  self.assertEqual([x["id"] for x in result],["core-code"])
 def test_no_available_model_is_not_assumed(self):
  self.assertEqual(route(self.registry,["reasoning"]),[])
 def test_delegate_allowlist(self):
  self.assertEqual(delegation_targets(self.registry,"fyr-prima",available_ids=["core-code","core-research","core-creative"]),["core-code","core-research"])
 def test_unknown_delegate_rejected(self):
  bad=json.loads(json.dumps(self.registry));bad["models"][0]["delegates_to"]=["missing"]
  with self.assertRaises(RegistryError):validate_registry(bad)
 def test_duplicate_ids_rejected(self):
  bad=json.loads(json.dumps(self.registry));bad["models"].append(bad["models"][0])
  with self.assertRaises(RegistryError):validate_registry(bad)
 def test_capability_route_requires_full_set(self):
  self.assertEqual(route(self.registry,["testing","code_review","deployment_verification"],available_ids=["core-code"]),[])
 def test_prime_capability_contract(self):
  prime=next(m for m in self.registry["models"] if m["id"]=="ash-prime")
  required={"task_intake","requirements_elicitation","multi_step_planning","adaptive_routing","result_integration","verification"}
  self.assertTrue(required.issubset(set(prime["capabilities"])))
  self.assertTrue(prime["profile"]["workflow"])
 def test_prima_capability_contract(self):
  prima=next(m for m in self.registry["models"] if m["id"]=="fyr-prima")
  required={"repository_inspection","code_generation","debugging","test_execution","ci_diagnosis","reproducibility","engineering_evidence_capture"}
  self.assertTrue(required.issubset(set(prima["capabilities"])))
  self.assertTrue(prima["profile"]["workflow"])
 def test_orchestrator_delegation_allowlists_are_defined(self):
  for model_id in ("ash-prime","fyr-prima"):
   model=next(m for m in self.registry["models"] if m["id"]==model_id)
   self.assertTrue(model["delegates_to"])
   self.assertTrue(model["limits"])
if __name__=="__main__": unittest.main()
