# Step-by-Step Implementation Roadmap

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)  
**Methodology**: Phased, incremental delivery with strict verification gates at each phase.

---

## Roadmap Overview

```
Phase 0: Project Initialization & Architectural Source of Truth (CURRENT)
  │
  ├─► Phase 1: Repository Foundation, Tooling & Scaffolding
  │
  ├─► Phase 2: Local Infrastructure (PostgreSQL/PostGIS, Redis, MinIO)
  │
  ├─► Phase 3: Database Models, Spatial Schemas & Alembic Migrations
  │
  ├─► Phase 4: Citizen Reporting Flow (API + Web Form + Media Upload)
  │
  ├─► Phase 5: External Ingestion Adapters (IMD AWS + RSS Feeds)
  │
  ├─► Phase 6: Asynchronous Ingestion & Processing Pipeline (Redis Streams)
  │
  ├─► Phase 7: AI Intelligence — Rule & NLP Event Classification
  │
  ├─► Phase 8: AI Intelligence — Spatial-Temporal Deduplication & Clustering
  │
  ├─► Phase 9: AI Intelligence — Explainable Credibility Scoring Engine
  │
  ├─► Phase 10: Executive & Operator Dashboard (KPIs, Charts, Leaflet Map)
  │
  ├─► Phase 11: Administrative Triage & Verification Queue
  │
  ├─► Phase 12: Real-Time Event Streaming (Server-Sent Events / SSE)
  │
  ├─► Phase 13: Analytics, Historical Trends & System Health Telemetry
  │
  ├─► Phase 14: End-to-End Testing, Load Simulation & Security Hardening
  │
  └─► Phase 15: Demo Scenario Preparation, Seed Datasets & Presentation Packaging
```

---

## Phase Details

### Phase 0: Project Initialization & Architectural Source of Truth
- **Objective**: Establish project directory structure, core documentation, rules, schemas, and workflows without premature implementation.
- **Dependencies**: None.
- **Tasks**:
  - Create root architecture and specification documentation under `/docs`.
  - Create agent rules and verification workflows under `/.agents`.
  - Establish `.gitignore` and baseline repository settings.
- **Expected Files**:
  - `AGENTS.md`, `README.md`, `.gitignore`
  - `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/TECH_STACK.md`, `docs/DATA_MODEL.md`, `docs/API_CONTRACT.md`, `docs/EXTERNAL_SETUP.md`, `docs/IMPLEMENTATION_PLAN.md`
  - `.agents/rules/project-rules.md`, `.agents/workflows/verify.md`, `.agents/workflows/checkpoint.md`
- **Verification Criteria**: All documentation files exist, are internally consistent, and no production code was prematurely generated.
- **Manual Setup**: None.

---

### Phase 1: Repository Foundation, Tooling & Scaffolding
- **Objective**: Bootstrap clean frontend and backend project skeletons with strict linters, formatters, and configuration managers.
- **Dependencies**: Phase 0.
- **Tasks**:
  - Initialize FastAPI backend structure with `pyproject.toml` / `requirements.txt`, `ruff`, `mypy`, `pytest`.
  - Initialize React + TypeScript frontend using Vite, Tailwind CSS, shadcn/ui foundation.
  - Setup Pydantic `BaseSettings` configuration and `.env.example`.
- **Expected Files**:
  - `back-end/app/main.py`, `back-end/app/core/config.py`, `back-end/pyproject.toml`
  - `front-end/package.json`, `front-end/vite.config.ts`, `front-end/src/App.tsx`, `front-end/tailwind.config.js`
- **Verification Criteria**: `ruff check`, `mypy`, `npm run build`, and `npm run typecheck` run clean with zero errors.
- **Manual Setup**: None.

---

### Phase 2: Local Infrastructure & Container Orchestration
- **Objective**: Provide a local development environment with PostgreSQL + PostGIS, Redis, and MinIO.
- **Dependencies**: Phase 1.
- **Tasks**:
  - Create `docker-compose.yml` defining `postgres` (with PostGIS 3.4 image), `redis` (v7), and `minio`.
  - Create local setup scripts for bucket creation and database health checks.
- **Expected Files**:
  - `docker-compose.yml`, `scripts/init_local_env.sh`
- **Verification Criteria**: All 3 services start cleanly; `psql -c "SELECT postgis_full_version();"` succeeds; Redis accepts `PING`; MinIO console is reachable.
- **Manual Setup**: Local Docker Desktop / Engine running.

---

### Phase 3: Database Models, Spatial Schemas & Alembic Migrations
- **Objective**: Implement SQLAlchemy 2.0 async models and execute initial Alembic migration.
- **Dependencies**: Phase 2.
- **Tasks**:
  - Define declarative models for all 10 core entities in `back-end/app/models/`.
  - Configure GeoAlchemy2 spatial types for coordinates and geometry points.
  - Generate and apply initial Alembic migration `0001_initial_schema.py`.
