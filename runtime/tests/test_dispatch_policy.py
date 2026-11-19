import unittest
from vectolith_runtime.registry import ModelLifecycle, ModelManifest, ModelRegistry
from vectolith_runtime.dispatch_policy import DispatchRequirements, select_model

def make(mid, state=ModelLifecycle.RELEASED, caps=frozenset({"coding"})):
    return ModelManifest(mid,mid,"1","coding specialist",caps,lifecycle=state)

class DispatchPolicyTests(unittest.TestCase):
    def test_selects_released_qualified_available_only(self):
        r=ModelRegistry()
        r.register(make("dev",ModelLifecycle.DEVELOPMENT))
        r.register(make("unqualified"))
        r.register(make("qualified"))
        d=select_model(r,DispatchRequirements(frozenset({"coding"})),qualified=lambda m:m.model_id=="qualified")
        self.assertEqual(d.selected.model_id,"qualified")
        self.assertIn(("dev","not_released"),d.rejected)
        self.assertIn(("unqualified","qualification_missing_or_failed"),d.rejected)

    def test_fails_closed_without_qualified_candidates(self):
        r=ModelRegistry(); r.register(make("a"))
        d=select_model(r,DispatchRequirements(frozenset({"coding"})),qualified=lambda _:False)
        self.assertIsNone(d.selected)
        self.assertEqual(d.reason,"no_eligible_model")

    def test_availability_filter(self):
        r=ModelRegistry(); r.register(make("a"))
        d=select_model(r,DispatchRequirements(frozenset({"coding"})),qualified=lambda _:True,available=lambda _:False)
        self.assertIsNone(d.selected)
        self.assertIn(("a","unavailable"),d.rejected)

    def test_missing_capability_not_candidate(self):
        r=ModelRegistry(); r.register(make("a"))
        d=select_model(r,DispatchRequirements(frozenset({"vision"})),qualified=lambda _:True)
        self.assertIsNone(d.selected)
        self.assertEqual(d.candidates,())

if __name__=="__main__": unittest.main()
