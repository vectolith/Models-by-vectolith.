import unittest

from vectolith_runtime.infrastructure import (
    AccessMode, ComputeRequest, ContributionClass, InfrastructureContribution,
    InfrastructureProvider, InfrastructureRegistry, MockComputeAdapter,
    ProviderState, QualificationState, qualification_blockers,
)


def approved_records():
    provider = InfrastructureProvider(
        "provider-a", "Provider A", "cloud",
        relationship_state=ProviderState.APPROVED,
        legal_review_ref="review:legal:1", security_review_ref="review:security:1",
    )
    contribution = InfrastructureContribution(
        "compute-a", "provider-a", ContributionClass.COMPUTE, "Mock capacity",
        "revision-1", "MIT", AccessMode.SELF_HOSTED,
        frozenset({"cpu", "memory", "gpu.mock"}),
        qualification_status=QualificationState.APPROVED,
        permitted_use=frozenset({"development"}),
        evidence_refs=("test:compatibility",),
        adapter_id="vectolith.mock-compute",
    )
    return provider, contribution


class InfrastructureRegistryTests(unittest.TestCase):
    def test_register_and_filter_contributions(self):
        provider, contribution = approved_records()
        registry = InfrastructureRegistry()
        registry.register_provider(provider)
        registry.register_contribution(contribution)
        self.assertEqual(registry.get_contribution("compute-a"), contribution)
        self.assertEqual(registry.list_contributions(approved_only=True), (contribution,))

    def test_unknown_provider_and_duplicate_ids_fail_closed(self):
        registry = InfrastructureRegistry()
        _, contribution = approved_records()
        with self.assertRaises(KeyError):
            registry.register_contribution(contribution)
        provider, _ = approved_records()
        registry.register_provider(provider)
        registry.register_provider(provider, replace=False) if False else None
        with self.assertRaises(ValueError):
            registry.register_provider(provider)
        registry.register_contribution(contribution)
        with self.assertRaises(ValueError):
            registry.register_contribution(contribution)

    def test_incomplete_provider_or_contribution_is_blocked(self):
        provider, contribution = approved_records()
        incomplete = InfrastructureProvider("provider-a", "Provider A", "cloud")
        blockers = qualification_blockers(incomplete, contribution)
        self.assertIn("provider relationship is not approved", blockers)
        self.assertIn("provider legal review evidence is missing", blockers)
        self.assertIn("provider security review evidence is missing", blockers)

    def test_hosted_resources_require_cost_and_data_review(self):
        provider, contribution = approved_records()
        hosted = InfrastructureContribution(
            "hosted", "provider-a", ContributionClass.COMPUTE, "Hosted GPU",
            "revision-2", "terms-v1", AccessMode.PROVIDER_HOSTED,
            frozenset({"cpu"}), qualification_status=QualificationState.APPROVED,
            permitted_use=frozenset({"training"}), evidence_refs=("review",),
        )
        blockers = qualification_blockers(provider, hosted)
        self.assertIn("verified price or quota evidence is missing", blockers)
        self.assertIn("data-handling review evidence is missing", blockers)

    def test_mock_adapter_preflight_and_lifecycle_are_offline(self):
        provider, contribution = approved_records()
        adapter = MockComputeAdapter()
        request = ComputeRequest("job-1", "compute-a", cpu_cores=2, memory_gb=4)
        self.assertEqual(adapter.preflight(request, contribution, provider), ())
        job = adapter.submit(request)
        self.assertEqual(job.state, "queued")
        self.assertIn("no resources were provisioned", job.detail)
        self.assertEqual(adapter.status("job-1"), job)
        self.assertEqual(adapter.cancel("job-1").state, "cancelled")

    def test_mock_adapter_refuses_unqualified_contribution(self):
        provider, contribution = approved_records()
        unapproved = InfrastructureProvider("provider-a", "Provider A", "cloud")
        blockers = MockComputeAdapter().preflight(
            ComputeRequest("job-2", "compute-a"), contribution, unapproved
        )
        self.assertTrue(blockers)
        self.assertIn("provider relationship is not approved", blockers)

    def test_invalid_resource_requests_are_rejected(self):
        with self.assertRaises(ValueError):
            ComputeRequest("job", "contribution", cpu_cores=0)


if __name__ == "__main__":
    unittest.main()