- **Expected Files**:
  - `back-end/app/models/`, `back-end/alembic/`, `back-end/alembic/versions/`
- **Verification Criteria**: `alembic upgrade head` executes smoothly; table structures and spatial GiST indexes match `DATA_MODEL.md`.
- **Manual Setup**: None.

---

### Phase 4: Citizen Reporting Flow (API + Web Form + Media Upload)
- **Objective**: End-to-end citizen reporting workflow from web submission to database persistence and MinIO media storage.
- **Dependencies**: Phase 3.
- **Tasks**:
  - Implement `POST /api/v1/reports` with multipart handling and S3 upload service.
  - Implement citizen web form with GPS location picker and photo attachment in React.
  - Implement tracking screen for submitted reports (`GET /api/v1/reports/{id}`).
- **Expected Files**:
  - `back-end/app/api/v1/reports.py`, `back-end/app/services/media_storage.py`
  - `front-end/src/pages/CitizenReportPage.tsx`, `front-end/src/components/forms/ReportForm.tsx`
- **Verification Criteria**: Submitting a report via UI saves metadata to PostgreSQL, uploads image to MinIO, and returns tracking code.
- **Manual Setup**: None.

---

### Phase 5: External Ingestion Adapters (IMD AWS + RSS Feeds)
- **Objective**: Implement pluggable ingestion adapters for external meteorological data.
- **Dependencies**: Phase 3.
- **Tasks**:
  - Build `BaseIngestionAdapter` interface.
  - Implement IMD AWS observation poller with parsing for temperature, rain, wind, and pressure.
  - Implement Disaster RSS / GeoRSS feed parser.
  - Implement demo seed generator for offline testing.
- **Expected Files**:
  - `back-end/app/ingestion/base.py`, `back-end/app/ingestion/imd/`, `back-end/app/ingestion/rss/`
- **Verification Criteria**: Running ingestion fetches observations and saves valid records into `weather_observations` and `weather_reports`.
- **Manual Setup**: Optional Data.gov.in API key (if live polling enabled).

---

### Phase 6: Asynchronous Ingestion & Processing Pipeline (Redis Streams)
- **Objective**: Connect ingestion adapters to Redis Streams and build async worker consumers.
- **Dependencies**: Phase 4, Phase 5.
- **Tasks**:
  - Implement `StreamPublisher` pushing events to `stream:weather:events`.
  - Implement background worker consumer loop with consumer group load-balancing and retry logic.
- **Expected Files**:
  - `back-end/app/core/redis_client.py`, `back-end/app/workers/ingestion_worker.py`
- **Verification Criteria**: 100 concurrent test reports enqueued into Redis are processed and committed by workers without dropouts.
- **Manual Setup**: None.

---

### Phase 7: AI Intelligence — Rule & NLP Event Classification
- **Objective**: Automatically classify unstructured descriptions into standardized hazard categories.
- **Dependencies**: Phase 6.
- **Tasks**:
  - Build keyword/rule-based hazard classifier.
  - Integrate lightweight NLP zero-shot / FastEmbed classifier for ambiguous descriptions.
  - Update `weather_reports.category_id` and severity assessments automatically.
- **Expected Files**:
  - `back-end/app/intelligence/classifier.py`
- **Verification Criteria**: Unit tests verifying classification accuracy across 50 sample hazard descriptions ($> 90\%$ accuracy).
- **Manual Setup**: None.

---

### Phase 8: AI Intelligence — Spatial-Temporal Deduplication & Clustering
- **Objective**: Group concurrent, co-located reports into duplicate clusters.
- **Dependencies**: Phase 7.
- **Tasks**:
  - Implement PostGIS spatial proximity check ($R \le 2.5\text{ km}$) and temporal window ($\Delta T \le 120\text{ min}$).
  - Implement FastEmbed text embedding cosine similarity ($> 0.75$).
  - Create/update `duplicate_clusters` and link `duplicate_members`.
- **Expected Files**:
  - `back-end/app/intelligence/deduplication.py`, `back-end/app/intelligence/embeddings.py`
- **Verification Criteria**: 5 simulated reports of the same flood at the same junction are automatically grouped into a single cluster.
- **Manual Setup**: None.

---

### Phase 9: AI Intelligence — Explainable Credibility Scoring Engine
- **Objective**: Compute transparent, multi-factor credibility score for every report.
- **Dependencies**: Phase 8.
- **Tasks**:
  - Implement scoring formula: source weight + cluster corroboration + IMD sensor proximity delta + media verification.
  - Generate structured `credibility_explanation` JSONB document.
