# Plan: Scale to 1000 Concurrent Users

## Context

The app currently runs as a single-process FastAPI with an in-memory job store, synchronous Claude API calls, and file-based persistence. The scalability evaluation identified hard ceilings at ~5–10 simultaneous estimations (thread pool) and a memory leak from unbounded `_JOBS` growth. The goal is to reach 1000 concurrent users.

---

## The Fundamental Constraint — Read This First

**1000 concurrent users ≠ 1000 concurrent Claude API calls.**

Realistic traffic distribution at 1000 simultaneous users:
- ~80% browsing history, reading reports, status polling → lightweight HTTP (trivially handled by async FastAPI)
- ~15% active in chat → Claude calls, ~10–30 s each
- ~5% submitting new estimations → Claude calls, ~30–90 s each

That means ~50–150 concurrent Claude API calls at peak — and **the Claude API itself is the hard ceiling**, not the server.

### Claude API throughput ceiling (Anthropic tiers)

| Tier | OTPM | Concurrent estimations (8k out tokens, ~60 s avg) |
|------|------|----------------------------------------------------|
| Tier 1 | 8,000 | **~1** |
| Tier 2 | 90,000 | **~11** |
| Tier 3 | 160,000 | **~20** |
| Tier 4 | 400,000 | **~48** |

At Tier 2 (most teams), only ~11 estimations can run simultaneously no matter how many servers you add. Infrastructure beyond that is idle for estimation work. The value of scaling infrastructure is handling the **web tier** (1000 connections, polling, chat history, saves) efficiently and making the job queue resilient — not running 200 Claude calls in parallel.

---

## Option Comparison

### Option A — Single VM + Docker Compose

**Stack**: 1× VPS (4–8 vCPU, 16 GB RAM), Docker Compose with nginx, 1 FastAPI container (async), 1 Redis container, 1+ ARQ worker containers.

| | |
|---|---|
| **Cost** | €40–120/month |
| **Ops complexity** | Low |
| **Horizontal scale** | ✗ (vertical only) |
| **Fault tolerance** | SPOF — VM dies, app dies |
| **Time to implement** | 1–2 days after code refactor |
| **User ceiling** | ~500 comfortable, 1000 with beefy VM |

**Verdict**: Good bootstrapping option. Fine for an internal tool or a small team. Unacceptable as a public product because of the single point of failure.

---

### Option B — Managed PaaS (Fly.io or Railway) ✅ RECOMMENDED

**Stack**: FastAPI app + ARQ worker service on Fly.io (or Railway), Upstash Redis (serverless, €0/idle), Supabase or Neon PostgreSQL.

| | |
|---|---|
| **Cost** | €80–250/month at 1000 users |
| **Ops complexity** | Very low — no cluster to manage |
| **Horizontal scale** | ✅ Auto-scales web + worker replicas |
| **Fault tolerance** | Multi-region on Fly.io, automatic restarts |
| **Time to implement** | 1 day after code refactor |
| **User ceiling** | 1000–5000 users comfortably |

How it works:
- `fly.toml` defines two services: `web` (FastAPI) and `worker` (ARQ)
- Both auto-scale: web scales by HTTP concurrency, worker scales by queue depth
- Upstash Redis: serverless, no idle cost, replicated
- Neon/Supabase PostgreSQL: managed, connection pooling included

**Verdict**: The right tool for a product at this stage. You get auto-scaling, redundancy, and zero K8s overhead. The team focuses on the product, not on cluster management.

---

### Option C — Docker + Kubernetes

**Stack**: Managed K8s cluster (GKE/EKS/AKS) with:
- `web` Deployment (3–5 FastAPI pods)
- `worker` Deployment (3–10 ARQ pods, HPA on queue depth)
- Redis (managed: Upstash/ElastiCache/Memorystore)
- PostgreSQL (managed: Cloud SQL/RDS/Supabase)
- Nginx Ingress + cert-manager

