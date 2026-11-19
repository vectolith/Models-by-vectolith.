"""Tests for the published model manifest schema."""
import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator

class ManifestSchemaTests(unittest.TestCase):
    def setUp(self):
        p=Path(__file__).parents[1] / "vectolith_runtime" / "schemas" / "model-manifest-v1.schema.json"
        self.validator=Draft202012Validator(json.loads(p.read_text()))

    def valid(self):
        return {"schema_version":"1.0.0","model_id":"sample-model","version":"1.0",
            "specialization":"example","capabilities":["coding.review"],
            "modalities":{"input":["text"],"output":["text"]},
            "lifecycle_state":"evaluation","identity_contract_version":"1.0",
            "safety_baseline":"vectolith-safety-baseline"}

    def test_schema_itself_is_valid(self):
        Draft202012Validator.check_schema(self.validator.schema)

    def test_valid_manifest(self):
        self.assertTrue(self.validator.is_valid(self.valid()))

    def test_required_field(self):
        v=self.valid(); del v["capabilities"]
        self.assertFalse(self.validator.is_valid(v))

    def test_empty_capability_list(self):
        v=self.valid(); v["capabilities"]=[]
        self.assertFalse(self.validator.is_valid(v))

    def test_unknown_lifecycle(self):
        v=self.valid(); v["lifecycle_state"]="production"
        self.assertFalse(self.validator.is_valid(v))

    def test_unknown_field(self):
        v=self.valid(); v["extra"]=True
        self.assertFalse(self.validator.is_valid(v))
