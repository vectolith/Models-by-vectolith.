from __future__ import annotations
import hashlib, hmac, json, unittest
from evaluation.criterion_verifiers import verify_decimal_answer, verify_exact_answer, verify_fact_claim_review, verify_sandbox_attestation

class CriterionVerifierTests(unittest.TestCase):
    def test_exact_answer(self):
        self.assertEqual(verify_exact_answer(actual="42", expected="42", case_id="m1", reference_id="fixture://m1")["status"], "verified_pass")
        self.assertEqual(verify_exact_answer(actual="42", expected="41", case_id="m1", reference_id="fixture://m1")["status"], "verified_fail")
    def test_decimal_tolerance_and_strict_parse(self):
        result = verify_decimal_answer(actual="3.1415", expected="3.14159", case_id="pi", reference_id="fixture://pi", absolute_tolerance="0.0001")
        self.assertEqual(result["status"], "verified_pass")
        with self.assertRaisesRegex(ValueError, "plain decimal"):
            verify_decimal_answer(actual="The answer is 3.14", expected="3.14", case_id="pi", reference_id="fixture://pi")
    def test_signed_sandbox_attestation(self):
        key=b"k"*32
        body={"schema_version":"vectolith-code-sandbox-attestation/1.0","case_id":"code-1","runner_id":"runner-1",
              "output_sha256":"a"*64,"report_sha256":"b"*64,"isolation_profile":"untrusted-code-v1",
              "network_egress_disabled":True,"filesystem_isolated":True,"timeout_enforced":True,
              "memory_limit_enforced":True,"process_limit_enforced":True,"exit_code":0,"tests_passed":5,"tests_failed":0}
        body["signature"]=hmac.new(key,json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode(),hashlib.sha256).hexdigest()
        result=verify_sandbox_attestation(attestation=body,signing_key=key,expected_case_id="code-1",
            expected_output_sha256="a"*64,expected_runner_id="runner-1")
        self.assertEqual(result["status"],"verified_pass")
        body["network_egress_disabled"]=False
        with self.assertRaisesRegex(ValueError,"signature is invalid"):
            verify_sandbox_attestation(attestation=body,signing_key=key,expected_case_id="code-1",
                expected_output_sha256="a"*64,expected_runner_id="runner-1")
    def test_fact_review_requires_independent_adjudicator(self):
        output="a"*64
        claims=[{"claim":"A claim","source_uri":"https://example.org/source","source_sha256":"b"*64,"review_status":"supported"}]
        review={"case_id":"fact-1","output_sha256":output,"reviewer_id":"r1","adjudicator_id":"r2","status":"adjudicated"}
        self.assertEqual(verify_fact_claim_review(case_id="fact-1",output_sha256=output,claims=claims,
            review_record=review,review_record_sha256="c"*64)["status"],"verified_pass")
        review["adjudicator_id"]="r1"
        with self.assertRaisesRegex(ValueError,"independent"):
            verify_fact_claim_review(case_id="fact-1",output_sha256=output,claims=claims,
                review_record=review,review_record_sha256="c"*64)
if __name__=="__main__": unittest.main()
