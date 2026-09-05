# Tech Stack — LOCKED

**Status:** Decided v1.0 — do not re-litigate without a concrete reason (new scale requirement, a provider going away, etc.). This is the stack for the Klesos-integration MVP and the operator dashboard that follows it.

---

## Backend

| Layer | Choice | Why |
|---|---|---|
| Language/framework | **Python 3.11 + FastAPI** | Already the MVP scaffold; async-native, typed via Pydantic, fast to iterate |
| Data validation / contract | **Pydantic v2** | `IntelligencePacket` and every API model already defined this way — this *is* the API contract |
| Database | **PostgreSQL** | Relational core (prospects, packets, call history) with room to grow |
| Vector/semantic memory | **pgvector** (Postgres extension) | Keeps the intelligence graph in the same database instead of standing up a separate vector store — one fewer moving part at this scale |
| Background jobs | **Redis + Celery** | Enrichment (site fetch, firmographics lookups) shouldn't block the API response once real providers are wired in; Celery is the boring, well-understood choice here |
| LLM provider | **Anthropic Claude (via `anthropic` SDK)**, behind the `intelligence/llm.py` abstraction already in the scaffold | One interface, swappable later; never call a provider SDK directly from reasoning code |
| Web extraction | **httpx + BeautifulSoup**, Playwright only when a target requires JS rendering | Covers the large majority of marketing/company sites cheaply |
| Observability | **Langfuse** for LLM call tracing, **OpenTelemetry** for the rest | Need to see what a reasoning call actually saw and returned, especially once heuristic fallbacks and real LLM calls are both live |

## Frontend (operator dashboard)

| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js (App Router) + TypeScript** | Matches the rest of the ORVYRA ecosystem's frontend direction; SSR where it helps, client components where it doesn't |
| Styling | **Tailwind CSS** | Already the working pattern for ORVYRA's existing frontend |
| Components | **shadcn/ui** | Unstyled-by-default primitives that don't fight the existing dark ORVYRA design system; also what the closest Dribbble reference used |
| Charts | **Recharts** | Only where the dashboard actually needs a chart (call volume, outcome trends) — most screens are cards/lists, not charts |
| Data fetching | **TanStack Query** | Standard, handles the packet/queue polling pattern cleanly |

## Infra / deployment

| Layer | Choice | Why |
|---|---|---|
| API hosting | **Railway** (MVP) | Fastest path from repo to a running API with a managed Postgres + Redis add-on; migrate to Fly.io/AWS only when there's a real scaling reason |
| Frontend hosting | **Vercel** | Default for Next.js, zero-config |
| Secrets | Provider env vars (Railway/Vercel), **never committed** | `ANTHROPIC_API_KEY`, DB URL, and any future firmographics API key follow the same rule already enforced in the ORVYRA space-economy repo: no credentials in source, ever |
| CI | **GitHub Actions** — lint + type-check + test on every PR | Minimal pipeline: `ruff` + `mypy` (or `pyright`) for Python, `tsc` for the frontend |
| Code review | **CodeRabbit** (GitHub App) on the repo — automated review on every PR alongside human review | Installed at repo level, config in `.coderabbit.yaml` |

## Explicitly rejected (and why, so this doesn't get re-asked)

- **Microservices** — one FastAPI app is enough at this stage; the ingestion/intelligence/interactions/api folder split already gives clean internal boundaries without the operational overhead.
- **A separate vector database (Pinecone/Weaviate/etc.)** — pgvector inside the existing Postgres instance is enough until proven otherwise.
- **GraphQL** — the two-endpoint contract (`pre-call`, `post-call`) is intentionally narrow; REST is the right shape for it.
