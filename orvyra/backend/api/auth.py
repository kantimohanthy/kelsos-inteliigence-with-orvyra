"""
Server-to-server auth.

MVP approach: a single shared bearer token, set as ORVYRA_API_KEY in
this service's environment. Klesos's worker sends the same value as
`Authorization: Bearer <token>`. Good enough for one trusted client
(Klesos); move to per-client keys the moment a second execution
client (CRM, recruitment agent, etc.) comes online, since a shared
secret can't distinguish who's calling or be revoked selectively.
"""

from __future__ import annotations
import os
import hmac
from fastapi import Header, HTTPException, status


def _expected_key() -> str:
    key = os.environ.get("ORVYRA_API_KEY")
    if not key:
        # Fail loud in any real deployment — never silently accept all requests.
        raise RuntimeError("ORVYRA_API_KEY is not set. Refusing to start unauthenticated.")
    return key


async def require_api_key(authorization: str | None = Header(default=None)) -> None:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, _expected_key()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
