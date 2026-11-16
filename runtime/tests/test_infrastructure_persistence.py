import tempfile
import unittest
from pathlib import Path
from vectolith_runtime import AccessMode, ContributionClass, InfrastructureContribution, InfrastructureProvider, ProviderState, QualificationState, SQLiteInfrastructureRegistry, validate_infrastructure_record
from vectolith_runtime.infrastructure_persistence import contribution_from_record, contribution_to_record, provider_from_record, provider_to_record

def records():
    p=InfrastructureProvider("provider-a","Provider A","cloud",ProviderState.APPROVED,("example.com",),"legal:1","security:1")
    c=InfrastructureContribution("compute-a","provider-a",ContributionClass.COMPUTE,"Mock compute","rev-1","MIT",AccessMode.SELF_HOSTED,frozenset({"cpu","memory"}),QualificationState.APPROVED,permitted_use=frozenset({"development"}),evidence_refs=("compatibility:1",),adapter_id="vectolith.mock-compute")
    return p,c

class InfrastructureSerializationTests(unittest.TestCase):
    def test_provider_round_trip(self):
        p,_=records(); self.assertEqual(provider_from_record(provider_to_record(p)),p)
    def test_contribution_round_trip(self):
        _,c=records(); self.assertEqual(contribution_from_record(contribution_to_record(c)),c)
    def test_schema_rejects_unknown_properties_and_missing_fields(self):
        p,_=records(); d=provider_to_record(p); d["secret_token"]="must-not-be-accepted"
        with self.assertRaisesRegex(ValueError,"additional properties"): validate_infrastructure_record("provider",d)
        with self.assertRaises(ValueError): validate_infrastructure_record("contribution",{"schema_version":"1.0"})

class SQLiteInfrastructureRegistryTests(unittest.TestCase):
    def test_records_survive_close_and_reopen(self):
        p,c=records()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"infra.sqlite3"; r=SQLiteInfrastructureRegistry(path); r.register_provider(p); r.register_contribution(c); r.close()
            reopened=SQLiteInfrastructureRegistry(path)
            self.assertEqual(reopened.get_provider(p.provider_id),p); self.assertEqual(reopened.get_contribution(c.contribution_id),c)
            self.assertEqual(reopened.list_contributions(approved_only=True),(c,)); reopened.close()
    def test_duplicate_requires_explicit_replace(self):
        p,_=records()
        with tempfile.TemporaryDirectory() as d:
            r=SQLiteInfrastructureRegistry(Path(d)/"db.sqlite3"); r.register_provider(p)
            with self.assertRaises(ValueError): r.register_provider(p)
            newer=InfrastructureProvider(p.provider_id,"Updated",p.provider_category,p.relationship_state,p.official_domains,p.legal_review_ref,p.security_review_ref)
            r.register_provider(newer,replace=True); self.assertEqual(r.get_provider(p.provider_id),newer); r.close()
    def test_unknown_provider_rejected_without_partial_write(self):
        _,c=records()
        with tempfile.TemporaryDirectory() as d:
            r=SQLiteInfrastructureRegistry(Path(d)/"db.sqlite3")
            with self.assertRaises(KeyError): r.register_contribution(c)
            self.assertEqual(r.list_contributions(),()); r.close()
    def test_secret_like_properties_rejected(self):
        p,_=records(); d=provider_to_record(p); d["api_key"]="sensitive"
        with self.assertRaises(ValueError): validate_infrastructure_record("provider",d)
