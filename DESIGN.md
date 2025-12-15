# FinComp Design Guide (SRS + Architecture + AI Runbook)

## Status / Source of Truth (READ THIS FIRST)

This file is the **single source of truth** for how this repository must be shaped and how "production-ready" is defined.

- **If other docs conflict** (e.g. `README.md`, `INSTALL.md`, legacy OpenAlgo notes), treat them as **historical** unless they are explicitly referenced here as "authoritative".
- **Workspace hard rules** (must be followed by humans and AIs):
  - `AGENTS.md` (tooling rules: **use `uv`**, SQLAlchemy async, etc.)
  - This `DESIGN.md` (architecture and design constraints)

### Normative language

We use:

- **MUST**: non-negotiable requirement
- **SHOULD**: strongly recommended; deviation requires justification
- **MAY**: optional

## Project Overview

**Inspired by**: [OpenAlgo](https://github.com/marketcalls/openalgo)

**FinComp** is an algorithmic trading platform for Indian brokers. It provides:

- A web UI (dashboard + operations)
- REST APIs for integrations
- Real-time streaming (market data, execution updates, strategy state)
- An execution subsystem (OMS façade) and broker adapters

## Current Repo Reality vs Target Architecture (IMPORTANT)

This repo is in transition. A production-ready AI must **not guess** the frontend/back-end shape.

### Current state (what actually exists today in this repo)

- **Backend entrypoint**: `app/main.py` (FastAPI + ASGI).
- **UI**: Server-rendered templates (Jinja-like), under `app/web/frontend/templates/`.
- **Static assets**: `app/web/frontend/static/` (served via `StaticFiles` mounted at `/static`).
- **Styling build**: PostCSS/Tailwind/DaisyUI via `package.json` scripts (generates `static/css/main.css`).
  - **Node.js is build-time only**; it is not required at runtime if assets are pre-built.
- **Real-time**:
  - Socket.IO (`python-socketio`) is wired into the ASGI app (`socketio.ASGIApp`).
  - A separate WebSocket proxy server is started (port `WEBSOCKET_PORT`, default 8765) via background thread logic.
- **ZMQ**: Settings exist and multiple modules reference ZMQ; service-boundary enforcement is the target model.

### Target state (what this document designs toward)

- A service-oriented runtime with strict boundaries:
  - `Web` (FastAPI + UI + fan-out)
  - `Data Engine` (market data owner)
  - `Algo Engine` (strategy owner)
  - `Execution Engine` (OMS / state owner)
- Inter-service communication **only** via the message bus (ZMQ patterns).
- UI may evolve into a React/Vite SPA, but **that is a planned target**, not the current UI shape.

## Repository Orientation (so you don't have to guess)

- **App entrypoint**: `app/main.py`
- **Configuration**: `app/core/config.py` (Pydantic settings; `.env` loaded from repo root)
- **Env validation**: `app/utils/env_check.py` (enforces `.env` compatibility with `.sample.env`)
- **Template UI**
  - Routes: `app/web/frontend/routes/`
  - Templates: `app/web/frontend/templates/`
  - Static assets: `app/web/frontend/static/`
- **Backend APIs**: `app/web/backend/api/` (typically mounted under `/api/v1/...`)
- **Websocket/Socket.IO integration**: `app/utils/web/socketio.py` and `app/web/websocket/`
- **Tests**
  - Primary test suite lives under `test/` (see `TESTING.md`).
  - If `tests/` exists, treat it as legacy unless explicitly migrated/used in CI.

## Current Goals (near-term execution priorities)

These goals are aligned with `AGENTS.md` and guide what "production-ready" work should focus on first:

1. Make the frontend work reliably with the backend (current template UI, then SPA if/when migrated).
2. Restructure codebase to match the service boundaries and ownership rules in this document.
3. Implement missing functionality according to this design guide (with tests and CI passing).

## Technology Stack (authoritative targets)

- **Language**: Python **3.11+**
- **Backend Web Framework**: **FastAPI (async)** running as **ASGI**
  - **Framework constraint**: new web code MUST be ASGI-compatible; do not introduce new Flask/WSGI runtime paths.
- **Frontend (two-track)**
  - **Current**: Server-rendered templates + Tailwind/DaisyUI compiled by PostCSS
  - **Target**: React SPA/PWA (Vite), served as pre-built static files in production
- **Production runtime constraint**: **Python-only runtime** (frontend is pre-built; no Node.js required on the server)
- **Database**: SQLAlchemy **2.0 async**
  - **Now**: SQLite
  - **Later**: PostgreSQL
  - **Migrations**: Alembic (MUST add when models stabilize)
- **Messaging/IPC**: ZeroMQ (PyZMQ) using PUB/SUB and ROUTER/DEALER
  - PUB/SUB is best-effort; snapshots MUST exist for recovery
- **Scheduling**: APScheduler
- **Concurrency**: asyncio + multiprocessing for CPU-bound workloads
  - Rule: **CPU-bound strategy logic MUST NOT block the event loop**
- **Testing**: pytest (see `TESTING.md` for structure; this file defines architecture-level expectations)

## Frontend/Backend Delivery Model (Dev vs Production)

This repository currently ships a template-based UI, but is designed to support a SPA later. Both are described so an AI can act deterministically.

### Option A (CURRENT): Templates + static assets

- **Development**
  - Run FastAPI (ASGI).
  - Run `npm run dev` to watch/build CSS (PostCSS).
- **Production**
  - Build CSS once (`npm run build`) and serve static assets via FastAPI.
  - **No Node.js is required at runtime**.

### Option B (TARGET): React/Vite SPA

- **Development**
  - React dev server (Vite) runs separately for HMR.
  - FastAPI serves REST APIs + WebSockets.
  - Vite proxies API/WebSocket calls to FastAPI.
- **Production**
  - `vite build` produces static assets.
  - FastAPI serves: static SPA assets + REST + WebSockets.
  - **No Node.js is required at runtime**.

Architecture summary:

```text
Option A (Current):
Browser ⇄ FastAPI (templates + REST + Socket.IO/WebSocket)
         ↳ /static (pre-built assets)

Option B (Target):
Dev:     React (Vite) ⇄ FastAPI (REST + WebSocket)
Prod:    React build → static files → served by FastAPI
```

## AI Implementation Runbook (How to use this doc to reach production-ready)

If you are an AI model working on this repository, follow this order **without asking for confirmation**:

1. **Establish ground truth**
   - Identify entrypoints (`app/main.py`, process model, background services).
   - Identify UI mode in use (templates vs SPA).
   - Identify current message bus usage and where boundaries are violated.
2. **Make the system runnable end-to-end**
   - `uv sync`
   - `uv run pytest`
   - Ensure the app starts with a clean `.env` derived from `.sample.env`.
   - Start dev server (recommended):
     - `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
   - If using the current template UI, build CSS:
     - `npm install`
     - `npm run dev` (watch) or `npm run build` (one-shot)
3. **Harden for production**

- Enforce "one owner per domain" (Web/Data/Algo/Execution).
- Ensure background services are not duplicated under multi-worker servers.
- Add/verify health endpoints, readiness checks, and graceful shutdown.
- Add/verify DB migrations (Alembic) and deterministic startup.
- Remove/contain legacy/unused framework paths (e.g., Flask-era modules) so they cannot break prod.

4. **Prove correctness**

- Add tests for all changes (unit + integration where appropriate).
- Update this `DESIGN.md` if new constraints or contracts are introduced.

## Phased Implementation Strategy

To ensure rapid development while maintaining architectural integrity, the project will follow a **"Monolithic First"** approach that strictly enforces the distributed architecture patterns.

### Phase 1: Logical Split (Current Phase)

- **Architecture**: Single machine, **multi-service** with strict boundaries.
- **Two supported run-modes**:
  - **Phase 1A (Dev-first, simplest)**: One process (FastAPI) + background `asyncio` tasks for Data/Algo/Execution.
  - **Phase 1B (Performance-first, recommended)**: **Web, Data, Algo, Execution run as separate OS processes** on the same machine.
- **Boundary Rule (MANDATORY)**: All cross-service calls MUST use the message bus (PUB/SUB or ROUTER/DEALER). Direct calls across service boundaries are **FORBIDDEN**.
  - Phase 1B transport uses ZMQ over `ipc://` (preferred) or loopback `tcp://`.
  - `inproc://` is only applicable when components share the same process (Phase 1A).
- **Goal**: Get the system working end-to-end now, while allowing an incremental move to a high-performance single-host multi-process layout without redesign.

### Phase 2: Physical Split (Future)

- **Architecture**: Distributed Multi-Process.
- **Transition**: Since the message bus interface enforces boundaries, Phase 2 mostly changes process entry points and bus URLs. Core logic should remain unchanged; only operational concerns (restarts, resource limits, scaling) should change.

### Performance-first Process Model (Recommended)

For lowest latency and best isolation, the recommended runtime is a **Supervisor** that starts services as OS processes:

- **Supervisor process**:

  - Starts and monitors: **Data Engine**, **Algo Engine**, **Execution Engine**, and **Web (FastAPI)**.
  - Restarts crashed child processes with backoff.
  - Owns shutdown ordering (stop strategies → stop execution → stop data → stop web).
  - Publishes a unified health/readiness status (optional).

- **Web (FastAPI) process**:

  - Runs REST + WebSocket fan-out only (no tick ingestion, no strategy execution).
  - On startup: connects to ZMQ endpoints and warms required snapshots.
  - On shutdown: closes sockets cleanly.

- **Why not start OS processes from FastAPI `lifespan` (Important)**:

  - Production servers often run **multiple web workers** (e.g., `uvicorn --workers N` / gunicorn). Each worker would run `lifespan` and accidentally start **duplicate** Data/Algo/Execution processes.
  - Therefore:
    - **Preferred**: Supervisor owns process startup (web `lifespan` does not spawn other services).
    - **Allowed for local dev only**: web `lifespan` may spawn other service processes **only when explicitly enabled** and when web worker count is forced to **1**.

- **Scaling knobs**:
  - Web: scale with additional uvicorn workers **only when Data/Algo/Execution are external processes** (Supervisor mode).
  - Algo: scale strategy execution with additional worker processes (CPU-bound isolation) under the Algo Supervisor.
  - Data: typically 1 process per broker connection group; shard by broker/exchange if needed.

## System Architecture

The application is structured into **four main independent logical services** (running as async tasks in Phase 1) to ensure stability, fault isolation, and performance.

### Service Ownership (Single Source of Truth)

To prevent duplicated responsibilities and circular dependencies, each domain has a single owner:

- **Web Server (`app/web`)**: Auth, REST API, UI aggregation, WebSocket fan-out. **Not** the owner of trading or market-data state.
- **Data Engine (`app/data`)**: Market-data ingestion, subscription registry, normalization, market-data snapshots/history. **Owner of market-data state**.
- **Algo Engine (`app/algo`)**: Strategy lifecycle + risk controls. **Owner of strategy state** and **signal generation**.
- **Execution Engine (`app/core/execution`)**: OMS gateway, broker execution, reconciliation, persistence. **Owner of orders/trades/positions/holdings/margins** as system-of-record (with broker reconciliation).

Broker Manager is a **library** that provides broker-specific adapters. It is **not** a system-of-record.

### 1. Web Server Service (`app/web`)

- **Host**: FastAPI (REST + Socket.IO/WebSocket) and static file server.
- **UI delivery (two-track)**:
  - **Current**: Template UI under `app/web/frontend/templates/` + static under `app/web/frontend/static/`.
  - **Target**: React/Vite build output served as static files by FastAPI.
- **Role**: Serves the UI, exposes REST APIs, and streams real-time data to the frontend (Socket.IO/WebSockets).
- **Interaction**:

  - **Requests Snapshots**:
    - Market-data snapshot/history from **Data Engine** (ROUTER/DEALER).
    - Account snapshots (orders/positions/trades/holdings/margins) from **Execution Engine** (ROUTER/DEALER).
  - **Subscribes to Streams**:
    - Market-data stream from **Data Engine** (PUB/SUB).
    - Execution stream from **Execution Engine** (PUB/SUB) to keep UI live.
    - Strategy state stream from **Algo Engine** (PUB/SUB).
  - **Control**: Publishes control commands (deploy/undeploy/kill) to Algo Service via PUB/SUB.

- **WebSocket Performance Guidelines**:
  - **One WebSocket connection per user** (recommended).
  - **Batch + throttle** outbound updates (e.g., 200–1000ms cadence) to avoid UI/render overload and network overhead.
  - Prefer sending **compact, normalized payloads** (e.g., per-symbol LTP + change + OHLC) and let the UI compute presentation (colors, flashes, etc.).

### 2. Data Engine Service (`app/data`)

- **Host**: Asyncio Event Loop.
- **Role**: Dedicated service for ingesting, normalizing, and serving market data.
- **Concrete Responsibilities**:
  - Maintain the **subscription registry** (symbol/index/watchlist → resolved symbol set).
  - Manage broker market-data connections via Broker Manager (DATA capability).
  - Normalize raw broker ticks into canonical `MarketData` payloads.
  - Publish market-data updates via PUB/SUB (best-effort).
  - Serve authoritative **snapshots/history** via ROUTER/DEALER (used for UI initialization and gap recovery).
- **Subscription Registry (Refined / Concrete)**:
  - **In-memory registry (hot path)**:
    - Stores the active subscription set with a uniqueness constraint per `(broker?, exchange, symbol, mode)`.
    - Tracks **who requested** the subscription (UI watchlists, strategies, indexes) using reference counts or source sets.
    - Must be concurrency-safe (Phase 1: `asyncio.Lock`; Phase 2: still single owner = Data Engine).
  - **Database persistence (durability)**:
    - Every subscription add/remove/update is persisted to DB.
    - DB is used for **restart recovery**, audits, and diagnostics (not for streaming reads).
    - On startup, Data Engine restores the subscription registry from DB and reconciles with broker streaming state.
- **Subscription Management Rules (Refined)**:
  - Subscriptions may be requested by:
    - **Symbol**: `exchange + symbol + mode`
    - **Index**: `index_id + mode` (Data Engine expands index → concrete symbols)
    - **All** (future): explicitly discouraged unless the broker supports it safely.
  - **No duplicate subscriptions**:
    - Multiple requests for the same `(exchange, symbol, mode)` increment a reference count / add a requester.
    - The broker stream is created once; consumers subscribe locally via PUB/SUB.
  - **Unsubscribe semantics**:
    - A symbol is unsubscribed from the broker only when its reference count reaches zero.
    - If a symbol is referenced via an Index subscription, removing an individual symbol subscription must **not** stop the broker stream (it remains referenced by the index).
- **Broker Limits + Fallback (Refined)**:
  - Data Engine enforces broker feed limits (per broker and/or per connection) before subscribing.
  - If the preferred broker is at limit or unavailable, Data Engine selects a fallback via:
    - `BrokerManager.get_fallback_broker(broker_id, capability=DATA)`
  - Fallback rules MUST be deterministic:
    - Prefer same exchange coverage + lowest current subscription load.
    - Emit an event whenever a subscription is moved to a fallback provider.
- **Event Bus (System-Wide Notifications, owned by Data Engine)**:
  - Data Engine emits system notifications as PUB/SUB events (in addition to high-frequency `md.*` ticks).
  - **Purpose**: lifecycle + low-frequency coordination (start/stop/error/subscription changes), not tick delivery.
  - **Canonical events (examples)**:
    - `DATA_STREAMING_STARTED`: payload includes provider/broker id(s), modes, and optionally the restored subscription count.
    - `DATA_STREAMING_STOPPED`: payload includes provider/broker id(s) and stop reason.
    - `DATA_STREAMING_ERROR`: payload includes provider/broker id(s), error code, and summary.
    - `SUBSCRIPTION_UPDATED`: payload includes what changed (added/removed/moved-to-fallback).
    - `MARKET_DATA_UPDATE` (optional): low-frequency heartbeat/summary for observability.
  - **Mechanism**:
    - Data Engine publishes `DATA_STREAMING_STARTED` when streaming is active and stable.
    - Algo Engine (and others) subscribe on startup; when the event fires, Algo Engine triggers deployment transitions (e.g., `WAITING_FOR_DATA` → `RUNNING`).
- **Details**: For detailed architecture, components, and data formats, please refer to [DATA_Service.md](DATA_Service.md).

### 3. Algo Engine Service (`app/algo`)

- **Host**: Asyncio Event Loop (Phase 1).
- **Role**: Manages Strategy execution.
- **Terminology**: **Algo Supervisor**.
- **Internal Architecture**:
  - **Workers (Strategies)**:
    - Implemented as `asyncio.Task`s.
    - **Input**: Subscribes to market-data topics via ZeroMQ SUB (canonical topic schema defined below).
    - **Logic**: Runs strategy logic.
    - **Output**: Generates **Signals**.
  - **Algo Supervisor**:
    - **Input**: Receives Signals from Workers.
    - **Risk Management**: Checks global/strategy limits.
    - **Position Sizing**: Calculates quantity.
    - **Output**: Publishes approved orders via PUB/SUB (topic family `orders.signal.*`).
    - **Feedback**: Subscribes to execution reports (topic family `orders.exec_report.*`) to update strategy state.

### 4. Execution Engine Service (`app/core/execution`)

- **Host**: Asyncio Event Loop.
- **Role**: Order Management System (OMS) + single execution gateway. This service is the **central facade** for all order/account state (orders, trades, positions, holdings, margins).
- **Concrete Responsibilities**:
  - **Inputs**:
    - Subscribes to validated **Signals** from Algo Engine (topic family `orders.signal.*`).
    - Receives UI-triggered actions via ROUTER/DEALER (cancel/square-off only; manual buy/sell is disabled).
  - **Validation & Safety**:
    - Validates signals against broker rules and global safety rules (e.g., max qty, allowed instruments, trading window, kill-switch state).
    - Enforces **idempotency** using `(correlation_id, source)` so duplicate messages do not place duplicate orders.
  - **Broker Routing (Deterministic)**:
    - Selects broker for each order using explicit routing rules:
      - Prefer the broker configured for the strategy/account.
      - If a position already exists, route closing orders to the same broker where the position resides.
    - **No automatic ORDER fallback** by default (trading fallback is dangerous). Only retries on the same broker with bounded backoff.
  - **Execution**:
    - Converts internal `OrderRequest` → broker-native request and submits via Broker Manager (ORDER capability).
    - Runs an async order lifecycle tracker (PLACED → PARTIAL → FILLED/CANCELLED/REJECTED).
  - **System of Record (State Registry)**:
    - Maintains authoritative **in-memory** registries for:
      - Orders (by `order_id`, by `broker_order_id`, by `strategy_id`)
      - Trades
      - Positions
      - Holdings
      - Margins
    - Every state transition is persisted to DB (durability + restart recovery + audit).
    - On startup, restores state from DB and performs broker reconciliation to correct drift.
  - **Reconciliation (Required for robustness)**:
    - Periodically fetches broker-native order/trade/position snapshots and reconciles:
      - Missing fills / late reports
      - Cancel/Reject drift
      - Position quantity/avg price mismatches
    - Emits a reconciliation event when corrections are applied.
  - **Outputs (Streaming + Snapshot)**:
    - Publishes execution lifecycle events via PUB/SUB (topic family `orders.exec_report.*`).
    - Publishes low-frequency account summary events (optional) for UI observability (e.g., `account.snapshot_summary.*`).
    - Serves snapshots/actions via ROUTER/DEALER:
      - Snapshot endpoints: orders, trades, positions, holdings, margins (with pagination/filtering).
      - Action endpoints: cancel order(s), square-off position(s), global kill-switch (if enabled).
- **Event Bus (System-Wide Notifications, owned by Execution Engine)**:
  - Purpose: lifecycle + low-frequency coordination/observability (not broker tick delivery).
  - Canonical events (examples):
    - `EXECUTION_ENGINE_STARTED`: payload includes active broker ids and restored state counts.
    - `EXECUTION_ENGINE_STOPPED`: payload includes reason.
    - `EXECUTION_ENGINE_ERROR`: payload includes error code and summary.
    - `ORDER_STATE_UPDATED`: payload includes `order_id`, status, and broker ids.
    - `POSITION_UPDATED`: payload includes `symbol`, qty, avg_price, and P&L fields if available.
    - `MARGIN_UPDATED`: payload includes utilized/available.
    - `RECONCILIATION_APPLIED`: payload includes what was corrected.

## Data Sharing & Concurrency

### ZeroMQ (The "Nervous System")

We use **ZeroMQ (ZMQ)** for service-boundary messaging. ZMQ is **not** a cache/database and PUB/SUB is **best-effort**.

Therefore, all real-time planes MUST be designed as:

- **Streams (PUB/SUB)**: best-effort, high-frequency updates (may drop).
- **Snapshots (ROUTER/DEALER)**: authoritative state used for initialization and recovery.

- **Pattern 1: Pub/Sub (Real-time Data & Signals)**

  - **Transport**: TCP (Localhost) or IPC.
  - **Flows**:

    - `Market Data`: Data Engine (PUB) -> Algo Engine (SUB) & Web Server (SUB).
      - **Topic schema (canonical)**: `md.{broker}.{exchange}.{symbol}.{mode}`
        - Examples: `md.fyers.NSE.NIFTY50.QUOTE`, `md.zerodha.NSE.RELIANCE.LTP`
        - `mode`: `LTP` | `QUOTE` | `DEPTH`
    - `Signals`: Algo Engine (PUB) -> Execution Engine (SUB) (topic family `orders.signal.*`).
    - `Execution Reports`: Execution Engine (PUB) -> Algo Engine + Web (SUB) (topic family `orders.exec_report.*`).
    - `Strategy State`: Algo Engine (PUB) -> Web (SUB) (topic family `strategy.state.*`).
    - `Control`: Web (PUB) -> Algo (SUB) (topic family `control.strategy.*`).

  - **Reliability Rule (MANDATORY)**:
    - Every streamed message MUST include a **monotonic `seq` per topic**.
    - Consumers MUST detect gaps and recover by requesting an authoritative snapshot over ROUTER/DEALER.

- **Pattern 2: Router/Dealer (State/Snapshots/History)**
  - **Flows**:
    - `Market Snapshot/History`: Web/Algo (DEALER/REQ) -> Data Engine (ROUTER).
    - `Account Snapshot/Actions`: Web/Algo (DEALER/REQ) -> Execution Engine (ROUTER).
      - **Use Case**: Dashboard initialization, gap recovery, and UI actions (cancel/square-off).
      - **Benefit**: **ROUTER** socket allows concurrent requests without blocking.

### Concurrency Strategy

- **Phase 1 (Monolith)**: All services run as **Asyncio Tasks** within the main FastAPI process.
- **Phase 2 (Distributed)**: Services move to separate processes. Algo Workers may move to `multiprocessing` for CPU isolation.

## Key Workflows

- **Authentication**:
  - **Centralized Auth**: The **Web Server Service** (FastAPI) is the **only** component responsible for performing user and broker authentication (e.g., Fyers OAuth, TOTP).
  - **Token Storage**: Tokens must never be returned to the frontend and must not be logged.
  - **Token Distribution (Concrete & Safer)**:
    - Tokens must not be broadcast via PUB/SUB.
    - Other services obtain tokens by reference: Web stores tokens in DB and issues a `broker_session_id`, then Data/Execution request token material over ROUTER/DEALER (local-only in Phase 1).
  - **Stateless Brokers**: Broker Adapters in other services (Data, Execution) are initialized _with_ valid tokens. They do **not** perform interactive login flows. If refresh is required, they request it via Web or emit a `BROKER_AUTH_REQUIRED` event.
  - **Flow**:
    1. User logs in via Web UI -> Web Server performs OAuth with Broker.
    2. Web Server receives Access Token.
    3. Web Server publishes `BROKER_AUTH_SUCCESS` event (or updates DB).
    4. Data/Algo Services receive token/notification and initialize their Broker Adapters.
- **Order Management**: Unified order placement API that routes requests to the specific broker adapter.
- **Market Data**: Websocket connection to brokers to receive tick data, which is then broadcasted via ZeroMQ.
- **Telegram Integration**: (Future Scope) Two-way communication via Telegram for alerts.

## Development Guidelines

- **Environment management (MANDATORY)**:
  - Use `uv` (`uv sync`, `uv run`, `uv add`); do not introduce `requirements.txt`.
  - Python version target is **3.11+** (match `pyproject.toml`).
- **Async/Await**: The codebase heavily relies on `asyncio`. Ensure all I/O bound operations are awaited.
- **DB access (MANDATORY)**:
  - Use **SQLAlchemy 2.0 async** patterns only.
  - Treat SQLite as dev/local; keep schemas portable to PostgreSQL.
- **Dependency injection & boundaries**:
  - Prefer DI/factories; avoid hidden globals for service state.
  - Keep "one owner per domain" and don't cross-call other services directly (use the message bus).
- **Code quality gates (MANDATORY)**:
  - Format: `uv run ruff format --check .`
  - Lint: `uv run ruff check .`
  - Type checks: `uv run mypy .` (or project-scoped targets)
- **Testing (MANDATORY)**:
  - Run: `uv run pytest`
  - Follow fixture rules from `AGENTS.md` (global vs module vs file fixtures).
  - Add tests for new features/bug fixes (unit + integration when needed).

### Forbidden patterns (do not do these)

- Starting Data/Algo/Execution processes from FastAPI `lifespan` while also running multiple web workers.
- Direct in-process calls across service boundaries (e.g., Web calling Data Engine functions directly).
- Logging or returning broker tokens/credentials to the frontend.
- Introducing new Flask/WSGI request handlers in the production path.
- Adding runtime Node.js requirements (Node is build-time only for assets).

## Production Readiness (Definition of Done)

"Production-ready" for this repo means **all** items below are satisfied (or explicitly marked as out-of-scope with rationale):

### Runtime & process model

- **No duplicate background services**:
  - If Data/Algo/Execution are started from FastAPI `lifespan`, the web server MUST run with **one worker**.
  - If the web server is scaled to multiple workers, Data/Algo/Execution MUST be external processes (Supervisor mode).
- **Graceful shutdown**: all sockets/threads/tasks MUST close cleanly on SIGTERM/SIGINT.
- **Deterministic startup**: startup must fail fast with actionable errors when config is invalid.

### Configuration & secrets

- **No hardcoded production secrets**:
  - Any default secrets in settings MUST be treated as dev-only and MUST be overridden via environment in production.
- **.env contract**:
  - `.sample.env` is the reference template.
  - `.env` must be versioned via `ENV_CONFIG_VERSION` and validated at startup (see `app/utils/env_check.py`).
  - **Minimum required variables (practical)**:
    - `ENV_CONFIG_VERSION`
    - `APP_ENV`, `APP_DEBUG`, `APP_HOST_IP`, `APP_PORT`
    - `APP_KEY`, `API_KEY_PEPPER`
    - `DATABASE_URL`
    - `WEBSOCKET_HOST`, `WEBSOCKET_PORT`, `WEBSOCKET_URL`
    - `BROKER_API_KEY`, `BROKER_API_SECRET`, `REDIRECT_URL`, `VALID_BROKERS`
  - **Legacy naming note**: some validators/settings still reference historical names (e.g., `FLASK_*`). Until the codebase completes its renaming, production configs MUST satisfy the currently enforced validation rules.
- **Secret handling**:
  - Broker tokens/credentials MUST never be sent to the frontend and MUST never be logged.
  - Secrets MUST be loaded via env/secret manager and not committed to git.

### Security baseline

- **TLS**: production deployments MUST terminate TLS (reverse proxy or platform TLS).
- **Cookies**: session cookies MUST be `Secure` under HTTPS and have appropriate SameSite policy.
- **CSRF**: state-changing browser endpoints MUST have CSRF protection.
- **Rate limiting**: public endpoints (auth, APIs, webhooks) MUST be rate-limited.
- **Headers**: CSP, Referrer-Policy, Permissions-Policy MUST be set appropriately (see settings in `app/core/config.py`).

### Observability & operations

- **Health/readiness endpoints**:
  - MUST expose a stable health endpoint for orchestration.
  - NOTE: `docker-compose.yml` currently expects `/monitoring/health` — either that route MUST exist or the healthcheck must be updated.
- **Structured logging**:
  - All logs MUST include correlation/request identifiers for tracing across services.
- **Metrics (SHOULD)**:
  - Provide basic counters/timers for request latency, broker connectivity, streaming lag, and error rates.

### Data durability

- **Migrations**: Alembic MUST exist before "real production" (when schema changes are expected).
- **Persistence**: Execution Engine must persist state transitions and be able to restore/reconcile after restart.

## Framework Decision Note (Django vs FastAPI)

**Decision**: FastAPI is the preferred backend framework for this project because it is a better fit for **low-latency, WebSocket-heavy, high-concurrency** real-time dashboards.

| Aspect              | FastAPI         | Django            |
| ------------------- | --------------- | ----------------- |
| WebSockets          | Native & simple | Requires Channels |
| Performance         | High            | Lower             |
| Complexity          | Low             | Higher            |
| Real-time streaming | Excellent       | Not ideal         |

Django can still be used in the future for **admin/internal tools** if needed, but **not** for the real-time market data plane.

## System Requirements (**RECOMMENDED DESIGN PATTERNS**)

- Web interface (Progressive Web App - PWA). It MUST be real-time (1s latency) and have following functionality.
  - Dashboard with following information.
    - Market Summary with following information.
      - NIFY 50, NIFTY 200, NIFTY 500, BANKNIFTY, NIFTY MIDCAP, NIFTY SMALLCAP, etc.
      - **Real-time Data**: Must stream Change, Change%, and OHLC (Open, High, Low, Close).
      - Advancers and Decliners (Simple count display, e.g., "30 Adv / 20 Dec").
      - Top Gainers and Losers with percentage.
      - Top Volume Traded with percentage.
      - Top Value Traded with percentage.
      - Top OI Traded with percentage.
    - Counter of deployed strategies.
      - Counter of open positions amount by strategy.
      - P&L percentage and amount by strategy.
    - Total Today P&L Realized and Unrealized.
    - Total Open Positions (today and previous day) with quantity and average price and profit/loss percentage, profit/loss amount.
    - Total Utilised Margin and Margin Available
    - Recent 5 Orders (Exactly the last 5 orders regardless of status) with info like symbol, quantity, average price, buy/sell, etc, strategy id, timestamp, etc.
  - Orders Page:
    - Showing all order segrageted as per status (open, complete, cancelled, rejected).
    - Showing all position segrageted as per status (open, closed).
    - Showing all trade which is executed order with info like average price, quantity, buy/sell, etc, strategy id, timestamp, etc.
  - Positions Page:
    - Showing all position segrageted as per status (open, closed).
    - Showing all trade which is executed order with info like average price, quantity, buy/sell, etc, strategy id, timestamp, etc.
  - Holdings Page:
    - Showing all holdings with info like symbol, quantity, average price, profit/loss percentage, profit/loss amount accorss all strategies (which are deployed) and brokers (which are active).
  - Strategy Page:
    - Deploy new strategy functionality.
      - User selects from a **predefined, hardcoded list** of strategies.
      - Future Scope: Python file upload capability.
    - Showing all strategy with info like strategy id, strategy name, strategy type, strategy status, strategy p&l percentage, strategy p&l amount, total amount of open positions by strategy, total amount of closed positions by strategy, total amount of trades by strategy, total amount of orders by strategy, strategy timestamp, etc.
    - **Kill Switch**:
      - **Hard Kill**: Cancel ALL pending orders + Close ALL open positions + Undeploy ALL strategies.
      - **Soft Kill**: Cancel ALL pending orders + Undeploy ALL strategies (Positions remain open).
  - Settings Page:
    - Telegram Integration (Future Scope):
      - Two-way communication via Telegram for alerts.
      - Showing all telegram commands with info like command, description, usage, etc.
    - Broker Integration:
      - Showing all broker with info like broker id, broker name, broker type, broker status, last checked timestamp, etc.
      - Broker connection status with info like broker id, broker name, broker type, broker status, last checked timestamp, etc.
      - Showing all settings with info like api key, api secret, api url, etc.
- Backend should have following functionality.

  - Web Server Module (frontend and backend):
    This module contains all web server functionality for the frontend and backend.
    - **Backend**: FastAPI (REST + WebSockets, async).
    - **Frontend (two-track)**:
      - **Current**: Template UI + static assets served by FastAPI.
      - **Target**: React (Vite build output) served as static files by FastAPI in production.
    - **Production constraint**: Python-only runtime (frontend is pre-built; no Node.js required on the server).
    - Routes to serve the frontend (templates today; SPA entry + static assets in target).
    - API for frontend.
    - API for orders, account, positions, trades, holdings, strategies, settings, etc.
    - **Order Management**:
      - **Manual Trading is DISABLED**. Users cannot place new manual Buy/Sell orders.
      - Allowed Actions: **Cancel** existing orders, **Square Off** (Close) existing positions.
    - WebSocket for real-time data streaming to frontend with async functionality.
      - Implement WebSocket endpoints in FastAPI and manage connect/disconnect with app lifecycle.
      - Optional: use `python-socketio` if we later need Socket.IO semantics/fallbacks.
      - Connect/Disconnect web socket server with web server lifecycle.
      - **Subscribe to ZeroMQ** to receive real-time ticks and forward to frontend clients.
    - services required for backend functionality.
  - Core Module:
    - This module have all code related to core functionality of the application which is common to all modules. Such as following functionality;
      - Database Management:
        - Database connection using SQLAlchemy 2.0.
        - Database session using AsyncSession.
        - Database models.
        - Database operations.
        - Database transactions.
        - Database queries using SQLAlchemy 2.0.
      - Logging Management:
        - This module will only provide logging functionality to all modules which use for debugging and monitoring. It is not for mobule specific logging such as Strategy Manager Logs.
        - Handling database operations for logs.
      - Messaging Contracts (Shared):
        - Canonical topic naming utilities.
        - Canonical message envelope schema and typed payload models.
        - Error model and request/reply correlation helpers.
        - NOTE: Market-data subscription registry and fallback logic are owned by **Data Engine** (not Core).
  - Broker Manager Module:
    This module contains the core logic for interacting with brokers. It is designed as a **library** to be instantiated by specific processes (Data Engine, Execution Engine).

    - **Authentication**: Uses **pre-authenticated tokens** provided by the Web Server. Does not handle interactive login flows (e.g., OTP entry) directly.
    - **Authorization**: Validates that the provided token has the necessary permissions (e.g., Trading vs Data only).
    - **State Management**: Broker connection status is shared across processes using **ZeroMQ PUB/SUB**.
      - `Data Engine` publishes data connection status.
      - `Execution Engine` publishes trade connection status.
      - `Web Server` subscribes to these topics to maintain a real-time registry for the UI.
    - Broker Manager Class:

      - It is registry of all brokers and their connection status.
      - All functionality related to brokers should be managed by Broker Manager.
      - Manage all brokers and their connection status.
      - Data Streaming Adapter:
        - Provides a standardized interface for the Data Engine to consume.
        - Handles the specific protocol details of the connected broker (e.g., WebSocket management).
      - Broker Registry & Filtering:
        - `get_active_brokers(capability=None)`: Returns brokers matching the requested capability (e.g., only DATA brokers).
        - `get_fallback_broker(broker_id, capability)`: Intelligent fallback finding another broker with the **same** capability. **Note: Fallback is only supported for DATA capability.**
      - Order/Account Adapter Functionality (Library Only):

        - Place/Cancel/Modify orders for a single broker instance (broker-native API).
        - Fetch broker-native order/trade/position/holding snapshots for **reconciliation**.
        - NOTE: Global consolidated books and OMS rules are owned by **Execution Engine** (system-of-record).
        - Broker Registry:
          - Register new broker.
            - Each registered broker should have fallback broker id in case of any error.
          - Unregister broker.
          - Get all brokers.
          - Get broker by id.
          - Get broker by name.
          - Get broker by type.
          - Get broker by status.
          - Get broker by last checked timestamp.
        - Data Streaming Provider (Broker) functionality:
          - Get broker for data streaming.
          - Fallback mechanism to get data from other active brokers if one broker is not available.
          - This is only provide active brokers which setup for providing data streaming.

      - **Brokers (sub-module)**:
        To improve modularity and separation of concerns, new broker implementations MUST follow the split-service architecture defined in `app/core/brokers/base.py`.

        - **Authentication (`BaseBrokerAuth`)**:

          - **Consumer**: Web Server Service.
          - Responsible solely for login mechanisms (OAuth, TOTP, etc.) and returning tokens.
          - Configured via `AuthConfig` Pydantic models.

        - **Account (`BaseBrokerAccount`)**:

          - **Consumer**: Execution Engine Service.
          - Responsible for Order Management (Place/Cancel/Modify) and Account State (Positions/Holdings/Funds).
          - Methods: `place_order`, `get_positions`, `get_funds`, etc.

        - **Data (`BaseBrokerData`)**:

          - **Consumer**: Data Engine Service.
          - Responsible for Market Data (Quotes, History, Depth).
          - Methods: `get_quotes`, `get_history`, `get_depth`.

        - **Legacy Note**: Older broker implementations (e.g., in `app/web/broker`) may still follow the monolithic `Broker` class pattern. These SHOULD be refactored to the new modular structure over time.

      - Broker Capability Enum (Legacy/Transition):

        - `ORDER`: Can execute trades.
        - `DATA`: Can stream real-time market data.
        - `BOTH`: Supports both.

      - Broker State (Legacy/Transition):
        - `is_active`: Boolean, master switch.
        - `capabilities`: List of `BrokerCapability`.
        - `connection_status`: Connected/Disconnected.
        - `data_streaming_status`: Streaming/Idle (if DATA capability exists).
      - Broker (Legacy Monolithic Base Optional):
        This is the base class for legacy brokers. Future implementations should use the Modular Architecture.
        - Get broker id, name, type, status.
        - Order Management Functionality (Place, Cancel, Modify).
        - Get books (Order, Trade, Position, Holding).
        - authenticate, disconnect, get real-time data.

  - Algo Module:
    This module have all code/modules/packages related to algo trading functionality. Such as following;
    - Strategy Manager Module (sub-module):
      This module have all code related to managing strategies. Base strategy class, Strategy Manager Class, etc.
      - Strategy Manager Class: It act as a registry of all strategies and their status. It should have following functionality.
        - Register new strategy.
        - Unregister strategy.
        - Get all strategies.
        - Get strategy by id.
        - Get strategy by name.
        - Get strategy by status.
        - Get strategy by type.
        - Deploy/Undeploy strategy (partialar strategy or all strategies).
        - Get strategy stats.
        - Notify all strategies on receiving new data from the Data Engine stream.
      - Logs Management Functionality for strategies:
        - Logs for all trigger points generated by strategies with info such as strategy id, symbol, price, single type or all types.
        - Handling database for logs.
      - Base Strategy Class: It is base class for all strategies. It should have following functionality.
        - Get strategy id.
        - Get strategy name.
        - Get strategy type.
        - Get strategy status.
        - Get strategy last checked timestamp.
        - Deploy/Undeploy strategy.
          - On deploy;
            - it should register itself to Strategy Manager.
            - it should subscribe to data streaming for all required symbols in strategy.
          - On undeploy;
            - it should unregister itself from Strategy Manager.
            - it should unsubscribe from data streaming for all required symbols in strategy.
        - Core logic for strategy execution.
        - Generate signal on matching strategy logic. Generated signal sent to Position Size Manager. Signal should have following information.
          - Strategy id.
          - Symbol.
          - Price.
          - Single type (buy or sell).
          - SL Price (Optional).
          - TP Price (Optional).
        - Logs Management Functionality filtered from strategy manager logs.
        - May have risk management rules specific to strategy, if not then it will use global risk management rules.
    - Risk Management Module (sub-module):
      This module have all code related to managing risk. Base risk class, Risk Manager Class, etc.
      - Risk Manager Class:
        - It calculate risk and reward for each signal generated by strategies.
        - Once risk is calculated, then audit risk and reward as per risk management rules.
        - Once audit is done, then take decision to execute trade or not.
        - If decision is to execute trade, then it **Publishes a Signal** to ZeroMQ (topic family `orders.signal.*`).
        - Risk Management Rules can be global, strategy specific.
          - Global Risk Management Rules superceeds all other rules.
      - Position Size Management Module (sub-module):
        This module should have functionality to calculate position size for each signal generated by strategies as per risk manager rules.
        - Position Size Manager Class:
          - This class has main goal to calculate quantity for each signal generated by strategies as per risk management rules.
          - It can override tp and sl price of signal as per risk management rules, but entry price will not be overridden.
          - Once, quantity is calculated, then it send to broker manager to execute trade.

## Data Structures

- **MessageEnvelope** (All ZMQ messages MUST use this envelope):

  - `type`: str (e.g., `md.update`, `orders.signal`, `orders.exec_report`, `control.strategy`)
  - `schema_version`: int
  - `correlation_id`: str (request/reply tracing)
  - `topic`: str (the ZMQ topic used for routing/filtering)
  - `seq`: int (monotonic per topic; required for streams)
  - `ts`: float (producer timestamp, seconds)
  - `source`: str (service identifier)
  - `payload`: dict (one of the typed payloads below)

- **Signal**:

  - `strategy_id`: str
  - `symbol`: str
  - `entry_price`: float
  - `stop_loss`: float
  - `target_price`: float
  - `timestamp`: int
  - `signal_type`: str (BUY/SELL)

- **OrderRequest** (Inherits Signal):

  - `quantity`: int
  - `estimated_pnl`: float
  - `validity`: str (DAY/IOC)
  - `order_type`: str (MARKET/LIMIT)

- **Control Message**:

  - `request_id`: str
  - `command`: str
  - `payload`: dict

- **ExecutionReport**:

  - `order_id`: str
  - `strategy_id`: str | None
  - `symbol`: str
  - `side`: str (BUY/SELL)
  - `status`: str (PLACED/PARTIAL/FILLED/CANCELLED/REJECTED)
  - `filled_qty`: int
  - `avg_fill_price`: float | None
  - `reason`: str | None
  - `ts`: float

- **MarketData**:
  - `symbol`: str
  - `exchange`: str
  - `ltp`: float
  - `change`: float
  - `percent_change`: float
  - `open`: float
  - `high`: float
  - `low`: float
  - `close`: float
  - `volume`: int
  - `timestamp`: float

## Centralized Configuration (Future Scope)

- **Config Service**:
  - **Role**: Serves configuration to all services via ZeroMQ **REP** socket.
  - **Bootstrapping**: Services connect to a known URL (env var) to fetch their config (ports, keys, etc.).
  - **Protocol**: JSON-RPC.

## Centralized Logging (Future Scope)

- **Logger Service**:

  - **Role**: Aggregates logs from all services.
  - **Transport**: ZeroMQ **PULL** (Server) / **PUSH** (Client) or **ROUTER/DEALER**.
  - **Storage**: Writes to file/database.
  - **Client**: Services use a lightweight ZeroMQ logger adapter instead of local file logging.

- **Current Implementation**:
  - **Config**: `app.core.config` (Pydantic BaseSettings) loading from `.env`.
  - **Logging**: `app.utils.logging` writing to local files/console.

## Next Possible Steps (Roadmap Candidates)

- **High-frequency feed fan-out**: introduce Redis Streams / Kafka (optional) if the market-data rate or client count outgrows a single-process fan-out.
- **Auth**: JWT-based auth for REST + WebSockets (token during handshake or first message).
- **Deployment**: Docker + optional reverse proxy (e.g., Nginx) for TLS termination and compression.
- **Frontend UX patterns**: watchlist virtualization, change-highlight animations, dark mode, and render-throttling aligned with backend batching.

- Flow of the application:
  - Application start. On start, do followings;
    - Start Web Server Module.
      - Start FastAPI server.
      - Start WebSocket server.
      - Connect to ZeroMQ (Subscriber) for real-time data.
      - Notify running state to Application.
    - Start Data Engine.
      - **Started by Web Server**: In Phase 1, `DataService` is started as a background task by `app/main.py`.
      - Initialize Broker Manager (DATA capability) in passive mode.
      - Load persisted subscriptions (if any) and build in-memory subscription registry.
      - **Wait for Auth**: On `BROKER_AUTH_SUCCESS`, Data Engine requests token material from Web using `broker_session_id` over ROUTER/DEALER (no token broadcast).
      - **On Token Receive**:
        - Initialize broker adapter (e.g., Fyers) with token.
        - Start data streaming for active subscriptions.
      - Publish data streaming status and market-data updates to Algo and Web.
    - Start Execution Engine.
      - Initialize Broker Manager (ORDER capability) in passive mode.
      - **Wait for Auth**: On `BROKER_AUTH_SUCCESS`, Execution Engine requests token material from Web using `broker_session_id` over ROUTER/DEALER.
      - Load persisted orders/strategies state as needed and start reconciliation loop(s).
      - Publish execution reports and account state updates to Web and Algo.
    - Start Algo Module.
      - Start Strategy Manager (Supervisor).
      - Load all strategies from database.
      - Set initial status of deployed strategies to `WAITING_FOR_DATA`.
      - Subscribe to `DATA_STREAMING_STARTED` event from Data Engine.
      - **On `DATA_STREAMING_STARTED` event**:
        - Verify required data feeds are active.
        - Transition applicable strategies to `RUNNING` (Deploy to Worker Processes).
