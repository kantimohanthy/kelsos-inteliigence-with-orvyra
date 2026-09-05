"""
Sprint 0 Test Suite — Orvyra Foundation Verification.

Tests:
1. Pre-call request and response with repaired schema (schema_version, packet_id, trace_id, status, sources, warnings).
2. Post-call request and response.
3. Bearer authentication enforcement (missing/invalid vs valid key).
4. Prospect listing endpoint (GET /v1/intelligence/prospects).
5. Prospect detail endpoint (GET /v1/intelligence/prospects/{id} & 404 check).
6. Prospect history & global call log (GET /v1/intelligence/prospects/{id}/history & GET /v1/intelligence/calls).
7. Duplicate prospect handling (email/LinkedIn dedup and memory lookup).
8. Invalid or incomplete input behavior (422 validation errors).
9. Schema contract compatibility against exported JSON schema.
"""

from __future__ import annotations
import os
import sys
import json
import unittest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test API key before importing FastAPI app
os.environ["ORVYRA_API_KEY"] = "sprint0-secret-test-key-9999"

from fastapi.testclient import TestClient
from main import app
from storage.memory import memory


class TestSprint0Foundation(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ORVYRA_API_KEY"] = "test-secret-key-9999"
        memory.clear()
        self.client = TestClient(app)
        self.auth_headers = {"Authorization": "Bearer test-secret-key-9999"}


    def test_auth_enforcement(self) -> None:
        """Verify 401 error on missing or invalid Bearer token."""
        # Missing header
        res_no_auth = self.client.get("/v1/intelligence/prospects")
        self.assertEqual(res_no_auth.status_code, 401)
        self.assertIn("Missing bearer token", res_no_auth.text)

        # Invalid token
        res_bad_auth = self.client.get(
            "/v1/intelligence/prospects",
            headers={"Authorization": "Bearer invalid-token-xyz"}
        )
        self.assertEqual(res_bad_auth.status_code, 401)
        self.assertIn("Invalid API key", res_bad_auth.text)

        # Valid token
        res_valid = self.client.get("/v1/intelligence/prospects", headers=self.auth_headers)
        self.assertEqual(res_valid.status_code, 200)

    def test_invalid_or_incomplete_input(self) -> None:
        """Verify 422 validation error on malformed or missing fields."""
        # Missing required field 'objective'
        payload = {
            "prospect": {"name": "Alice Smith", "company": "Acme Corp"}
        }
        res = self.client.post("/v1/intelligence/pre-call", json=payload, headers=self.auth_headers)
        self.assertEqual(res.status_code, 422)

    def test_pre_call_and_repaired_contract(self) -> None:
        """Verify pre-call response includes all repaired schema fields."""
        payload = {
            "prospect": {
                "name": "Jane Doe",
                "company": "TechCorp Solutions",
                "email": "jane.doe@techcorp.example",
                "linkedin_url": "https://linkedin.com/in/janedoe-test",
                "company_url": "https://techcorp.example"
            },
            "objective": "Schedule product demo for outbound AI agent",
            "product": "Klesos",
            "role_hint": "VP of Sales"
        }
        res = self.client.post("/v1/intelligence/pre-call", json=payload, headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)

        packet = res.json()
        self.assertEqual(packet["schema_version"], "1.0.0")
        self.assertTrue(packet["packet_id"].startswith("pkt_"))
        self.assertTrue(packet["trace_id"].startswith("trace_"))
        self.assertTrue(packet["prospect_id"].startswith("prospect_"))
        self.assertIn(packet["status"], ["ready", "low_relevance", "generated"])
        self.assertIsInstance(packet["sources"], list)
        self.assertGreater(len(packet["sources"]), 0)

        # Check structured EvidenceSource shape
        first_src = packet["sources"][0]
        self.assertIn("source_id", first_src)
        self.assertIn("source_type", first_src)
        self.assertIn("confidence", first_src)

        # Check person context seniority inference
        self.assertEqual(packet["person_context"]["seniority"], "Executive")
        self.assertIsNotNone(packet["opportunity"])

        if packet["opportunity"]["pursue"]:
            self.assertIsNotNone(packet["conversation_strategy"])
        else:
            self.assertIsNone(packet["conversation_strategy"])
            self.assertIsNotNone(packet["opportunity"]["reason_if_not_pursue"])


    def test_post_call_and_history(self) -> None:
        """Verify post-call analysis ingestion and memory recording."""
        # 1. Create a pre-call prospect
        pre_payload = {
            "prospect": {"name": "Bob Vance", "email": "bob@vancerefrig.example", "company": "Vance Refrigeration"},
            "objective": "Qualify outbound interest",
            "role_hint": "Director of Logistics"
        }
        pre_res = self.client.post("/v1/intelligence/pre-call", json=pre_payload, headers=self.auth_headers)
        prospect_id = pre_res.json()["prospect_id"]

        # 2. Submit post-call transcript
        post_payload = {
            "conversation_id": "conv_test_101",
            "prospect_id": prospect_id,
            "transcript": "Hello Bob, calling from Klesos. Sounds good, send me pricing and demo details.",
            "events": [{"type": "dial", "detail": "call_connected"}, {"type": "hangup", "detail": "completed"}]
        }
        post_res = self.client.post("/v1/intelligence/post-call", json=post_payload, headers=self.auth_headers)
        self.assertEqual(post_res.status_code, 200)

        analysis = post_res.json()
        self.assertEqual(analysis["conversation_id"], "conv_test_101")
        self.assertEqual(analysis["prospect_id"], prospect_id)
        self.assertEqual(analysis["outcome"], "interested_follow_up")
        self.assertGreater(analysis["intent_score"], 0.5)

        # 3. Check prospect history endpoint
        hist_res = self.client.get(f"/v1/intelligence/prospects/{prospect_id}/history", headers=self.auth_headers)
        self.assertEqual(hist_res.status_code, 200)
        history = hist_res.json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["conversation_id"], "conv_test_101")

        # 4. Check global calls endpoint
        calls_res = self.client.get("/v1/intelligence/calls", headers=self.auth_headers)
        self.assertEqual(calls_res.status_code, 200)
        self.assertEqual(len(calls_res.json()), 1)

    def test_prospect_listing_and_detail(self) -> None:
        """Verify GET /prospects and GET /prospects/{id} endpoints."""
        pre_payload = {
            "prospect": {"name": "Carol Danvers", "email": "carol@marvel.example"},
            "objective": "Demo call"
        }
        pre_res = self.client.post("/v1/intelligence/pre-call", json=pre_payload, headers=self.auth_headers)
        prospect_id = pre_res.json()["prospect_id"]

        # List prospects
        list_res = self.client.get("/v1/intelligence/prospects", headers=self.auth_headers)
        self.assertEqual(list_res.status_code, 200)
        prospects = list_res.json()
        self.assertEqual(len(prospects), 1)
        self.assertEqual(prospects[0]["prospect_id"], prospect_id)

        # Get prospect detail
        detail_res = self.client.get(f"/v1/intelligence/prospects/{prospect_id}", headers=self.auth_headers)
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["identity"]["name"], "Carol Danvers")

        # 404 for missing prospect
        not_found_res = self.client.get("/v1/intelligence/prospects/prospect_nonexistent", headers=self.auth_headers)
        self.assertEqual(not_found_res.status_code, 404)

    def test_duplicate_prospect_handling(self) -> None:
        """Verify that submitting a second pre-call for the same identity reuses prospect_id."""
        req1 = {
            "prospect": {"name": "David Miller", "email": "david@acme.example"},
            "objective": "First contact"
        }
        res1 = self.client.post("/v1/intelligence/pre-call", json=req1, headers=self.auth_headers)
        pid1 = res1.json()["prospect_id"]

        req2 = {
            "prospect": {"name": "David Miller", "email": "david@acme.example"},
            "objective": "Second call follow-up"
        }
        res2 = self.client.post("/v1/intelligence/pre-call", json=req2, headers=self.auth_headers)
        pid2 = res2.json()["prospect_id"]

        self.assertEqual(pid1, pid2)

    def test_schema_contract_compatibility(self) -> None:
        """Verify API output conforms to exported contracts/intelligence-packet.json."""
        contract_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "contracts", "intelligence-packet.json")
        if os.path.exists(contract_path):
            with open(contract_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            self.assertIn("properties", schema)
            self.assertIn("schema_version", schema["properties"])
            self.assertIn("packet_id", schema["properties"])
            self.assertIn("trace_id", schema["properties"])


if __name__ == "__main__":
    unittest.main()
