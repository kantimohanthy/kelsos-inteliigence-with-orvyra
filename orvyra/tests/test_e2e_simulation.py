"""
Sprint 0 End-to-End Simulation Test.

Simulates the complete full-loop pipeline:
1. Test lead enters Orvyra via POST /v1/intelligence/pre-call.
2. IntelligencePacket is generated with repaired schema fields (version, packet_id, trace_id, sources).
3. Dashboard fetches the queue (GET /v1/intelligence/prospects) and detail view (GET /v1/intelligence/prospects/{id}).
4. Mock Klesos client submits post-call transcript (POST /v1/intelligence/post-call).
5. Post-call analysis appears in prospect call history (GET /v1/intelligence/prospects/{id}/history) & calls log.
"""

from __future__ import annotations
import os
import sys
import unittest

# Ensure backend directory is in python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

os.environ["ORVYRA_API_KEY"] = "e2e-simulation-test-key-7777"

from fastapi.testclient import TestClient
from main import app
from storage.memory import memory


class TestOrvyraE2ESimulation(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ORVYRA_API_KEY"] = "test-secret-key-9999"
        memory.clear()
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-secret-key-9999"}


    def test_full_lead_to_post_call_loop(self) -> None:
        print("\n--- Running Orvyra Sprint 0 E2E Simulation ---")

        # Step 1: Lead intake -> Pre-call API
        lead_input = {
            "prospect": {
                "name": "Sarah Connor",
                "company": "Cyberdyne Systems",
                "email": "sarah.connor@cyberdyne.example",
                "linkedin_url": "https://linkedin.com/in/sarahconnor",
                "company_url": "https://cyberdyne.example"
            },
            "objective": "Demonstrate outbound AI voice agent capabilities",
            "product": "Klesos AI Agent",
            "role_hint": "Head of Operations"
        }

        print("[Step 1] Submitting test lead to Pre-call API...")
        pre_res = self.client.post("/v1/intelligence/pre-call", json=lead_input, headers=self.headers)
        self.assertEqual(pre_res.status_code, 200, f"Pre-call failed: {pre_res.text}")

        packet = pre_res.json()
        prospect_id = packet["prospect_id"]
        print(f"[Step 2] Intelligence Packet generated! Prospect ID: {prospect_id}")
        self.assertEqual(packet["schema_version"], "1.0.0")
        self.assertTrue(packet["packet_id"].startswith("pkt_"))
        self.assertTrue(packet["trace_id"].startswith("trace_"))
        self.assertIn("sources", packet)
        self.assertGreater(len(packet["sources"]), 0)

        # Step 3: Dashboard retrieves prospect queue and detail
        print("[Step 3] Dashboard querying GET /v1/intelligence/prospects...")
        queue_res = self.client.get("/v1/intelligence/prospects", headers=self.headers)
        self.assertEqual(queue_res.status_code, 200)
        queue = queue_res.json()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["prospect_id"], prospect_id)

        print(f"[Step 3b] Dashboard querying GET /v1/intelligence/prospects/{prospect_id}...")
        detail_res = self.client.get(f"/v1/intelligence/prospects/{prospect_id}", headers=self.headers)
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["identity"]["company"], "Cyberdyne Systems")

        # Step 4: Mock Klesos client submits post-call transcript
        print("[Step 4] Mock Klesos client sending transcript to Post-call API...")
        transcript_payload = {
            "conversation_id": "conv_klesos_e2e_888",
            "prospect_id": prospect_id,
            "transcript": (
                "Klesos: Hi Sarah, this is Klesos calling regarding outbound AI workflow automation. "
                "Sarah: Yes, we are actively looking for solutions to streamline ops! Sounds good, send me pricing."
            ),
            "events": [
                {"type": "dial", "detail": "call_initiated"},
                {"type": "media_stream", "detail": "active_audio"},
                {"type": "hangup", "detail": "user_completed"}
            ]
        }
        post_res = self.client.post("/v1/intelligence/post-call", json=transcript_payload, headers=self.headers)
        self.assertEqual(post_res.status_code, 200, f"Post-call failed: {post_res.text}")

        analysis = post_res.json()
        print(f"[Step 4b] Call Analysis completed! Outcome: {analysis['outcome']}, Intent Score: {analysis['intent_score']}")
        self.assertEqual(analysis["outcome"], "interested_follow_up")
        self.assertGreater(analysis["intent_score"], 0.6)

        # Step 5: Dashboard verifies history & call logs
        print("[Step 5] Dashboard checking GET /v1/intelligence/prospects/{id}/history...")
        history_res = self.client.get(f"/v1/intelligence/prospects/{prospect_id}/history", headers=self.headers)
        self.assertEqual(history_res.status_code, 200)
        history = history_res.json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["conversation_id"], "conv_klesos_e2e_888")

        print("[Step 5b] Dashboard checking GET /v1/intelligence/calls...")
        calls_res = self.client.get("/v1/intelligence/calls", headers=self.headers)
        self.assertEqual(calls_res.status_code, 200)
        self.assertEqual(len(calls_res.json()), 1)

        print("--- E2E Simulation Completed Successfully! Zero manual data insertion required. ---")


if __name__ == "__main__":
    unittest.main()
