# National Weather Big Data Analytics Platform

**Smart India Hackathon 2026 — Problem Statement ID**: `SIH26069`  
**Domain**: Big Data Analytics / Disaster Management / Geospatial Intelligence

---

## 1. Project Overview & Mission

The **National Weather Big Data Analytics Platform** is a scalable, real-time intelligence system engineered to ingest, corroborate, and analyze multi-source meteorological feeds and crowdsourced citizen incident reports during extreme weather emergencies.

The platform bridges the gap between high-altitude meteorological observations (IMD radar, AWS, hydrological stations) and localized ground realities (urban waterlogging, flash floods, landslides, storm damage) through:
- **High-Throughput Multi-Source Ingestion**: Citizen web submissions, IMD automatic weather stations, NDMA alerts, CWC flood telemetry, and open disaster feeds.
- **Intelligent Pipeline**: Rule-based categorization, spatial-temporal deduplication, and digital/physical sensor corroboration.
- **Explainable Credibility Scoring**: Deterministic, multi-factor scoring engine providing transparent driver breakdowns and uncertainty flags.
- **Interactive Geospatial Dashboards**: Live Leaflet map, multi-dimensional incident explorer, and priority-ranked triage queues for disaster management authorities (NDRF, SDRF, DEOCs).

---

## 2. High-Level Architecture

```
[Citizen Reports, IMD Telemetry, CWC, NDMA Feeds]
                      │
                      ▼
        [Pluggable Ingestion Adapters]
                      │
                      ▼
            [Redis Streams Buffer]
                      │
                      ▼
    [Asynchronous Orchestration & Intelligence Pipeline]
   ┌──────────────────────────────────────────────────┐
   │ 1. Classification & Quality Gate                 │
   │ 2. Spatial-Temporal Clustering (FastEmbed/GiST)  │
   │ 3. Digital Evidence Provenance Linking           │
   │ 4. Physical Station Observation Corroboration    │
   │ 5. Explainable Credibility Scoring Engine        │
   └──────────────────────────────────────────────────┘
                      │
                      ▼
      [PostgreSQL 16 + PostGIS] ◄──► [MinIO / S3 Object Storage]
                      │
                      ▼
       [FastAPI Intelligence REST Layer]
                      │
                      ▼
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

---

## 4. Current Implementation & Verification Status

| Subsystem / Phase | Scope & Implementation Status | Verification Gates |
| :--- | :--- | :---: |
| **Phase 0–3: Foundation & Schemas** | PostgreSQL 16 + PostGIS, declarative models, spatial GiST indexes, Alembic migrations. | **COMPLETED & VERIFIED** |
| **Phase 4: Citizen Intake** | Multi-part report intake, photo upload to MinIO, GPS geocoding, public tracking. | **COMPLETED & VERIFIED** |
| **Phase 5–6: Ingestion & Streaming** | Adapters for IMD AWS, NDMA SACHET, CWC, Mastodon, GDELT; Redis Stream workers. | **COMPLETED & VERIFIED** |
| **Phase 7–9: AI Intelligence Engine** | Deduplication clustering, digital evidence linking, physical station corroboration, explainable credibility scorer. | **COMPLETED & VERIFIED** |
| **Phase 10: Executive Dashboard** | Live Leaflet map, KPI telemetry cards, category breakdown charts, spatial queries. | **COMPLETED & VERIFIED** |
| **Phase 11: Verification & Triage** | Priority triage queue, side-by-side evidence inspection, status-aware action drawer, immutable audit log. | **COMPLETED & VERIFIED** |
| **Incident Intelligence Frontend** | Multi-filter Incident Explorer (`/incidents`), 5-dimension Deep-Dive (`/incidents/:id`), Operator Portal (`/login`). | **COMPLETED & VERIFIED** |
| **Phase 13: Analytics Platform** | Server-aggregated trends (`/api/v1/analytics/trends`), summary metrics, and two-tier regional demographics (`/api/v1/analytics/regional`). | **COMPLETED & VERIFIED** |
| **Phase 12: Real-Time Event Streaming** | Transactional outbox pattern, dedicated worker, Redis Streams buffer, FastAPI SSE (`GET /api/v1/events/stream`), and React Query live cache invalidation. | **COMPLETED & VERIFIED** |
| **Phase 14–15: Production Auth & Scale** | Role-based JWT/OAuth2 boundary, multi-region Kafka streaming, edge IoT mesh. | *Future Hardening Scope* |

---

## 5. Authentication & Operator Access Status (MVP Honest Disclosure)

> [!NOTE]
> **Current MVP Architecture**: In accordance with the hackathon evaluation scope, the platform provides an **Emergency Operations Portal** (`/login`) acting as an open operator-access gateway into the Verification Queue (`/admin/queue`) and Incident Intelligence Center (`/incidents`).
> 
> Triage actions are immutably logged under the institutional reviewer record (`officer@deoc.gov.in`, `DEOC_OFFICER`). 
> 
> Full HTTP Bearer token validation, password hashing, and session lifecycle enforcement are deferred to production security hardening.

---

## 6. Quickstart & Local Setup

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

### 4. Frontend Setup
```bash
cd front-end
npm install
npm run dev
```

The application will be available at:
- **Frontend Dashboard**: `http://localhost:5173`
- **Weather Analytics**: `http://localhost:5173/analytics`
- **Operator Access Portal**: `http://localhost:5173/login`
- **Verification Queue**: `http://localhost:5173/admin/queue`
- **Incident Explorer**: `http://localhost:5173/incidents`
- **Backend Swagger API Docs**: `http://localhost:8000/docs`
- **Real-Time SSE Stream**: `http://localhost:8000/api/v1/events/stream`

