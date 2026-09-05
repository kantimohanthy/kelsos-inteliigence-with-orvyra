import asyncio
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.models import ProspectInput
from intelligence.pipeline import build_intelligence_pipeline

async def main():
    prospect = ProspectInput(
        name="Patrick Collison",
        company="Stripe",
        email="patrick@stripe.com",
        company_url="https://stripe.com",
        linkedin_url="https://linkedin.com/in/patrickcollison"
    )
    packet = await build_intelligence_pipeline(
        prospect=prospect,
        objective="Qualify Stripe for AI voice agent outbound sales integration",
        product_name="Klesos",
        role_hint="CEO"
    )
    print("---STRIPE_PACKET_JSON_START---")
    print(json.dumps(packet.model_dump(mode="json"), indent=2))
    print("---STRIPE_PACKET_JSON_END---")

if __name__ == "__main__":
    asyncio.run(main())
