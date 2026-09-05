import sys
import os
import asyncio
import time
import json

sys.path.insert(0, r"H:\kelsos inteliigence with orvyra\orvyra\backend")

from storage.models import ProspectInput
from intelligence.pipeline import build_intelligence_pipeline
from intelligence.llm import has_llm

async def main():
    print(f"=== PART A STEP 1: REAL LLM EXTRACTION (stripe.com) ===")
    print(f"has_llm(): {has_llm()}")
    
    prospect = ProspectInput(
        name="Patrick Collison",
        email="patrick@stripe.com",
        company="Stripe",
        company_url="https://stripe.com",
        role="CEO"
    )
    
    start_t = time.perf_counter()
    packet = await build_intelligence_pipeline(
        prospect=prospect,
        objective="Evaluate Stripe payment infrastructure and global expansion APIs",
        product_name="Klesos"
    )
    elapsed = time.perf_counter() - start_t
    
    print(f"Pipeline finished in {elapsed:.2f} seconds.")
    print(f"Packet Prospect: {packet.identity.name} ({packet.identity.company})")
    print(f"Packet Status: {packet.status}")
    print(f"Total Facts/Claims Extracted: {len(packet.facts)}")
    
    fact_count = sum(1 for f in packet.facts if f.type == "fact")
    inference_count = sum(1 for f in packet.facts if f.type == "inference")
    
    print(f"Claim Type breakdown: {fact_count} FACTS, {inference_count} INFERENCES")
    
    packet_dict = packet.model_dump(mode="json")
    print("\n--- FULL UNTRUNCATED INTELLIGENCE PACKET JSON ---")
    print(json.dumps(packet_dict, indent=2))
    print("--- END FULL UNTRUNCATED JSON ---\n")

if __name__ == "__main__":
    asyncio.run(main())