| | |
|---|---|
| **Cost** | €200–500/month (cluster overhead + nodes) |
| **Ops complexity** | High — requires K8s expertise |
| **Horizontal scale** | ✅ Unlimited, multi-region possible |
| **Fault tolerance** | ✅ Best-in-class (pod restarts, node failover) |
| **Time to implement** | 3–7 days after code refactor |
| **User ceiling** | 10,000+ users |

K8s is genuinely powerful but the overhead is real:
- Cluster management, node sizing, PodDisruptionBudgets, resource limits/requests, rolling deployments, liveness/readiness probes — all must be configured correctly
- The minimum viable K8s cluster costs ~€150–200/month before your app runs on it
- **At 1000 users it is almost certainly overkill** unless you already have K8s expertise or anticipate rapid growth to 5000+

**Verdict**: Correct choice at 5000+ users, or if you have a dedicated DevOps engineer. Premature at 1000 users.

---

### Option D — Cloud-native Serverless (Cloud Run + Cloud Tasks)

**Stack**: FastAPI on Google Cloud Run (HTTP tier), Cloud Tasks queue (estimation jobs), Cloud Run jobs or a long-running Cloud Run service for workers, Cloud Memorystore (Redis), Cloud SQL (PostgreSQL).

| | |
|---|---|
| **Cost** | €100–350/month at 1000 users (usage-based) |
| **Ops complexity** | Medium |
| **Horizontal scale** | ✅ Auto-scales to 0 on idle |
| **Fault tolerance** | ✅ Managed by Google |
| **Time to implement** | 2–4 days after code refactor |
| **User ceiling** | 1000–10,000+ |

Main gotchas:
- Cloud Run instances can be killed between requests — job state must be 100% in Redis, never local
- Cloud Tasks has a max task dispatch rate and payload size limit (1 MB)
- Networking between services (Cloud Run → Memorystore → Cloud SQL) requires VPC connector setup — non-trivial
- All-in on GCP: leaving later is painful

**Verdict**: Solid if you're already in GCP. More moving parts than Option B for similar outcomes.

---

## My Recommendation

> **Do the code refactoring first (all options require identical changes), then deploy on Fly.io (Option B). Migrate to Kubernetes only when you demonstrably exceed 3000–5000 users or if business requirements demand it.**

Rationale:
- The code refactor is the hard part (3–5 days). The deployment on Fly.io is 1 day. K8s deployment would be an additional 3–5 days for no extra user capacity at this scale.
- Fly.io auto-scales ARQ workers on queue depth, giving you the same elasticity as K8s HPA for this workload.
- The Claude API will be your capacity ceiling long before Fly.io is. Focus effort on rate limit handling and prompt caching rather than infrastructure.
- The architecture you build for Fly.io (async FastAPI + Redis + ARQ + PostgreSQL) is **100% portable to K8s** later — no re-architecture needed, only Dockerfiles and deployment manifests.

---

## Mandatory Code Changes (identical for all options)

These are non-negotiable regardless of deployment choice:

### 1. Async Claude client (`app/core/claude_client.py`)
- Replace `Anthropic` with `AsyncAnthropic` (SDK natively supports this)
- Replace `time.sleep()` retry backoff with `asyncio.sleep()`
- `call_claude()` becomes `async def call_claude(...)`
- `chat_with_claude()` becomes `async def chat_with_claude(...)`

### 2. Async GitHub client (`app/core/github_client.py`)
- Replace `httpx.Client` with `httpx.AsyncClient`
- `fetch_repo_summary()` becomes `async def fetch_repo_summary(...)`

### 3. Redis job store (replace `_JOBS` dict in `app/core/estimator.py`)
- Add `redis.asyncio` (from `redis[asyncio]` package)
- `create_job()`, `get_job()`, `update_job()` use `await redis.set/get` with JSON serialization
- Set TTL of 24 hours on each job key (`EXPIRE`)
- Remove the module-level `_JOBS` dict entirely

### 4. ARQ worker queue (replace `BackgroundTasks`)
- `run_estimation()` becomes an ARQ task function (already sync-compatible, but make async)
- `POST /api/estimate` enqueues the job via `await arq_pool.enqueue_job("run_estimation", ...)` instead of `background_tasks.add_task(...)`
- Worker process runs separately: `arq app.worker.WorkerSettings`
- ARQ settings define `max_jobs` (cap at Claude API tier limits, e.g. 10 for Tier 2)

