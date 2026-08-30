# National Weather Big Data Analytics Platform

**Smart India Hackathon 2026 — Problem Statement ID**: `SIH26069`
**Domain**: Big Data Analytics / Disaster Management / Geospatial Intelligence
**Status**: **FROZEN FOR SIH/MVP SCOPE** (Baseline: `faa14cd`)

---

## 1. Project Overview & Mission

The **National Weather Big Data Analytics Platform** is a real-time big data analytics and geospatial intelligence platform engineered to ingest, corroborate, and analyze multi-source meteorological feeds and crowdsourced citizen incident reports during extreme weather emergencies.

The platform bridges the gap between high-altitude meteorological observations (IMD radar, AWS, hydrological stations) and localized ground realities (urban waterlogging, flash floods, landslides, storm damage) through:
- **High-Throughput Multi-Source Ingestion**: Citizen web submissions with photo uploads, IMD automatic weather stations, NDMA SACHET alerts, CWC flood telemetry, Mastodon posts, and GDELT disaster news.
- **Intelligent Pipeline**: Rule-based categorization, spatial-temporal deduplication clustering ($R \le 2.5\text{ km}$, $\Delta T \le 120\text{ min}$), and digital evidence/physical sensor corroboration.
- **Explainable Credibility Scoring**: Deterministic, multi-factor scoring engine ($0.0000$ to $0.9800$) providing transparent driver breakdowns and uncertainty flags.
- **Interactive Geospatial Dashboards**: Live Leaflet GIS map with bounded GeoJSON vector layers, server-aggregated weather analytics, and priority-ranked triage queues for disaster management authorities (NDRF, SDRF, DEOCs).
- **Transactional Real-Time Streaming**: Atomic outbox pattern in PostgreSQL, dedicated worker relay, Redis Streams buffer (`stream:weather:realtime`), persistent FastAPI Server-Sent Events (`GET /api/v1/events/stream`), and automatic React Query cache invalidation.

---

## 2. High-Level Architecture

```
[Citizen Reports, IMD Telemetry, CWC, NDMA, Mastodon, GDELT]
                          │
                          ▼
            [Pluggable Ingestion Adapters]
                          │
                          ▼
      [PostgreSQL 16 + PostGIS] ◄──► [MinIO / S3 Storage]
         ├── weather_reports / duplicate_clusters
         ├── verification_events (audit log)
         └── realtime_outbox (status = 'PENDING')
                          │
                          ▼ (SKIP LOCKED Batch Polling)
        [Dedicated Outbox Worker Process]
        (python -m app.workers.run_outbox_worker)
                          │
                          ▼ (XADD Stable Event IDs)
         [Redis 7 Stream: stream:weather:realtime]
                          │
                          ▼ (XREAD Cursor & Replay)
          [FastAPI SSE Stream: /api/v1/events/stream]
                          │
                          ▼ (Deduplicated Push)
         [Frontend RealtimeService Singleton]
                          │
                          ▼ (Targeted Query Invalidation)
         [TanStack React Query Cache Layer]
                          │
                          ▼ (Authoritative REST Refetch)
     [React 18 + Leaflet + Recharts Operations Dashboard]
```

---

## 3. Core Semantic & Architectural Guarantees

The platform strictly enforces the following domain separations:

1. **Machine Credibility $\ne$ Human Ground Truth**: `credibility_score` ($0.0000$ to $0.9800$) is an algorithmic machine assessment. `verification_status` (`PENDING`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `DUPLICATE`) is the authoritative operational state set by human operators.
2. **Crowd Volume $\ne$ Independent Confirmations**: Duplicate reports are clustered with a single diminishing-returns sub-signal, never summed as independent corroborating proofs.
3. **Stage Execution $\ne$ Domain Corroboration**: Orchestration stage outcomes (`SUCCESS_WITH_RESULTS`) signify that an analysis stage executed and found telemetry, not that the incident was verified.
4. **Zero Client-Side Intelligence Math**: The frontend is a pure presentation consumer and never recalculates credibility, cluster embeddings, or corroboration weights.
5. **No Binary Media in Relational Database**: All images and videos reside in S3/MinIO; only metadata, dimensions, SHA-256 checksums, and signed URIs are stored in PostgreSQL.
6. **Delivery Semantics**: At-least-once stream delivery with bounded frontend deduplication (1,000 items). The system does not claim an unverified exactly-once guarantee.

---

## 4. Current Implementation & Verification Status

