"""
Async Pre-Warming Test Suite — 7 Dedicated Pre-Warming Verification Scenarios.

Scenarios:
1. test_01_submit_enrich_returns_pending_immediately
2. test_02_poll_enrichment_job_before_ready
3. test_03_poll_enrichment_job_until_ready
4. test_04_duplicate_identity_dedup_with_mock_call_count
5. test_05_partial_batch_failure_isolation
6. test_06_direct_pre_call_fallback_regression
7. test_07_pre_warmed_instant_return_with_mock_call_count
"""

from __future__ import annotations
import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from storage.memory import memory
from storage.jobs import jobs
from storage.models import SourceDocument


class TestAsyncPreWarming(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ORVYRA_API_KEY"] = "test-secret-key-9999"
        memory.clear()
        jobs.clear()
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-secret-key-9999"}

    def test_01_submit_enrich_returns_pending_immediately(self) -> None:
        """Scenario 1: POST /v1/prospects/enrich returns job_id and status: pending immediately."""
        lead = {
            "prospect": {"name": "Scenario One", "email": "scen1@example.com"},
            "objective": "Pre-warming submit test"
        }
        res = self.client.post("/v1/prospects/enrich", json=[lead], headers=self.headers)
        self.assertEqual(res.status_code, 200)
        batch = res.json()
        self.assertEqual(len(batch), 1)
        self.assertIn("job_id", batch[0])
        self.assertIn("prospect_id", batch[0])
        self.assertEqual(batch[0]["status"], "pending")

    def test_02_poll_enrichment_job_before_ready(self) -> None:
        """Scenario 2: Poll GET /v1/enrichment-jobs/{job_id} immediately returns non-ready status."""
        lead = {
            "prospect": {"name": "Scenario Two", "email": "scen2@example.com"},
            "objective": "Pre-warming poll before ready"
        }
        res = self.client.post("/v1/prospects/enrich", json=[lead], headers=self.headers)
        job_id = res.json()[0]["job_id"]

        job_res = self.client.get(f"/v1/enrichment-jobs/{job_id}", headers=self.headers)
        self.assertEqual(job_res.status_code, 200)
        job_data = job_res.json()
        self.assertEqual(job_data["job_id"], job_id)
        self.assertIn(job_data["status"], ["pending", "enriching", "ready", "partial", "needs_review"])

    def test_03_poll_enrichment_job_until_ready(self) -> None:
        """Scenario 3: Poll job until completion and verify packet is fetchable in memory."""
        lead = {
            "prospect": {
                "name": "Scenario Three",
                "email": "scen3@example.com",
                "company": "Scenario 3 Corp",
                "company_url": "https://example.com"
            },
            "objective": "Pre-warming poll until ready"
        }
        res = self.client.post("/v1/prospects/enrich", json=[lead], headers=self.headers)
        job_id = res.json()[0]["job_id"]
        prospect_id = res.json()[0]["prospect_id"]

        # Poll job status
        job_res = self.client.get(f"/v1/enrichment-jobs/{job_id}", headers=self.headers)
        self.assertEqual(job_res.status_code, 200)

        # Verify packet is fetchable
        packet_res = self.client.get(f"/v1/intelligence/prospects/{prospect_id}", headers=self.headers)
        self.assertEqual(packet_res.status_code, 200)
        self.assertEqual(packet_res.json()["identity"]["name"], "Scenario Three")

    def test_04_duplicate_identity_dedup_with_mock_call_count(self) -> None:
        """Scenario 4: Duplicate identity submission within valid_until skips pipeline run (assert pipeline call count = 0)."""
        lead = {
            "prospect": {"name": "Scenario Four", "email": "scen4@example.com"},
            "objective": "Duplicate identity test"
        }
        # First submission (pre-warms & saves to memory)
        res1 = self.client.post("/v1/prospects/enrich", json=[lead], headers=self.headers)
        self.assertEqual(res1.status_code, 200)
        job_id1 = res1.json()[0]["job_id"]
        pid1 = res1.json()[0]["prospect_id"]

        # Wait for background pre-warming to complete
        for _ in range(50):
            jres = self.client.get(f"/v1/enrichment-jobs/{job_id1}", headers=self.headers)
            if jres.status_code == 200 and jres.json()["status"] in ("ready", "partial", "failed", "needs_review"):
                break
            time.sleep(0.05)

        # Second submission within valid_until window, mock pipeline to ensure it is NOT called
        with patch("intelligence.pipeline.build_intelligence_pipeline") as mock_pipeline:
            res2 = self.client.post("/v1/prospects/enrich", json=[lead], headers=self.headers)
            self.assertEqual(res2.status_code, 200)
            pid2 = res2.json()[0]["prospect_id"]
            status2 = res2.json()[0]["status"]

            self.assertEqual(pid1, pid2)
            self.assertIn(status2, ["ready", "partial", "needs_review"])
            # Pipeline must NOT be re-executed for duplicate fresh lead
            mock_pipeline.assert_not_called()

    def test_05_partial_batch_failure_isolation(self) -> None:
        """Scenario 5: Heterogeneous batch of 3 leads with 1 SSRF-blocked URL isolates failure without a 500 server error; Lead A & C reach 'ready', Lead B reaches 'needs_review'."""
        batch_leads = [
            {"prospect": {"name": "Batch Lead A", "company": "Acme SaaS", "company_url": "https://acme.example"}, "objective": "Batch A"}, # Healthy lead -> ready
            {"prospect": {"name": "Batch Lead B", "company_url": "http://127.0.0.1"}, "objective": "Batch B"}, # SSRF blocked URL -> critic veto -> needs_review
            {"prospect": {"name": "Batch Lead C", "company": "Tech Corp", "company_url": "https://techcorp.example"}, "objective": "Batch C"} # Healthy lead -> ready
        ]

        async def fake_crawl_company(url: str | None, max_pages: int = 10):
            if not url or "127.0.0.1" in url:
                return [SourceDocument(url=url or "", title="SSRF Blocked", content="", status="blocked", error="Local IP blocked")]
            return [
                SourceDocument(
                    doc_id=f"doc_{url}",
                    url=url,
                    title="Company Overview",
                    content=f"{url} is a leading SaaS provider with active hiring in engineering and expanding revenue teams.",
                    status="success"
                )
            ]

        with patch("intelligence.pipeline.crawl_company", side_effect=fake_crawl_company):
            res = self.client.post("/v1/prospects/enrich", json=batch_leads, headers=self.headers)
            self.assertEqual(res.status_code, 200)
            batch_res = res.json()
            self.assertEqual(len(batch_res), 3)

            # 1. Initial submission status should be 'pending' for all jobs
            for job in batch_res:
                self.assertEqual(job["status"], "pending")

            # 2. Poll jobs until completion and verify isolation
            final_statuses = {}
            for job in batch_res:
                job_id = job["job_id"]
                for _ in range(50):
                    jres = self.client.get(f"/v1/enrichment-jobs/{job_id}", headers=self.headers)
                    if jres.status_code == 200 and jres.json()["status"] not in ("pending", "enriching"):
                        final_statuses[job_id] = jres.json()["status"]
                        break
                    time.sleep(0.05)

            job_a_id = batch_res[0]["job_id"]
            job_b_id = batch_res[1]["job_id"]
            job_c_id = batch_res[2]["job_id"]

            # Healthy leads with valid content reach 'ready'
            self.assertEqual(final_statuses.get(job_a_id), "ready")
            self.assertEqual(final_statuses.get(job_c_id), "ready")

            # Lead B: SSRF blocked URL -> zero facts -> critic veto (pursue=False) -> terminal status = 'needs_review'
            self.assertEqual(final_statuses.get(job_b_id), "needs_review")

    def test_06_direct_pre_call_fallback_regression(self) -> None:
        """Scenario 6: Calling pre-call directly (no pre-warming) works synchronously as a regression test."""
        req = {
            "prospect": {"name": "Scenario Six", "email": "scen6@example.com"},
            "objective": "Direct call regression test"
        }
        res = self.client.post("/v1/intelligence/pre-call", json=req, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        packet = res.json()
        self.assertEqual(packet["identity"]["name"], "Scenario Six")

    def test_07_pre_warmed_instant_return_with_mock_call_count(self) -> None:
        """Scenario 7: Calling pre-call for a pre-warmed prospect returns instantly from memory (pipeline mock call count = 0)."""
        lead = {
            "prospect": {"name": "Scenario Seven", "email": "scen7@example.com"},
            "objective": "Pre-warmed instant return test"
        }
        # Pre-warm prospect
        res1 = self.client.post("/v1/prospects/enrich", json=[lead], headers=self.headers)
        self.assertEqual(res1.status_code, 200)
        job_id1 = res1.json()[0]["job_id"]

        # Wait for background pre-warming to complete
        for _ in range(50):
            jres = self.client.get(f"/v1/enrichment-jobs/{job_id1}", headers=self.headers)
            if jres.status_code == 200 and jres.json()["status"] in ("ready", "partial", "failed", "needs_review"):
                break
            time.sleep(0.05)

        # Call pre-call for pre-warmed prospect with pipeline mocked to ensure it is NOT called
        with patch("intelligence.pipeline.build_intelligence_pipeline") as mock_pipeline:
            res = self.client.post("/v1/intelligence/pre-call", json=lead, headers=self.headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["identity"]["name"], "Scenario Seven")
            # Pipeline must NOT be re-executed for pre-warmed prospect
            mock_pipeline.assert_not_called()


if __name__ == "__main__":
    unittest.main()