### 5. Chat endpoint async (`app/api/routes.py`)
- `def chat(...)` → `async def chat(...)` (uses `await chat_with_claude(...)`)
- No longer needs thread pool; runs natively in event loop

### 6. PostgreSQL for saves (replace `saves/*.json`)
- Add `asyncpg` + `SQLAlchemy[asyncio]` or use `databases` library
- `saves` table: `save_id, name, status, created_at, updated_at, requirements_md, model_md, report_markdown, estimate_data (JSONB), financials_data (JSONB)`
- All functions in `app/core/saves.py` become async
- `list_saves()` uses SQL `ORDER BY updated_at DESC LIMIT 100` (no full scan)

### 7. Rate limiting (`slowapi`)
- Add `SlowAPI` middleware
- Limit `POST /api/estimate`: 5 requests/minute per IP
- Limit `POST /api/estimate/{id}/chat`: 20 requests/minute per IP

### 8. Prompt caching (quick win, no architecture change)
- Add `cache_control: {"type": "ephemeral"}` to the estimation model markdown block in the user prompt
- This caches the 3000-token model document across calls, reducing ITPM consumption by ~60% and cost by ~60% on repeated calls

---

## New Files Required

| File | Purpose |
|---|---|
| `app/worker.py` | ARQ `WorkerSettings` class, imports `run_estimation` as task |
| `app/db.py` | SQLAlchemy async engine + session factory |
| `app/models/db_models.py` | SQLAlchemy `Save` table definition |
| `Dockerfile` | Multi-stage build (web + worker use same image, different CMD) |
| `docker-compose.yml` | Local dev: web, worker, redis, postgres |
| `fly.toml` | Fly.io deployment config (web service) |
| `fly.worker.toml` | Fly.io deployment config (ARQ worker service) |

---

## Files Modified

| File | Change |
|---|---|
| `app/core/claude_client.py` | Async SDK, asyncio.sleep retries |
| `app/core/github_client.py` | httpx.AsyncClient |
| `app/core/estimator.py` | Redis job store, async functions, job TTL |
| `app/core/saves.py` | PostgreSQL via SQLAlchemy async |
| `app/api/routes.py` | async chat, ARQ enqueue, async saves |
| `app/config.py` | Add REDIS_URL, DATABASE_URL settings |
| `requirements.txt` | Add redis[asyncio], arq, asyncpg, sqlalchemy[asyncio], slowapi |

---

## Local Development Flow

```bash
# Start dependencies
docker-compose up -d redis postgres

# Run web server
uvicorn app.main:app --reload

# Run ARQ worker (separate terminal)
arq app.worker.WorkerSettings

# Env vars needed
ANTHROPIC_API_KEY=...
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/estimate
```

---

## Fly.io Deployment Flow

```bash
fly launch                        # creates fly.toml
fly redis create                  # Upstash Redis
fly postgres create               # managed PG
fly secrets set ANTHROPIC_API_KEY=...
fly deploy                        # web service
fly deploy -c fly.worker.toml     # worker service
```

Scale workers: `fly scale count worker=3`

---

## Verification

1. Submit 5 estimates simultaneously → confirm all poll correctly (no cross-job contamination from Redis isolation)
2. Kill the web process mid-estimation → confirm job survives in Redis and worker completes it
3. Restart app → confirm jobs created before restart are still visible via GET /api/saves
4. Submit 10 estimates at once → confirm ARQ queues them (not all start simultaneously) and processes them with `max_jobs` concurrency cap
5. Verify `GET /api/saves` uses SQL query and doesn't full-scan a directory
6. Load test with `locust` or `k6`: 1000 simulated users polling `/status`, reading `/saves` → target <200 ms p99 for read endpoints
7. Check prompt caching: verify `cache_creation_input_tokens` appears in Claude API response headers for repeated model text
