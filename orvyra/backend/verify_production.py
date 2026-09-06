from __future__ import annotations
import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import dotenv_values
import httpx

def mask_secret(val: str | None) -> str:
    if not val:
        return "<NOT SET>"
    s = val.strip()
    if len(s) <= 8:
        return "***" + s[-2:]
    return f"***{s[-4:]}"

def run_verification() -> None:
    backend_dir = Path(__file__).resolve().parent
    env_file = backend_dir / ".env.production.local"
    
    env_vars = dotenv_values(env_file) if env_file.exists() else {}
    db_url = env_vars.get("DATABASE_PUBLIC_URL_PROD") or os.environ.get("DATABASE_PUBLIC_URL_PROD")
    api_key = env_vars.get("ORVYRA_API_KEY_PROD") or os.environ.get("ORVYRA_API_KEY_PROD")

    # --- CHECK A: Real Postgres pytest ---
    check_a_passed = False
    check_a_error = ""

    if not db_url:
        check_a_passed = False
        check_a_error = "DATABASE_PUBLIC_URL_PROD not found in .env.production.local"
    else:
        # Prepare subprocess environment with DATABASE_URL
        sub_env = dict(os.environ)
        sub_env["DATABASE_URL"] = db_url

        try:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_v1_pipeline.py", "-k", "test_exact_original_failing_curl_payload", "-q"],
                cwd=str(backend_dir),
                env=sub_env,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                check_a_passed = True
            else:
                check_a_passed = False
                output = (res.stdout + "\n" + res.stderr).replace(db_url, mask_secret(db_url))
                check_a_error = output.strip()
        except Exception as exc:
            check_a_passed = False
            check_a_error = str(exc).replace(db_url, mask_secret(db_url))

    # --- CHECK B: Live production endpoint ---
    check_b_status = 0
    check_b_response = ""

    if not api_key:
        check_b_status = 0
        check_b_response = "ORVYRA_API_KEY_PROD not found in .env.production.local"
    else:
        url = "https://kelsos-inteliigence-with-orvyra-production.up.railway.app/v1/intelligence/pre-call"
        payload = {
            "prospect": {
                "name": "Test",
                "company": "Anthropic",
                "company_url": "https://www.anthropic.com"
            },
            "objective": "test"
        }
        headers = {
            "Authorization": f"Bearer {api_key.strip()}"
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(url, json=payload, headers=headers)
                check_b_status = r.status_code
                if r.status_code == 200:
                    try:
                        check_b_response = json.dumps(r.json(), indent=2)
                    except Exception:
                        check_b_response = r.text
                else:
                    check_b_response = r.text.replace(api_key, mask_secret(api_key))
        except Exception as exc:
            check_b_status = 500
            check_b_response = str(exc).replace(api_key, mask_secret(api_key))

    # --- OUTPUT ---
    print("=== CHECK A: Real Postgres pytest ===")
    print(f"Result: {'PASS' if check_a_passed else 'FAIL'}")
    if not check_a_passed:
        print(check_a_error)

    print()
    print("=== CHECK B: Live production endpoint ===")
    print(f"HTTP Status: {check_b_status}")
    print(f"Response: {check_b_response}")

if __name__ == "__main__":
    run_verification()
