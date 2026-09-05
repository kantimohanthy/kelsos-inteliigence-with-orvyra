I'm deploying the ORVYRA backend to Railway for real. Railway's root directory is being fixed on my end to `orvyra/backend` — that part is handled outside your work. Your job is to make sure the code itself is actually production-deploy-ready, not just locally-runnable. Go through these in order, verify each, fix what's broken, don't skip any.

## 1. Port binding

Check `main.py` / wherever uvicorn gets started. Railway assigns a port dynamically via the `PORT` environment variable — it does NOT let you bind to a fixed port like 8009 in production. Confirm the app either:
- Has a `Procfile` or `railway.json`/`railway.toml` start command that reads `$PORT`, e.g. `uvicorn main:app --host 0.0.0.0 --port $PORT`, or
- If there's no start command file yet, create one — Railway needs to know how to actually start this app. Check what Railway's Railpack auto-detection expects for a Python/FastAPI project and match that convention, don't invent a nonstandard one.

Also confirm the host is `0.0.0.0`, not `127.0.0.1` — the app needs to accept connections from outside the container, not just localhost.

## 2. Environment variable loading in production

`llm.py` has `load_dotenv()` — confirm this doesn't break or error out when there's no `.env` file present (Railway injects env vars directly into the process environment, it doesn't create a `.env` file). `load_dotenv()` should just silently no-op if the file doesn't exist — verify that's actually true, don't assume it.

Confirm every place that reads `ORVYRA_API_KEY`, `ANTHROPIC_API_KEY`, and `DATABASE_URL` reads from `os.environ` (or via `os.environ.get()`), not from a hardcoded path or a dev-only config file.

## 3. Database migration must run on deploy, not just locally

Right now, `alembic upgrade head` is something you've been running manually. On Railway, this needs to happen automatically as part of the deploy — otherwise the app starts against a database with no schema and every request fails.

Add this to the deploy process — either as a Railway "release command" (check if `railway.json`/`railway.toml` supports a `releaseCommand` or pre-deploy hook) or by having the start command run the migration first, e.g. `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`. Pick whichever matches how Railway's Python project convention actually works — check Railway's own documentation for this rather than guessing, since getting this wrong means either migrations silently don't run, or they run on every restart when they shouldn't need to (Alembic handles "already migrated" gracefully, so re-running on every deploy is actually fine and safer than trying to detect whether it's needed).

## 4. requirements.txt completeness

Confirm `orvyra/backend/requirements.txt` has every package actually imported anywhere in the backend — specifically double-check `sqlalchemy`, `alembic`, `psycopg` (or `psycopg2-binary`), `pgvector`, and `python-dotenv` are all in there with no typos. A package that's installed locally in your dev environment but missing from `requirements.txt` will deploy fine and then crash on Railway, since Railway does a clean install from that file — this is a common silent failure mode, actually check every import statement against the file rather than assuming it's complete.

## 5. CORS

The dashboard will be deployed separately (Vercel, per the locked tech stack) and will call this API cross-origin. Check `main.py` for CORS middleware — if it's not there yet, add FastAPI's `CORSMiddleware` allowing the dashboard's origin. For now, allow `*` if there's no dashboard URL decided yet, but flag this in your report as something to lock down to the real dashboard domain once that's deployed — don't leave a wide-open CORS policy as a permanent state.

## 6. After I apply the Railway root-directory fix and it redeploys

Once I confirm the deploy succeeded on my end, do these checks against the LIVE Railway URL (I'll give you the URL):

1. `GET /health` — confirm it responds
2. Check Railway's deploy logs (I'll paste them, or if you have Railway CLI access, pull them directly) — confirm the Alembic migration ran and completed without error, not just that the app started
3. Run one real `POST /v1/prospects/enrich` against the live URL with a real company site, poll until ready, confirm the packet comes back correctly — this is the actual proof that Postgres, pgvector, the LLM extraction, and the whole pipeline all work together in the real production environment, not just locally

## Report back

1. What was already correct vs. what you had to fix, for each of items 1-5
2. The exact start command / release command you configured
3. Full `requirements.txt` diff if anything was added
4. Once I give you the live URL: the health check, migration log confirmation, and one real end-to-end packet from production

Do not touch anything related to Step 3 (critic pass) or the dashboard's own deployment — that's separate, later work. This is purely "make the already-working backend actually deployable and verified in production."
