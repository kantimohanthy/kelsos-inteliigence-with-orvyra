"""
Postgres / Durable Storage & Identity Resolution Tests.

Verifies:
1. Packet retrieval survival across process/connection restart.
2. Job status survival across connection restart.
3. Identity resolution deduplication via identities table.
4. Conflicting identity signals returning 'needs_review'.
"""

from __future__ import annotations
import os
import sys
import unittest
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.memory import IntelligenceMemory, memory
from storage.jobs import EnrichmentJobStore, jobs
from storage.models import (
    IntelligencePacket, ProspectInput, CompanyContext, PersonContext,
    Opportunity, ConversationStrategy, new_id
)
from intelligence.enrichment import resolve_identity


class TestPostgresStorage(unittest.TestCase):
    def setUp(self) -> None:
        memory.clear()
        jobs.clear()

    def tearDown(self) -> None:
        memory.clear()
        jobs.clear()

    def _sample_packet(self, prospect_id: str, email: str = "test@stripe.com", company: str = "Stripe") -> IntelligencePacket:
        now = datetime.datetime.now(datetime.timezone.utc)
        return IntelligencePacket(
            prospect_id=prospect_id,
            schema_version="1.0.0",
            status="ready",
            valid_until=now + datetime.timedelta(days=7),
            warnings=[],
            sources=[],
            identity=ProspectInput(
                name="Test Person",
                email=email,
                company=company,
                company_url="https://stripe.com",
                linkedin_url=f"https://linkedin.com/in/{email.split('@')[0]}",
            ),
            company_context=CompanyContext(
                name=company,
                industry="Financial Services",
                business_model="B2B SaaS",
            ),
            person_context=PersonContext(
                role="CTO",
                seniority="Executive",
            ),
            facts=[],
            signals=[],
            opportunity=Opportunity(
                pursue=True,
                recommended_angle="Payments Infra",
            ),
            conversation_strategy=ConversationStrategy(
                objective="Test Objective",
                opening_angle="Payments Infra",
                discovery_questions=["Current volume?"],
            ),
            previous_interactions=[],
            created_at=now,
        )

    def test_packet_retrieval_across_restart(self) -> None:
        """1. Packet retrieval after process/connection restart."""
        pid = new_id("prospect")
        pkt = self._sample_packet(pid)
        memory.save_packet(pkt)

        # Simulate process restart by creating a new IntelligenceMemory instance
        fresh_memory = IntelligenceMemory()
        fetched = fresh_memory.get_packet(pid)

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.prospect_id, pid)
        self.assertEqual(fetched.identity.email, "test@stripe.com")
        self.assertEqual(fetched.company_context.industry, "Financial Services")

    def test_job_status_survival_across_restart(self) -> None:
        """2. Job status survival across connection restart."""
        pid = new_id("prospect")
        job = jobs.create(prospect_id=pid, status="pending")
        jobs.update_status(job.job_id, "enriching")

        # Simulate process restart by creating a new EnrichmentJobStore instance
        fresh_jobs = EnrichmentJobStore()
        fetched = fresh_jobs.get(job.job_id)

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.job_id, job.job_id)
        self.assertEqual(fetched.prospect_id, pid)
        self.assertEqual(fetched.status, "enriching")

        # Complete job and verify persistence again
        fresh_jobs.update_status(job.job_id, "ready")
        re_fetched = fresh_jobs.get(job.job_id)
        self.assertEqual(re_fetched.status, "ready")

    def test_identity_deduplication_lookup(self) -> None:
        """3. Identity resolution deduplication via identities table."""
        pid = new_id("prospect")
        pkt = self._sample_packet(pid, email="alex@company.com")
        memory.save_packet(pkt)

        # Lookup by email
        found_by_email = memory.find_by_identity("alex@company.com", None)
        self.assertIsNotNone(found_by_email)
        self.assertEqual(found_by_email.prospect_id, pid)

        # Lookup by linkedin_url
        found_by_linkedin = memory.find_by_identity(None, "https://linkedin.com/in/alex")
        self.assertIsNotNone(found_by_linkedin)
        self.assertEqual(found_by_linkedin.prospect_id, pid)

    def test_conflicting_identity_returns_needs_review(self) -> None:
        """4. Conflicting identity signals returning 'needs_review'."""
        pid = new_id("prospect")
        pkt = self._sample_packet(pid, email="john@example.com", company="Acme Corp")
        memory.save_packet(pkt)

        # Input with matching email but conflicting company name
        conflicting_input = ProspectInput(
            name="John Doe",
            email="john@example.com",
            company="Global Tech Inc",
        )

        res = resolve_identity(conflicting_input)
        self.assertEqual(res["status"], "needs_review")
        self.assertTrue(res["needs_review"])
        self.assertIn("conflicts", res)
        self.assertGreater(len(res["conflicts"]), 0)


if __name__ == "__main__":
    unittest.main()
