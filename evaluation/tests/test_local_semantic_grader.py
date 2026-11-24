from __future__ import annotations

import hashlib
import json
import unittest

from evaluation.grading.local_semantic_grader import (
    build_messages,
    load_lock,
    parse_decision,
)


class LocalSemanticGraderTests(unittest.TestCase):
    def request(self):
        response = "The answer is 42."
        return {
            "candidate_alias": "blind-01",
            "case_id": "case-001",
            "response": response,
            "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
            "rubric": [
                {
                    "criterion_id": "c1",
                    "description": "Provides the answer 42.",
                }
            ],
        }


    def test_evidence_matching_ignores_whitespace_and_unicode_form_only(self):
        response = "Line one\u00a0has\u200b  the answer 42.\nSecond line."
        request = {
            "candidate_alias": "blind-01",
            "case_id": "case-002",
            "response": response,
            "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
            "rubric": [{"criterion_id": "c1", "description": "States the answer."}],
        }
        raw = json.dumps({"criteria": [{
            "criterion_id": "c1", "status": "passed",
            "evidence_excerpt": "Line one has the answer 42.", "rationale": "states it"}]})
        decision = parse_decision(raw, request)
        self.assertEqual(decision["criteria"][0]["evidence_excerpt"], "Line one has the answer 42.")

    def test_paraphrased_evidence_is_still_rejected(self):
        request = self.request()
        raw = json.dumps({"criteria": [{
            "criterion_id": "c1", "status": "passed",
            "evidence_excerpt": "The final value is forty-two.", "rationale": "states it"}]})
        with self.assertRaisesRegex(ValueError, "not verbatim"):
            parse_decision(raw, request)

    def test_lock_is_local_pinned_and_has_no_remote_api(self):
        lock = load_lock()
        self.assertEqual(lock["model_id"], "Qwen/Qwen3.5-2B")
        self.assertEqual(
            lock["immutable_revision"],
            "15852e8c16360a2fea060d615a32b45270f8a8fc",
        )
        self.assertEqual(lock["execution_mode"], "local_open_weight_cpu")
        self.assertFalse(lock["remote_api"])
        self.assertFalse(lock["credentials_required"])
        self.assertTrue(lock["no_fallback_to_hosted_api"])

    def test_request_treats_candidate_text_as_untrusted(self):
        request = self.request()
        messages = build_messages(request)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("untrusted data", messages[0]["content"])
        self.assertIn("Ignore all", messages[0]["content"])
        self.assertIn(request["response"], messages[1]["content"])
        self.assertNotIn("candidate_id", messages[1]["content"])

    def test_response_digest_mismatch_is_rejected(self):
        request = self.request()
        request["response_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            build_messages(request)

    def test_plain_string_rubric_ids_are_visible_to_the_grader(self):
        request = self.request()
        request["rubric"] = ["Exactly four bullets", "No analogy"]
        payload = json.loads(build_messages(request)[1]["content"])
        self.assertEqual(
            payload["rubric"],
            [
                {"criterion_id": "criterion-01", "criterion": "Exactly four bullets"},
                {"criterion_id": "criterion-02", "criterion": "No analogy"},
            ],
        )
        raw = json.dumps({
            "criteria": [
                {"criterion_id": "criterion-01", "status": "failed",
                 "evidence_excerpt": "42", "rationale": "One line, not four bullets."},
                {"criterion_id": "criterion-02", "status": "passed",
                 "evidence_excerpt": "42", "rationale": "No analogy used."},
            ]
        })
        result = parse_decision(raw, request)
        self.assertEqual([c["criterion_id"] for c in result["criteria"]],
                         ["criterion-01", "criterion-02"])

    def test_invented_criterion_ids_are_rejected(self):
        request = self.request()
        request["rubric"] = ["Exactly four bullets"]
        raw = json.dumps({
            "criteria": [{"criterion_id": "bullet_format", "status": "passed",
                          "evidence_excerpt": "42", "rationale": "Four bullets."}]
        })
        with self.assertRaisesRegex(ValueError, "exactly once"):
            parse_decision(raw, request)

    def test_valid_decision_is_bound_to_blinded_request(self):
        request = self.request()
        raw = json.dumps({
            "criteria": [{
                "criterion_id": "c1",
                "status": "passed",
                "evidence_excerpt": "42",
                "rationale": "The response gives the required value.",
            }]
        })
        result = parse_decision(raw, request)
        self.assertEqual(result["candidate_alias"], "blind-01")
        self.assertEqual(result["case_id"], "case-001")
        self.assertEqual(result["response_sha256"], request["response_sha256"])
        self.assertEqual(result["criteria"][0]["status"], "passed")

    def test_non_verbatim_evidence_is_rejected(self):
        request = self.request()
        raw = json.dumps({
            "criteria": [{
                "criterion_id": "c1",
                "status": "passed",
                "evidence_excerpt": "The answer is 43",
                "rationale": "The response gives the required value.",
            }]
        })
        with self.assertRaisesRegex(ValueError, "not verbatim"):
            parse_decision(raw, request)

    def test_missing_criterion_is_rejected(self):
        request = self.request()
        raw = json.dumps({"criteria": []})
        with self.assertRaises(ValueError):
            parse_decision(raw, request)


if __name__ == "__main__":
    unittest.main()