- **Expected Files**:
  - `back-end/app/intelligence/credibility.py`
- **Verification Criteria**: Validated reports near active IMD stations score $> 0.80$; isolated unverified reports score $< 0.50$; breakdown is fully explainable.
- **Manual Setup**: None.

---

### Phase 10: Executive & Operator Dashboard
- **Objective**: Build the core visual interface with interactive Leaflet map and Recharts analytics.
- **Dependencies**: Phase 9.
- **Tasks**:
  - Implement Leaflet Map Explorer with marker clustering, hazard layer toggles, and radius circles.
  - Implement KPI summary cards and severity breakdown charts.
  - Build multi-filter controls (Date range, Hazard category, Severity, Status).
- **Expected Files**:
  - `front-end/src/pages/DashboardPage.tsx`, `front-end/src/components/map/WeatherMap.tsx`, `front-end/src/components/analytics/KpiCards.tsx`
- **Verification Criteria**: Map fluidly renders $> 500$ markers with filters dynamically updating cards and charts.
- **Manual Setup**: None.

---

### Phase 11: Administrative Triage & Verification Queue
- **Objective**: Dedicated interface for disaster management officers to review and verify incidents.
- **Dependencies**: Phase 10.
- **Tasks**:
  - Implement `GET /api/v1/admin/verification-queue` and triage actions (`POST verify`, `POST reject`, `POST mark-duplicate`).
  - Build Admin Queue UI with side-by-side evidence viewer (photos + sensor readings + AI explanation).
- **Expected Files**:
  - `back-end/app/api/v1/admin.py`, `front-end/src/pages/AdminQueuePage.tsx`, `front-end/src/components/admin/TriageDetailModal.tsx`
- **Verification Criteria**: Officer can verify an incident; status changes to `VERIFIED`; audit record is written to `verification_events`.
- **Manual Setup**: None.

---

### Phase 12: Real-Time Event Streaming (Server-Sent Events)
- **Objective**: Enable real-time updates on the dashboard without manual page refreshes.
- **Dependencies**: Phase 11.
- **Tasks**:
  - Implement SSE endpoint in FastAPI reading from Redis Pub/Sub.
  - Connect React frontend TanStack Query cache invalidation to incoming SSE stream.
- **Expected Files**:
  - `back-end/app/api/v1/realtime.py`, `front-end/src/hooks/useRealtimeStream.ts`
- **Verification Criteria**: Submitting a report in another tab triggers an instant map marker and counter update on the dashboard in $< 1\text{ second}$.
- **Manual Setup**: None.

---

### Phase 13: Analytics, Historical Trends & System Health Telemetry
- **Objective**: Deep-dive analytics, trend visualization, and adapter telemetry monitoring.
- **Dependencies**: Phase 12.
- **Tasks**:
  - Implement time-series aggregation endpoints in backend.
  - Build Analytics Page with Recharts flood hydrographs, seasonal frequency, and source reliability scores.
  - Build System Health page showing adapter uptime and stream lag.
- **Expected Files**:
  - `front-end/src/pages/AnalyticsPage.tsx`, `front-end/src/pages/SystemHealthPage.tsx`
- **Verification Criteria**: Historical date range queries render smooth time-series charts; health page displays live adapter latencies.
- **Manual Setup**: None.

---

### Phase 14: End-to-End Testing, Load Simulation & Security Hardening
- **Objective**: Rigorous validation of end-to-end flows, performance, and security rules.
- **Dependencies**: Phase 13.
- **Tasks**:
  - Write complete pytest integration suite covering ingestion, deduplication, and triage.
  - Run synthetic load test simulating 1,000 concurrent submissions.
  - Audit OWASP top 10, SQL injection prevention, and PII masking.
- **Expected Files**:
  - `back-end/tests/`, `scripts/simulate_disaster_burst.py`
- **Verification Criteria**: 100% test pass rate; zero security leaks; sub-second query response under load.
- **Manual Setup**: None.

---

### Phase 15: Demo Scenario Preparation & Presentation Packaging
- **Objective**: Prepare comprehensive demonstration scripts, realistic disaster scenarios (e.g., Cyclone landfall / Urban deluge), and judge presentation deck.
- **Dependencies**: Phase 14.
- **Tasks**:
  - Create deterministic multi-hazard seed datasets for key Indian metro regions (Mumbai, Chennai, Uttarakhand).
  - Prepare guided walkthrough script for SIH jury presentation.
- **Expected Files**:
  - `scripts/seed_demo_scenarios.py`, `docs/DEMO_GUIDE.md`
- **Verification Criteria**: One-command seed script reliably populates realistic, stunning demo data for live presentation.
- **Manual Setup**: None.