---

## 7. Quality Gates & Automated Testing

### Backend Quality Suite
```bash
cd back-end
.venv/bin/pytest -q                       # Runs 322 unit and integration tests (100% passing)
.venv/bin/mypy app tests                 # Full static typechecking (0 issues across 136 source files)
.venv/bin/ruff check .                   # Linter check (0 errors)
.venv/bin/ruff format --check .          # Code formatting verification (141 files formatted)
pyrefly check                            # Python 3.14 static diagnostics (0 errors)
```

### Frontend Quality Suite
```bash
cd front-end
npm run typecheck                        # TypeScript strict compiler check (0 errors)
npm run lint                             # ESLint verification (0 errors, 0 warnings)
npx vitest run                           # Runs 152 unit and contract tests (100% passing across 9 suites)
npm run build                            # Production bundle build verification (built in ~1.8s)
```

---

## 8. Authoritative Documentation Suite

For comprehensive specifications, consult the `/docs` documentation suite:
- [docs/PRD.md](file:///Users/akshatjain/Documents/SIH/docs/PRD.md) — Product Requirements, User Personas, SIH Scope.
- [docs/ARCHITECTURE.md](file:///Users/akshatjain/Documents/SIH/docs/ARCHITECTURE.md) — High-Level Design, Data Flow, Intelligence Pipeline.
- [docs/TECH_STACK.md](file:///Users/akshatjain/Documents/SIH/docs/TECH_STACK.md) — Approved Frameworks, Libraries, and Technical Constraints.
- [docs/DATA_MODEL.md](file:///Users/akshatjain/Documents/SIH/docs/DATA_MODEL.md) — Entity Relationships, Field Constraints, Spatial Schemas.
- [docs/API_CONTRACT.md](file:///Users/akshatjain/Documents/SIH/docs/API_CONTRACT.md) — RESTful Endpoints, Envelopes, Schemas.
- [docs/EXTERNAL_SETUP.md](file:///Users/akshatjain/Documents/SIH/docs/EXTERNAL_SETUP.md) — Environment Configuration and Service Credentials.
- [docs/IMPLEMENTATION_PLAN.md](file:///Users/akshatjain/Documents/SIH/docs/IMPLEMENTATION_PLAN.md) — Phased Implementation Roadmap & Verification Gates.
- [AGENTS.md](file:///Users/akshatjain/Documents/SIH/AGENTS.md) — Developer & AI Agent Guardrails.
