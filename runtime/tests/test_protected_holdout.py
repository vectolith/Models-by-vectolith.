import copy, json, tempfile, unittest
from pathlib import Path

from vectolith_runtime import protected_holdout as ph

SHA64 = 'a' * 64

def deployment():
    return {
        'schema_version': ph.DEPLOYMENT_SCHEMA,
        'dataset_version': 'holdout-2026-11',
        'dataset_sha256': SHA64,
        'case_count': 4,
        'minimum_required_pass_rate': 0.8,
        'custody': {
            'storage_uri': 'vault://restricted/holdout',
            'access_boundary': 'dedicated_vault',
            'encryption_at_rest': True,
            'key_custody_separate': True,
            'custodian_id': 'custodian-a',
            'evaluator_operator_id': 'evaluator-b',
        },
        'execution': {
            'evaluator_service_id': 'svc-eval',
            'deployment_image_sha256': 'b' * 64,
            'pull_request_code_denied': True,
            'candidate_network_egress_denied': True,
            'dataset_mount_read_only': True,
            'result_channel_separated': True,
        },
        'audit': {
            'access_log_sha256': 'c' * 64,
            'leakage_audit_sha256': 'd' * 64,
            'provenance_report_sha256': 'e' * 64,
            'public_fixture_overlap_checked': True,
            'unauthorized_access_count': 0,
            'reviewed_by': 'reviewer-c',
        },
    }

def report_for(dep, **overrides):
    report = {
        'schema_version': ph.RESULT_SCHEMA,
        'deployment_manifest_sha256': ph.canonical_digest(dep),
        'candidate_id': 'cand-1',
        'candidate_revision': 'f' * 40,
        'evaluator_id': 'evaluator-b',
        'evaluator_image_sha256': 'b' * 64,
        'case_count': 4,
        'verified_pass_count': 4,
        'verified_fail_count': 0,
        'unscored_count': 0,
        'pass_rate': 1.0,
        'minimum_required_pass_rate': 0.8,
        'status': 'passed',
        'evaluation_suite_version': '1.0',
        'evaluated_at': '2026-11-20T00:00:00Z',
        'evaluator_run_id': 'run-1',
    }
    report.update(overrides)
    return report