| Subsystem / Phase | Scope & Implementation Status | Verification Gates |
| :--- | :--- | :---: |
| **Phase 0–3: Foundation & Schemas** | PostgreSQL 16 + PostGIS, declarative models, spatial GiST indexes, Alembic migrations (`0001`–`0004`). | **COMPLETED & VERIFIED** |
| **Phase 4: Citizen Intake** | Multi-part report intake, photo upload to MinIO, GPS geocoding, public tracking. | **COMPLETED & VERIFIED** |
| **Phase 5–6: Ingestion & Streaming** | Adapters for IMD AWS, NDMA SACHET, CWC, Mastodon, GDELT; Redis Stream workers. | **COMPLETED & VERIFIED** |
| **Phase 7–9: AI Intelligence Engine** | Deduplication clustering, digital evidence linking, physical station corroboration, explainable credibility scorer. | **COMPLETED & VERIFIED** |
| **Phase 10: Executive Dashboard** | Live Leaflet map, KPI telemetry cards, category breakdown charts, bounded GeoJSON queries. | **COMPLETED & VERIFIED** |
| **Phase 11: Verification & Triage** | Priority triage queue, side-by-side evidence inspection, status-aware action drawer, immutable audit log. | **COMPLETED & VERIFIED** |
| **Incident Intelligence Frontend** | Multi-filter Incident Explorer (`/incidents`), 5-dimension Deep-Dive (`/incidents/:id`), Operator Portal (`/login`). | **COMPLETED & VERIFIED** |
| **Phase 13: Analytics Platform** | Server-aggregated trends (`/api/v1/analytics/trends`), summary metrics, and two-tier regional demographics (`/api/v1/analytics/regional`). | **COMPLETED & VERIFIED** |
| **Phase 12: Real-Time Event Streaming** | Transactional outbox pattern, dedicated worker, Redis Streams buffer, FastAPI SSE (`GET /api/v1/events/stream`), and React Query live cache invalidation. | **COMPLETED & VERIFIED** |
| **Phase 13E: Map GeoJSON Migration** | Bounded HTTP GeoJSON queries (`GET /api/v1/geo/incidents`, 500-feature bound), lazy detail lookups, and error fallback. | **COMPLETED & VERIFIED** |
| **Production Auth & Supervision** | Institutional OAuth2/JWT boundary, multi-worker process supervision (`systemd`/Kubernetes). | *Deferred Production Hardening* |

---

## 5. Quickstart & Local Setup

### Prerequisites
- Python 3.11+ (or Python 3.14)
- Node.js 18+ and npm
- Docker & Docker Compose (for PostgreSQL/PostGIS, Redis, and MinIO)

### 1. Start Infrastructure
```bash
docker compose up -d
```

### 2. Backend API Setup
```bash
cd back-end
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8000 --reload
```

### 3. Realtime Outbox Worker (Separate Terminal)
```bash
cd back-end
source .venv/bin/activate
python -m app.workers.run_outbox_worker
```

### 4. Frontend Setup (Separate Terminal)
```bash
cd front-end
npm install
npm run dev
```

---

## 6. Important Application URLs

| Interface | URL | Purpose |
| :--- | :--- | :--- |
| **Executive Dashboard** | `http://localhost:5173/dashboard` | Main situational awareness dashboard with KPI cards and Leaflet map |
| **Live GIS Map** | `http://localhost:5173/map` | Fullscreen operational Leaflet map with lazy detail inspection |
| **Weather Analytics** | `http://localhost:5173/analytics` | Server-aggregated trends, category breakdown, and regional demographics |
| **Citizen Reporting Portal** | `http://localhost:5173/report` | Public incident submission form with photo upload and GPS pin |
| **Public Report Tracking** | `http://localhost:5173/track-report` | Public citizen status lookup via Reference Tracking ID |
| **Operator Access Portal** | `http://localhost:5173/login` | Institutional gateway for DEOC / SDRF / NDRF emergency officers |
| **Verification & Triage Queue** | `http://localhost:5173/admin/queue` | Priority triage backlog for verifying, rejecting, or clustering incidents |
| **Incident Explorer** | `http://localhost:5173/incidents` | Multi-filter incident inventory with credibility indicators |
| **Interactive API Documentation** | `http://localhost:8000/docs` | Swagger UI documentation for all 22 registered API endpoints |
| **Real-Time SSE Stream** | `http://localhost:8000/api/v1/events/stream` | Persistent Server-Sent Events stream for live dashboard propagation |

---

## 7. Quality Gates & Automated Testing

