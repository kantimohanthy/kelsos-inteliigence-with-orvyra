# ORVYRA — Async Pre-Warming (Corrected Build Instructions)

**For: Antigravity, working in `H:\kelsos inteliigence with orvyra\orvyra\`**
**Precondition: Sprint 0 (versioned contract) and Core V1 (crawler/extraction/opportunity/strategy pipeline) are both complete — 15/15 tests passing, verified by manual run.**

---

## 0. Before writing any code

Read these files as they exist right now — do not assume field names below without checking:

- `orvyra/backend/storage/models.py` (specifically the `status` and `valid_until` fields Sprint 0 added to `IntelligencePacket` — confirm their exact type/enum, if any, before reusing them)
- `orvyra/backend/storage/memory.py`
- `orvyra/backend/api/routes.py`
- `orvyra/backend/interactions/pre_call.py`
- `orvyra/backend/intelligence/pipeline.py`

If this doc's description of any of those files doesn't match what's on disk, the file on disk wins — extend it, don't fork it.

## 1. The problem this fixes

Right now, `POST /v1/intelligence/pre-call` runs the entire crawl → extract → reason → strategy pipeline **synchronously**, inside the HTTP request. That's fine for testing. It is the wrong shape for Kyle to actually call right before dialing — a real crawl can take several seconds, and nothing about a live outbound call should be waiting on a webpage fetch.

The fix is **not** Celery/Redis (that's still correctly deferred — see Scope lock). The fix is running the same pipeline as a background task inside the existing FastAPI process, with a status the caller can poll. This is a few hours of work, not a new infrastructure layer.

## 2. Scope lock

**Is:** submit leads ahead of time → pipeline runs in the background → caller polls or fetches the finished packet → pre-call becomes "give me what's ready" instead of "go do all the work right now."

**Is not:** Celery, Redis, Postgres, Docker, a real job queue with retries/backoff/dead-letter handling. `python`'s standard library and FastAPI's built-in `BackgroundTasks` are enough for this sprint. In-memory storage stays exactly as it is — jobs and packets both live in the existing `IntelligenceMemory` singleton (or a small sibling to it), not a new database.

Do not touch `crawler.py`, `extraction.py`, `person.py`, `opportunity.py`, or `strategy.py` internals — this sprint wraps the existing `build_intelligence_packet()` orchestrator in an async job, it doesn't change what that orchestrator does.

## 3. New endpoints

Add to `api/routes.py`:

```python
POST /v1/prospects/enrich
```
Body: a **list** of the same shape `PreCallRequest.prospect` + `objective` + `role_hint` + optional `product_context` already accepts (reuse those models, don't redefine them). For each lead in the list:

1. Resolve identity the same way `run_pre_call()` already does (`find_by_identity`).
2. If an existing packet is found **and** still fresh (`valid_until` in the future — reuse whatever field Sprint 0 already added; if `valid_until` isn't set on old packets, treat missing as stale), skip re-enrichment and return that packet's `prospect_id` with `status: "ready"` immediately.
3. Otherwise, create a job entry with `status: "pending"`, kick off `build_intelligence_packet()` via `BackgroundTasks`, and return a `job_id` + `prospect_id` immediately (don't block the response on the pipeline running).

Response — a list, one entry per submitted lead:
```json
[{"job_id": "job_abc123", "prospect_id": "prospect_xyz", "status": "pending"}]
```

```python
GET /v1/enrichment-jobs/{job_id}
```
Returns the job's current status and, once done, the `prospect_id` to fetch:
```json
{"job_id": "job_abc123", "prospect_id": "prospect_xyz", "status": "ready", "error": null}
```

Status values: `pending` (queued, not started) → `enriching` (pipeline running) → one of `ready` (success), `partial` (pipeline completed but with a degraded/incomplete result — e.g. crawler found nothing, or the LLM call failed and it fell back to heuristics), `failed` (pipeline raised and couldn't produce a packet at all), or `needs_review` (reserved for future identity-conflict handling — not used yet in this sprint, just don't remove it if `enrichment.py`'s `resolve_identity()` gets extended later).

## 4. Job tracking

Add a small, separate structure — don't overload `IntelligenceMemory`'s packet store with job bookkeeping:

```python
# storage/jobs.py (new file)
class EnrichmentJob(BaseModel):
    job_id: str
    prospect_id: str
    status: Literal["pending", "enriching", "ready", "partial", "failed", "needs_review"]
    error: str | None = None
    created_at: datetime

class EnrichmentJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, EnrichmentJob] = {}

    def create(self, prospect_id: str) -> EnrichmentJob: ...
    def update_status(self, job_id: str, status: str, error: str | None = None) -> None: ...
    def get(self, job_id: str) -> EnrichmentJob | None: ...

