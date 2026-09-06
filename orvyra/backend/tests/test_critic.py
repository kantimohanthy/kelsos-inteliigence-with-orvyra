"""
Unit tests for the Opportunity Critic Pass (Part 1).
"""

from __future__ import annotations
import unittest
from storage.models import Opportunity, Claim, ClaimType, EvidenceSource
from intelligence.critic import critique_opportunity


class TestOpportunityCritic(unittest.TestCase):
    def test_critic_weak_single_source_claim(self) -> None:
        """Verify critic pass downgrades/flips opportunity supported by a single weak claim."""
        weak_claim = Claim(
            claim="We might be expanding sales hiring next year",
            type=ClaimType.INFERENCE,
            confidence=0.5,
            evidence=[EvidenceSource(source_type="website_scrape", excerpt="hiring maybe", confidence=0.5)]
        )
        raw_opp = Opportunity(
            primary_problem="Sales team expansion needs voice automation",
            confidence=0.85,
            value_hypothesis="Automate SDR calling",
            likely_objections=["Budget"],
            recommended_angle="Co-pilot angle",
            pursue=True,
            reason_if_not_pursue=None
        )

        critiqued = critique_opportunity(raw_opp, [weak_claim], [])
        self.assertFalse(critiqued.pursue)
        self.assertLess(critiqued.confidence, 0.5)
        self.assertIsNotNone(critiqued.reason_if_not_pursue)
        self.assertIn("single low-confidence claim", critiqued.reason_if_not_pursue or "")

    def test_critic_prior_rejection_override(self) -> None:
        """Verify prior negative interaction forces pursue: False regardless of current run score."""
        fact_claim = Claim(
            claim="Active hiring for 20 SDRs",
            type=ClaimType.FACT,
            confidence=0.95,
            evidence=[EvidenceSource(source_type="website_scrape", excerpt="Hiring 20 SDRs", confidence=0.95)]
        )
        raw_opp = Opportunity(
            primary_problem="High SDR growth",
            confidence=0.90,
            value_hypothesis="Automate SDR work",
            likely_objections=["AI quality"],
            recommended_angle="Growth angle",
            pursue=True,
            reason_if_not_pursue=None
        )
        prior_interactions = [
            {"date": "2026-08-01", "outcome": "Prospect stated: do not contact us again under any circumstances"}
        ]

        critiqued = critique_opportunity(raw_opp, [fact_claim], prior_interactions)
        self.assertFalse(critiqued.pursue)
        self.assertIsNotNone(critiqued.reason_if_not_pursue)
        self.assertIn("rejection or do-not-contact", critiqued.reason_if_not_pursue or "")


if __name__ == "__main__":
    unittest.main()
