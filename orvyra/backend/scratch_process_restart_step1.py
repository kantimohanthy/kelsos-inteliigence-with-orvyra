import httpx
import time
import json

URL = "http://127.0.0.1:8009"
HEADERS = {"Authorization": "Bearer test-secret-key-9999"}

print("=== STEP 1: SUBMIT ENRICHMENT JOB TO PROCESS 1 (PORT 8009) ===")
lead = [
    {
        "prospect": {
            "name": "Restart Proof Person",
            "email": "restart.proof@stripe.com",
            "company": "Stripe",
            "company_url": "https://stripe.com"
        },
        "objective": "Verify process-level restart persistence"
    }
]

t0 = time.time()
with httpx.Client(timeout=30.0) as client:
    res = client.post(f"{URL}/v1/prospects/enrich", json=lead, headers=HEADERS)
    t1 = time.time()

    print(f"POST /v1/prospects/enrich -> HTTP {res.status_code} in {(t1-t0)*1000:.2f}ms")
    data = res.json()[0]
    job_id = data["job_id"]
    prospect_id = data["prospect_id"]
    print(f"Job ID: {job_id}, Prospect ID: {prospect_id}, Initial Status: {data['status']}")

    # Poll until completed
    for i in range(1, 60):
        time.sleep(0.5)
        poll_res = client.get(f"{URL}/v1/enrichment-jobs/{job_id}", headers=HEADERS)
        st = poll_res.json()["status"]
        print(f"Poll #{i} status: {st}")
        if st in ("ready", "partial", "failed", "needs_review"):
            break

    # Fetch packet
    pkt_res = client.get(f"{URL}/v1/intelligence/prospects/{prospect_id}", headers=HEADERS)
    print(f"GET /v1/intelligence/prospects/{prospect_id} -> HTTP {pkt_res.status_code}")
    print(f"Packet Prospect Name: {pkt_res.json()['identity']['name']}")
    print(f"Packet Status: {pkt_res.json()['status']}")

    # Save state
    state = {"job_id": job_id, "prospect_id": prospect_id, "status": st, "name": pkt_res.json()['identity']['name']}
    with open("H:/kelsos inteliigence with orvyra/orvyra/backend/scratch_restart_state.json", "w") as f:
        json.dump(state, f, indent=2)
    print("Saved state to scratch_restart_state.json")