### Backend Quality Suite
```bash
cd back-end
.venv/bin/pytest -q                       # Runs 325 unit and integration tests (100% passing)
.venv/bin/mypy app tests                 # Full static typechecking (0 issues across 136 source files)
.venv/bin/ruff check .                   # Linter check (0 errors)
.venv/bin/ruff format --check .          # Code formatting verification (141 files clean)
pyrefly check                            # Python 3.14 static type analyzer (0 errors)
```

### Frontend Quality Suite
```bash
cd front-end
npm run typecheck                        # TypeScript strict compiler check (0 errors)
npm run lint                             # ESLint verification (0 errors, 0 warnings)
npx vitest run                           # Runs 160 unit, migration, and contract tests (100% passing across 11 suites)
npm run build                            # Production bundle build verification (built in ~1.9s)
```

---

## 8. Known MVP Boundaries & Deferred Production Hardening

1. **Operator Authentication**: Verification triage mutations operate unauthenticated in the local demo environment to facilitate evaluator testing. Institutional OAuth2 / JWT authentication is deferred for production hardening.
2. **Worker Supervision**: The outbox worker runs as a dedicated CLI process (`python -m app.workers.run_outbox_worker`). In production, it should be supervised via `systemd` or Kubernetes Pod lifecycle management.
3. **500-Feature Map Bound**: Map queries enforce a 500-feature server-side limit (`LIMIT 500`) to protect browser memory. Macro counts derive authoritatively from `/api/v1/dashboard/summary`.
4. **Cloud Observability**: Structured Python logging is active; OpenTelemetry distributed tracing and Prometheus exporters are deferred for cloud deployment.

---

## 9. Recommended Demo Walkthrough

1. **Start Infrastructure & Services**: Run Docker containers, start FastAPI on port 8000, launch the outbox worker in a separate terminal, and run Vite frontend on port 5173.
2. **Open Dashboard (`/dashboard`)**: Inspect national KPI cards (Total Reports, Verified, Under Review, High Severity), hazard category distribution, and the interactive Leaflet map.
3. **Submit a Citizen Report (`/report`)**: Fill out the form (e.g., severe waterlogging in Kurla, Mumbai), attach an image, and submit. Receive the instant tracking ID (`RPT-...`).
4. **Observe Realtime Triage Queue (`/admin/queue`)**: Without page refresh, the new incident appears in the priority triage queue with `PENDING` status.
5. **Perform Operator Triage (`/admin/queue`)**: Click the incident, inspect the machine credibility explanation and corroborating evidence, and click **Verify Incident**.
6. **Observe Real-Time Dashboard Propagation**: Return to `/dashboard` — the Verified Reports counter increments immediately and the incident card updates without a page refresh.
7. **Inspect Analytics & Intelligence (`/analytics`, `/incidents/:id`)**: Explore time-series trends and inspect the 5-dimension deep-dive intelligence view.

---

## 10. Authoritative Documentation Suite

For deeper technical specifications, consult the `/docs` documentation suite:
- [docs/ARCHITECTURE.md](file:///Users/akshatjain/Documents/SIH/docs/ARCHITECTURE.md) — Comprehensive System Architecture, Lifecycle, and Realtime Design.
- [docs/API_CONTRACT.md](file:///Users/akshatjain/Documents/SIH/docs/API_CONTRACT.md) — Complete RESTful and SSE Endpoint Catalog.
- [docs/DATA_MODEL.md](file:///Users/akshatjain/Documents/SIH/docs/DATA_MODEL.md) — Entity Relationships, Field Constraints, and PostGIS Schemas.
- [docs/TECH_STACK.md](file:///Users/akshatjain/Documents/SIH/docs/TECH_STACK.md) — Approved Frameworks, Libraries, and Technical Constraints.
- [docs/EXTERNAL_SETUP.md](file:///Users/akshatjain/Documents/SIH/docs/EXTERNAL_SETUP.md) — Configuration Reference, Environment Variables, and Operations Runbook.
- [docs/PROJECT_STATUS.md](file:///Users/akshatjain/Documents/SIH/docs/PROJECT_STATUS.md) — Authoritative Engineering Freeze Status and Verification Snapshot.
- [docs/PRD.md](file:///Users/akshatjain/Documents/SIH/docs/PRD.md) — Product Requirements Traceability Matrix.
- [docs/IMPLEMENTATION_PLAN.md](file:///Users/akshatjain/Documents/SIH/docs/IMPLEMENTATION_PLAN.md) — Implementation History and Phased Delivery Record.
- [AGENTS.md](file:///Users/akshatjain/Documents/SIH/AGENTS.md) — Developer & AI Agent Guidelines.