class DeploymentTests(unittest.TestCase):
    def test_valid_manifest_has_no_errors(self):
        self.assertEqual(ph.validate_deployment_manifest(deployment()), [])

    def test_wrong_schema_short_circuits(self):
        self.assertEqual(ph.validate_deployment_manifest({'schema_version': 'x'}), ['unsupported_or_missing_schema'])
        self.assertEqual(ph.validate_deployment_manifest(None), ['unsupported_or_missing_schema'])

    def test_each_missing_control_is_reported(self):
        cases = [
            (('dataset_version', ''), 'dataset_version_missing'),
            (('dataset_sha256', 'short'), 'dataset_digest_invalid'),
            (('case_count', 0), 'case_count_invalid'),
            (('case_count', True), 'case_count_invalid'),
        ]
        for (key, value), code in cases:
            mutated = deployment()
            mutated[key] = value
            self.assertIn(code, ph.validate_deployment_manifest(mutated))

    def test_custody_rules(self):
        mutations = [
            (('storage_uri', 'https://public'), 'restricted_storage_uri_required'),
            (('access_boundary', 'shared_project'), 'separate_custody_boundary_required'),
            (('encryption_at_rest', False), 'independent_encryption_and_key_custody_required'),
            (('key_custody_separate', False), 'independent_encryption_and_key_custody_required'),
            (('custodian_id', '  '), 'custodian_identity_missing'),
            (('evaluator_operator_id', 'custodian-a'), 'independent_evaluator_operator_required'),
        ]
        for (key, value), code in mutations:
            mutated = deployment()
            mutated['custody'][key] = value
            self.assertIn(code, ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        del mutated['custody']
        self.assertIn('custody_missing', ph.validate_deployment_manifest(mutated))

    def test_execution_rules(self):
        for field in ('pull_request_code_denied', 'candidate_network_egress_denied',
                      'dataset_mount_read_only', 'result_channel_separated'):
            mutated = deployment()
            mutated['execution'][field] = False
            self.assertIn('execution_control_missing:' + field, ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        mutated['execution']['deployment_image_sha256'] = 'nope'
        self.assertIn('evaluator_deployment_digest_invalid', ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        del mutated['execution']['evaluator_service_id']
        self.assertIn('dedicated_evaluator_service_required', ph.validate_deployment_manifest(mutated))

    def test_audit_rules(self):
        mutated = deployment()
        mutated['audit']['unauthorized_access_count'] = 2
        self.assertIn('unauthorized_access_detected_or_unreported', ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        mutated['audit']['reviewed_by'] = 'custodian-a'
        self.assertIn('independent_audit_reviewer_required', ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        mutated['audit']['public_fixture_overlap_checked'] = False
        self.assertIn('public_fixture_overlap_audit_required', ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        mutated['audit']['leakage_audit_sha256'] = 'x'
        self.assertIn('audit_digest_invalid:leakage_audit_sha256', ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        mutated['audit']['unauthorized_access_count'] = False
        self.assertIn('unauthorized_access_detected_or_unreported', ph.validate_deployment_manifest(mutated))
        mutated = deployment()
        mutated['audit']['reviewed_by'] = 7
        self.assertIn('independent_audit_reviewer_required', ph.validate_deployment_manifest(mutated))

class EvaluationReportTests(unittest.TestCase):
    def setUp(self):
        self.dep = deployment()

    def test_valid_report_has_no_errors(self):
        self.assertEqual(ph.validate_evaluation_report(report_for(self.dep), self.dep, 'cand-1', 'f' * 40), [])

    def test_binding_and_identity_errors(self):
        checks = [
            ({'deployment_manifest_sha256': 'f' * 64}, 'evaluation_not_bound_to_protected_deployment'),
            ({'candidate_id': 'other'}, 'evaluation_candidate_identity_or_revision_mismatch'),
            ({'candidate_revision': 'e' * 40}, 'evaluation_candidate_identity_or_revision_mismatch'),
            ({'candidate_revision': 'rev-2'}, 'evaluation_report_candidate_revision_invalid'),
            ({'evaluator_id': 'custodian-a'}, 'evaluation_evaluator_identity_mismatch'),
            ({'evaluator_image_sha256': 'c' * 64}, 'evaluation_evaluator_image_mismatch'),
            ({'case_count': 5}, 'evaluation_case_count_mismatch'),
            ({'case_count': True}, 'evaluation_case_count_invalid'),
            ({'status': 'attempted'}, 'holdout_evaluation_not_passed'),
            ({'evaluator_run_id': ''}, 'evaluation_provenance_missing:evaluator_run_id'),
        ]
        for override, code in checks:
            errors = ph.validate_evaluation_report(report_for(self.dep, **override), self.dep, 'cand-1', 'f' * 40)
            self.assertIn(code, errors)

    def test_case_count_accounting_errors(self):
        errors = ph.validate_evaluation_report(report_for(self.dep, unscored_count=1, verified_pass_count=2, pass_rate=0.5), self.dep, 'cand-1', 'f' * 40)
        self.assertIn('evaluation_contains_unscored_cases', errors)
        self.assertIn('evaluation_case_counts_do_not_sum', errors)
        errors = ph.validate_evaluation_report(report_for(self.dep, verified_pass_count=1, verified_fail_count=1), self.dep, 'cand-1', 'f' * 40)
        self.assertIn('evaluation_case_counts_do_not_sum', errors)
        errors = ph.validate_evaluation_report(report_for(self.dep, verified_pass_count=-1), self.dep, 'cand-1', 'f' * 40)
        self.assertIn('evaluation_case_counts_invalid', errors)

    def test_threshold_and_pass_rate_errors(self):
        errors = ph.validate_evaluation_report(report_for(self.dep, pass_rate=0.25, verified_pass_count=1, verified_fail_count=3), self.dep, 'cand-1', 'f' * 40)
        self.assertIn('evaluation_did_not_meet_or_bind_declared_threshold', errors)
        errors = ph.validate_evaluation_report(report_for(self.dep, minimum_required_pass_rate=0.7), self.dep, 'cand-1', 'f' * 40)
        self.assertIn('evaluation_did_not_meet_or_bind_declared_threshold', errors)
        errors = ph.validate_evaluation_report(report_for(self.dep, minimum_required_pass_rate=0.0, pass_rate=0.0, verified_pass_count=0, verified_fail_count=4), self.dep, 'cand-1', 'f' * 40)
        self.assertIn('evaluation_did_not_meet_or_bind_declared_threshold', errors)
        errors = ph.validate_evaluation_report(report_for(self.dep, pass_rate=0.95), self.dep, 'cand-1', 'f' * 40)
        self.assertIn('evaluation_pass_rate_does_not_match_case_counts', errors)

class FileValidationTests(unittest.TestCase):
    def test_round_trip_and_digest(self):
        dep = deployment()
        with tempfile.TemporaryDirectory() as tmp:
            dep_path = Path(tmp, 'deployment.json')
            dep_path.write_text(json.dumps(dep))
            manifest, digest = ph.validate_deployment_file(dep_path)
            self.assertEqual(manifest, dep)
            self.assertEqual(digest, ph.canonical_digest(dep))
            result_path = Path(tmp, 'cand-1.json')
            result_path.write_text(json.dumps(report_for(dep)))
            report, report_digest = ph.validate_candidate_result(result_path, manifest, digest, 'cand-1', 'f' * 40)
            self.assertEqual(report['candidate_id'], 'cand-1')
            self.assertEqual(len(report_digest), 64)
    def test_invalid_deployment_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'deployment.json')
            bad = deployment()
            bad['case_count'] = 0
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError) as ctx:
                ph.validate_deployment_file(path)
            self.assertIn('case_count_invalid', str(ctx.exception))

    def test_unsafe_candidate_id_invalid_revision_and_missing_file(self):
        dep = deployment()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ph.validate_candidate_result(Path(tmp, 'x.json'), dep, ph.canonical_digest(dep), '../etc/passwd', 'f' * 40)
            with self.assertRaises(ValueError):
                ph.validate_candidate_result(Path(tmp, 'x.json'), dep, ph.canonical_digest(dep), 'bad id', 'f' * 40)
            with self.assertRaises(ValueError):
                ph.validate_candidate_result(Path(tmp, 'x.json'), dep, ph.canonical_digest(dep), 'cand-1', 'rev-1')
            with self.assertRaises(FileNotFoundError):
                ph.validate_candidate_result(Path(tmp, 'missing.json'), dep, ph.canonical_digest(dep), 'cand-1', 'f' * 40)

    def test_result_digest_mismatch_raises(self):
        dep = deployment()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'cand-1.json')
            path.write_text(json.dumps(report_for(dep, deployment_manifest_sha256='f' * 64)))
            with self.assertRaises(ValueError) as ctx:
                ph.validate_candidate_result(path, dep, ph.canonical_digest(dep), 'cand-1', 'f' * 40)
            self.assertIn('holdout_result_deployment_digest_mismatch', str(ctx.exception))

if __name__ == '__main__':
    unittest.main()