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
  self.assertEqual(delegation_targets(self.registry,"core-prima",available_ids=["core-code","core-research","core-creative"]),["core-code","core-research"])
 def test_unknown_delegate_rejected(self):
  bad=json.loads(json.dumps(self.registry));bad["models"][0]["delegates_to"]=["missing"]
  with self.assertRaises(RegistryError):validate_registry(bad)
 def test_duplicate_ids_rejected(self):
  bad=json.loads(json.dumps(self.registry));bad["models"].append(bad["models"][0])
  with self.assertRaises(RegistryError):validate_registry(bad)
 def test_capability_route_requires_full_set(self):
  self.assertEqual(route(self.registry,["testing","code_review"],available_ids=["core-code"]),[])
if __name__=="__main__": unittest.main()
