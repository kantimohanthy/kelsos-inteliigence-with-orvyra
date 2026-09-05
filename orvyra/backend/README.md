# ORVYRA — Intelligence Layer for Klesos (MVP)

This is the reference implementation described in the architecture doc:
Klesos sends a prospect before a call, Orvyra returns strategy; Klesos
sends the transcript after, Orvyra returns analysis + next action and
remembers it for the next call.

## Run it

```bash
cd orvyra
pip install -r requirements.txt
uvicorn main:app --reload --port 8009
```

Health check: `GET http://localhost:8009/health`
Interactive docs: `http://localhost:8009/docs`

Optional — real reasoning instead of the heuristic fallback:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```
Without a key, every reasoning step still runs, just via the
conservative heuristic fallbacks in `intelligence/reasoning.py`
(clearly marked in code, and it will honestly recommend
`pursue: false` rather than fabricate an opportunity).

## Endpoints

### `POST /v1/intelligence/pre-call`
```json
{
  "prospect": {"name": "Jane Doe", "company": "Acme AI", "email": "jane@acme.ai", "company_url": "https://acme.ai"},
  "objective": "Book a product demo",
  "product": "Klesos",
  "role_hint": "VP Sales"
}
```
Returns an `IntelligencePacket`: company/person context, an
opportunity hypothesis (with `pursue: true/false` and a reason),
and a conversation strategy (angles + discovery questions —
never a script).

### `POST /v1/intelligence/post-call`
```json
{
  "conversation_id": "conv_1",
  "prospect_id": "prospect_...",
  "transcript": "...",
  "events": []
}
```
Returns a `CallAnalysis`: outcome, intent score, objections,
next best action, and CRM stage/probability. Also writes to
Orvyra's memory so the *next* pre-call for this person is no
longer a cold start.

## What's real vs. stubbed right now

| Piece | Status |
|---|---|
| API contract (`IntelligencePacket`, two endpoints) | Real, stable |
| Identity resolution | Real, but trusts input — no cross-source dedup yet |
| Website ingestion | Real (`httpx` + `BeautifulSoup`) |
| Company/firmographic enrichment | Heuristic keyword match — swap in a real firmographics/hiring/news API |
| Opportunity + conversation strategy reasoning | Heuristic fallback; real LLM reasoning if `ANTHROPIC_API_KEY` set |
| Post-call analysis | Heuristic keyword scan fallback; real LLM if key set |
| Memory / intelligence graph | In-process dict — swap for Postgres + pgvector, nothing else changes |
| CRM sync | Reads Orvyra's own memory only — wire a real CRM API in `ingestion/crm.py` |

## Wiring in Klesos

Klesos doesn't need to know how Orvyra gets its answers — only the
two endpoints above. On your side, the integration is:

1. Before dialing: `POST /v1/intelligence/pre-call` → use
   `conversation_strategy` (angles, questions, things to avoid) to
   brief Klesos's real-time engine. Do **not** feed it as a script.
2. If `opportunity.pursue` is `false`: skip the call, log the reason.
3. After the call: `POST /v1/intelligence/post-call` with the
   transcript → act on `next_best_action` (email/CRM/next call).

## Next build steps (in priority order)

1. Real firmographics + hiring-signal source in `ingestion/company.py`
   (currently keyword-matches scraped site text only).
2. Postgres + pgvector behind `storage/memory.py` (interface is
   already isolated — only that file changes).
3. CRM connector in `ingestion/crm.py` (HubSpot/Salesforce/Pipedrive).
4. Real-time mid-call endpoint (`/v1/intelligence/live`) once the
   two batch endpoints are proven against real Klesos calls.
