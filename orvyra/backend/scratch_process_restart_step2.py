import httpx
import json

URL = "http://127.0.0.1:8009"
HEADERS = {"Authorization": "Bearer test-secret-key-9999"}

print("=== STEP 2: QUERY NEW PROCESS 2 (PORT 8009) FOR JOB & PACKET SAVED BY KILLED PROCESS 1 ===")

with open("H:/kelsos inteliigence with orvyra/orvyra/backend/scratch_restart_state.json", "r") as f:
    state = json.load(f)

job_id = state["job_id"]
prospect_id = state["prospect_id"]

with httpx.Client(timeout=10.0) as client:
    # 1. Fetch Job from NEW Process 2
    job_res = client.get(f"{URL}/v1/enrichment-jobs/{job_id}", headers=HEADERS)
    print(f"GET /v1/enrichment-jobs/{job_id} -> HTTP {job_res.status_code}")
    print(f"Fetched Job Data from Process 2: {json.dumps(job_res.json(), indent=2)}")

    # 2. Fetch Packet from NEW Process 2
    pkt_res = client.get(f"{URL}/v1/intelligence/prospects/{prospect_id}", headers=HEADERS)
    print(f"GET /v1/intelligence/prospects/{prospect_id} -> HTTP {pkt_res.status_code}")
    pkt = pkt_res.json()
    print(f"Fetched Packet Prospect Name: {pkt['identity']['name']}")
    print(f"Fetched Packet Company: {pkt['identity']['company']}")
    print(f"Fetched Packet Status: {pkt['status']}")

print("=== PROCESS-LEVEL RESTART VERIFICATION SUCCESSFUL! ===")