jobs = EnrichmentJobStore()  # process-wide singleton, same pattern as storage/memory.py's `memory`
```

## 5. Wiring the background task

```python
async def _run_enrichment_job(job_id: str, request: PreCallRequest) -> None:
    jobs.update_status(job_id, "enriching")
    try:
        packet = await build_intelligence_packet(request)
        memory.save_packet(packet)
        status = "ready" if packet.opportunity.confidence > 0 and packet.company_context.industry else "partial"
        jobs.update_status(job_id, status)
    except Exception as e:
        jobs.update_status(job_id, "failed", error=str(e))
        # log the full traceback — a silently swallowed background-task exception
        # is the single worst failure mode here, since nothing else will surface it
```

Use FastAPI's `BackgroundTasks` parameter on the `/v1/prospects/enrich` route handler to schedule `_run_enrichment_job` per lead — do not use a bare `asyncio.create_task` detached from the request, since `BackgroundTasks` is what FastAPI actually tracks and it's the standard pattern here.

**The "partial" heuristic above is a starting point, not gospel** — pick whatever condition on the finished packet reasonably indicates "the pipeline ran but didn't get much" (e.g. zero facts extracted, or the crawler returned zero documents) and document your actual condition in a comment. It doesn't need to be perfect this sprint.

## 6. `pre-call` becomes "fetch what's warm, else fall back"

Update `run_pre_call()` in `interactions/pre_call.py`:

1. If the prospect was already submitted via `/v1/prospects/enrich` and has a `ready` or `partial` packet, return it immediately — no pipeline run.
2. If there's no pre-warmed packet (the caller skipped pre-warming and called `pre-call` directly, as every existing test and the current Klesos client does today), **fall back to running the pipeline synchronously, exactly as it does now.** This is the important backward-compatibility rule: nothing that calls `pre-call` today should break or start getting empty responses. Pre-warming is an optimization path, not a replacement for the existing contract.

## 7. Optional but recommended — `refresh`

If time permits this sprint (not required for done, but cheap given the machinery above already exists):

```python
POST /v1/intelligence/prospects/{id}/refresh
```
Forces re-enrichment ignoring `valid_until` freshness — same background-job mechanism as §3, just skips the freshness check. This is what the dashboard's future "refresh" button (Sprint 5, not this sprint) will call — build the endpoint now since it's a thin wrapper over what already exists, but don't build the dashboard button yet.

## 8. Klesos-side client — document only, don't force a change

Add the two new calls to `source/klesos-worker-orvyra-client.ts` as new exported functions (`enrichLeads()`, `getEnrichmentJobStatus()`), following the existing file's pattern (undici + zod, fail-open on error). **Do not change `preCall()`'s existing signature or behavior** — Kyle's worker isn't wired to the new pre-warming flow yet (that's Sprint 4, separate work), so the existing synchronous call path must keep working unchanged.

## 9. Tests

Add `orvyra/backend/tests/test_prewarming.py`:

1. Submit one lead via `/v1/prospects/enrich` → get back `job_id` + `status: pending`
2. Poll `/v1/enrichment-jobs/{job_id}` immediately → `pending` or `enriching`, not `ready` yet (proves it's actually async, not just fast)
3. Poll again after the background task has had time to finish → `ready`, with a fetchable packet at `GET /v1/intelligence/prospects/{prospect_id}`
4. Submit the same identity twice within `valid_until` → second call returns the existing packet's `prospect_id` immediately with `status: ready`, **does not create a second job** (prove no duplicate pipeline run — e.g. assert the crawler mock was only called once)
5. Submit a batch of 3 leads where one has an invalid/unreachable `company_url` → the other two still reach `ready`/`partial`, the bad one reaches `failed` with a populated `error`, and the whole batch request doesn't 500
6. Call `pre-call` directly (skipping `/enrich` entirely) for a brand-new prospect → still works synchronously exactly as before, unchanged behavior (this is the regression test for §6's fallback rule)
7. Call `pre-call` for a prospect that *was* pre-warmed and is `ready` → returns instantly, and (via a call-count assertion on the pipeline function, mocked) does **not** re-run the pipeline

Run the full suite (Sprint 0 + Core V1 + these new tests) and confirm all previously-passing tests still pass.

## 10. Definition of done

- `/v1/prospects/enrich` accepts a batch, returns immediately with job IDs, doesn't block on any pipeline run.
- `/v1/enrichment-jobs/{job_id}` reflects real in-progress state (`pending`/`enriching` observable before `ready`, not just a fast-forward to done).
- Submitting the same identity twice within its freshness window does not re-run enrichment.
- One failed lead in a batch doesn't affect the others.
- `pre-call` called directly (no pre-warming) still works exactly as it does today — zero regression.
- `pre-call` called for an already-warmed prospect skips the pipeline and returns instantly.
- All prior tests (Sprint 0 + Core V1) still pass, plus the new suite above.
- No Celery, Redis, Postgres, or Docker touched.

## 11. At completion, report

1. Changed-file list (new / edited)
2. Full test output (old suite + new suite, pass/fail counts)
3. One real run: submit a lead via `/enrich`, poll until `ready`, show the timestamps proving it was actually asynchronous (job created at T, still `pending`/`enriching` at T+1s, `ready` sometime after)
4. Confirmation that a direct `pre-call` call (no pre-warming) still works unchanged
5. Known limitations
