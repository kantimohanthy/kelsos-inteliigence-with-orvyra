import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ORVYRA_API_KEY"] = "test-secret-key-9999"

from fastapi.testclient import TestClient
from main import app
from storage.memory import memory
from storage.jobs import jobs

memory.clear()
jobs.clear()
client = TestClient(app)
headers = {"Authorization": "Bearer test-secret-key-9999"}

print("=== Real Async Pre-Warming Run Demo ===")
t0 = datetime.datetime.now(datetime.timezone.utc)
print(f"[{t0.strftime('%H:%M:%S.%f')[:-3]}] Submitting lead batch to POST /v1/prospects/enrich...")

res = client.post(
    "/v1/prospects/enrich",
    json=[{
        "prospect": {
            "name": "Elon Vance",
            "company": "SpaceX",
            "company_url": "https://example.com"
        },
        "objective": "Demonstrate async pre-warming pipeline"
    }],
    headers=headers
)

t1 = datetime.datetime.now(datetime.timezone.utc)
batch = res.json()
job_id = batch[0]["job_id"]
prospect_id = batch[0]["prospect_id"]
elapsed_ms = (t1 - t0).total_seconds() * 1000
print(f"[{t1.strftime('%H:%M:%S.%f')[:-3]}] Batch HTTP response received in {elapsed_ms:.1f}ms!")
print(f"            Job ID: {job_id} | Prospect ID: {prospect_id} | Initial Status: {batch[0]['status']}")

poll_res = client.get(f"/v1/enrichment-jobs/{job_id}", headers=headers)
t2 = datetime.datetime.now(datetime.timezone.utc)
print(f"[{t2.strftime('%H:%M:%S.%f')[:-3]}] Polled GET /v1/enrichment-jobs/{job_id} -> Status: {poll_res.json()['status']}")

packet_res = client.get(f"/v1/intelligence/prospects/{prospect_id}", headers=headers)
t3 = datetime.datetime.now(datetime.timezone.utc)
print(f"[{t3.strftime('%H:%M:%S.%f')[:-3]}] Fetched pre-warmed packet for: {packet_res.json()['identity']['name']} ({packet_res.json()['identity']['company']})")
print("=======================================")
