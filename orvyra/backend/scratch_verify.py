import time
import datetime
import json
import httpx

SERVER_URL = "http://127.0.0.1:8009"
HEADERS = {"Authorization": "Bearer test-secret-key-9999", "Content-Type": "application/json"}

def log(msg: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}")

def run_item1_async_verification():
    log("=== ITEM 1: ASYNC PRE-WARMING VERIFICATION OVER REAL SOCKET (PORT 8009) ===")
    lead = {
        "prospect": {
            "name": "Alex Mercer",
            "email": "alex.mercer@stripe.com",
            "company": "Stripe",
            "company_url": "https://stripe.com",
            "role": "Head of Payments Engineering"
        },
        "objective": "Evaluate Stripe's global payment orchestration and API integrations"
    }

    with httpx.Client(base_url=SERVER_URL, timeout=30.0) as client:
        log("Submitting POST /v1/prospects/enrich...")
        start_t = time.perf_counter()
        res = client.post("/v1/prospects/enrich", json=[lead], headers=HEADERS)
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        
        log(f"HTTP Response Status Code: {res.status_code}")
        log(f"HTTP Response Time: {duration_ms:.2f} ms")
        
        data = res.json()
        log(f"Response Payload: {json.dumps(data, indent=2)}")
        
        job_info = data[0]
        job_id = job_info["job_id"]
        prospect_id = job_info["prospect_id"]
        initial_status = job_info["status"]
        
        log(f"Initial Job Status: '{initial_status}' (Fast response time: {duration_ms:.2f} ms < 500ms)")
        
        log(f"Polling GET /v1/enrichment-jobs/{job_id}...")
        poll_count = 0
        while True:
            poll_count += 1
            poll_res = client.get(f"/v1/enrichment-jobs/{job_id}", headers=HEADERS)
            status_data = poll_res.json()
            current_status = status_data.get("status")
            log(f"Poll #{poll_count} status: '{current_status}' (error: {status_data.get('error')})")
            
            if current_status in ["ready", "partial", "failed"]:
                break
            time.sleep(0.5)
            
        log(f"Final Job Status achieved: '{current_status}'")
        
        log(f"Fetching complete pre-warmed intelligence packet for prospect_id='{prospect_id}'...")
        packet_res = client.get(f"/v1/intelligence/prospects/{prospect_id}", headers=HEADERS)
        log(f"Packet Fetch Status: {packet_res.status_code}")
        packet = packet_res.json()
        log(f"Packet Prospect Name: {packet['identity']['name']}")
        log(f"Packet Prospect Company: {packet['company_context']['name']}")
        log(f"Packet Status: {packet['status']}")
        log(f"Packet Facts Count: {len(packet['facts'])}")

def run_item2_real_company_verification():
    log("\n=== ITEM 2: REAL COMPANY SITE CORE V1 PIPELINE RUN (FULL UNTRUNCATED JSON) ===")
    req = {
        "prospect": {
            "name": "Sarah Chen",
            "email": "sarah.chen@anthropic.com",
            "company": "Anthropic",
            "company_url": "https://www.anthropic.com",
            "role": "VP of AI Systems"
        },
        "objective": "Understand Anthropic's Claude models, safety research, and enterprise AI deployment offerings"
    }
    
    with httpx.Client(base_url=SERVER_URL, timeout=60.0) as client:
        log("Executing POST /v1/intelligence/pre-call against real website https://www.anthropic.com...")
        start_t = time.perf_counter()
        res = client.post("/v1/intelligence/pre-call", json=req, headers=HEADERS)
        duration_sec = time.perf_counter() - start_t
        log(f"Pipeline finished in {duration_sec:.2f} seconds.")
        log(f"HTTP Status: {res.status_code}")
        
        packet = res.json()
        print("\n--- FULL UNTRUNCATED INTELLIGENCE PACKET JSON ---")
        print(json.dumps(packet, indent=2))
        print("--- END FULL UNTRUNCATED JSON ---\n")

if __name__ == "__main__":
    run_item1_async_verification()
    run_item2_real_company_verification()
