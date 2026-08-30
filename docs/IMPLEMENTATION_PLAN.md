# Step-by-Step Implementation Roadmap

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)  
**Methodology**: Phased, incremental delivery with strict verification gates at each phase.

---

## Roadmap Overview

```
Phase 0: Project Initialization & Architectural Source of Truth   [COMPLETED & VERIFIED]
  │
  ├─► Phase 1: Repository Foundation, Tooling & Scaffolding       [COMPLETED & VERIFIED]
  │
  ├─► Phase 2: Local Infrastructure (PostgreSQL, Redis, MinIO)    [COMPLETED & VERIFIED]
  │
  ├─► Phase 3: Database Models, Spatial Schemas & Alembic         [COMPLETED & VERIFIED]
  │
  ├─► Phase 4: Citizen Reporting Flow & Media Storage             [COMPLETED & VERIFIED]
  │
  ├─► Phase 5: External Ingestion Adapters (IMD, NDMA, CWC, RSS)  [COMPLETED & VERIFIED]
  │
  ├─► Phase 6: Asynchronous Ingestion Pipeline (Redis Streams)    [COMPLETED & VERIFIED]
  │
  ├─► Phase 7: AI Intelligence — Categorization & Quality Gate    [COMPLETED & VERIFIED]
  │
  ├─► Phase 8: AI Intelligence — Spatial-Temporal Deduplication   [COMPLETED & VERIFIED]
  │
  ├─► Phase 9: AI Intelligence — Explainable Credibility Engine   [COMPLETED & VERIFIED]
  │
  ├─► Phase 10: Executive & Operator Dashboard (Leaflet GIS)      [COMPLETED & VERIFIED]
  │
  ├─► Phase 11: Administrative Triage & Verification Queue        [COMPLETED & VERIFIED]
  │
  ├─► Incident Intelligence Subsystem: Explorer & Deep Dive       [COMPLETED & VERIFIED]
  │
  ├─► Phase 13: Analytics Platform & Server Aggregation           [COMPLETED & VERIFIED]
  │
  ├─► Phase 12: Real-Time Event Streaming (Server-Sent Events)    [COMPLETED & VERIFIED]
  │
  ├─► Phase 14: Full-Product Hardening & Demonstration Packaging  [NEXT PHASE]
  │
  └─► Phase 15: Production Security & Enterprise RBAC             [FUTURE EXTENSION]
```

---

## 1. Completed & Verified Phases

### Phase 0: Project Initialization & Architectural Source of Truth
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Complete documentation suite under `/docs` (`PRD.md`, `ARCHITECTURE.md`, `TECH_STACK.md`, `DATA_MODEL.md`, `API_CONTRACT.md`, `EXTERNAL_SETUP.md`, `IMPLEMENTATION_PLAN.md`), agent guardrails in `AGENTS.md`.

### Phase 1: Repository Foundation, Tooling & Scaffolding
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: FastAPI backend foundation with strict linters (`ruff`, `mypy`, `pyrefly`), React 18 frontend with Vite, Tailwind CSS, and TanStack Query.

### Phase 2: Local Infrastructure & Container Orchestration
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: `docker-compose.yml` orchestrating PostgreSQL 16 with PostGIS 3.4, Redis 7, and MinIO S3 object storage.

### Phase 3: Database Models, Spatial Schemas & Alembic Migrations
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Declarative models in `back-end/app/models/` for reports, duplicate clusters, evidence items, physical observations, and verification events with PostGIS `SRID 4326` spatial point geometries and GiST indexing.

### Phase 4: Citizen Reporting Flow & S3 Media Storage
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: `POST /api/v1/reports` multipart intake, S3 signed image uploads to MinIO, public tracking lookup `GET /api/v1/reports/{id}`, citizen web reporting form.

### Phase 5: External Ingestion Adapters
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Resilient ingestion adapters for IMD Automatic Weather Stations, NDMA SACHET alerts, Central Water Commission (CWC) river gauges, Mastodon public feeds, and GDELT disaster news.

### Phase 6: Asynchronous Ingestion & Processing Pipeline
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Redis Streams event buffer (`event:raw_ingestion`), decoupled background workers, failure isolation, and deduplicated ingestion tracking.

### Phase 7: AI Intelligence — Rule & NLP Event Classification
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Event categorization engine for 6 primary disaster classes (`FLOOD_WATERLOGGING`, `CYCLONE_HIGH_WIND`, `HEAVY_RAINFALL`, `LANDSLIDE`, `HEATWAVE`, `HAILSTORM`, `OTHER_SEVERE`), input sanitization, and report quality scoring.

### Phase 8: AI Intelligence — Spatial-Temporal Deduplication & Clustering
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: PostGIS spatial radius matching ($R \le 2.5\text{ km}$), temporal windowing ($\Delta T \le 120\text{ min}$), cosine text similarity, automatic cluster centroid tracking (`duplicate_clusters`).

### Phase 9: AI Intelligence — Explainable Credibility Scoring Engine
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Deterministic multi-factor scorer combining base source prior, quality score, crowd volume signal, digital evidence provenance, physical station corroboration, and multi-source diversity multipliers with a transparent `credibility_explanation` breakdown and $0.9800$ ceiling cap.

### Phase 10: Executive & Operator Dashboard
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Interactive Leaflet map explorer (`LiveMapContainer`), viewport-aware GeoJSON queries (`/api/v1/geo/incidents`), KPI summary cards, and severity breakdown charts.

### Phase 11: Administrative Triage & Verification Queue
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**: Prioritized verification queue (`/api/v1/verification/queue`), operator triage actions (`POST verify`, `POST reject`, `POST mark-duplicate`), immutable audit events in `verification_events`, and status-aware review drawer.

### Incident Intelligence Subsystem: Explorer & Deep Dive
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**:
  - **Incident Explorer** (`/incidents`): Paginated, multi-filter operational incident list with credibility badges, hazard icons, and cluster summaries.
  - **Incident Deep-Dive** (`/incidents/:id`): 5-dimension intelligence inspection page rendering machine credibility breakdowns, duplicate cluster topology, linked digital evidence, physical AWS station observations, and pipeline stage telemetry.
  - **Emergency Operations Portal** (`/login`): Institutional operator access gateway for DEOC / SDRF / NDRF triage workflows.

### Phase 13: Analytics Platform & Server Aggregation
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**:
  - **Dashboard Summary Aggregation** (`GET /api/v1/dashboard/summary`): SQL-aggregated KPIs, diurnal distribution, category distribution, severity breakdown, and verification rates.
  - **Activity Trends API** (`GET /api/v1/analytics/trends`): Time-series bucketed volume and verification progression across 24h, 7d, 30d, and all-time windows.
  - **Regional Demographics API** (`GET /api/v1/analytics/regional`): Full-population two-tier regional aggregation (word-boundary city/state tokens + PostGIS spatial bounding envelope fallback).
  - **Analytics Interface** (`/analytics`): Fully server-aggregated analytics dashboard with zero client-side calculation loops or raw record dependency.

### Phase 12: Real-Time Event Streaming (Server-Sent Events)
- **Status**: **COMPLETED & VERIFIED**
- **Deliverables**:
  - **Transactional Outbox** (`realtime_outbox`): Atomically stages events inside domain mutation transactions in PostgreSQL with `SKIP LOCKED` batch claiming and exponential retry backoff.
  - **Outbox Worker Runtime** (`python -m app.workers.run_outbox_worker`): Standalone publisher process with adaptive draining, idle sleep, graceful `SIGTERM`/`SIGINT` shutdown, and scheduled 72-hour historical pruning.
  - **Streaming Transport** (`GET /api/v1/events/stream`): Persistent HTTP Server-Sent Events endpoint backed by Redis Streams (`stream:weather:realtime`, `MAXLEN ~ 10000`), comment heartbeats (15s), cursor replay via `Last-Event-ID`, and `system.resync_required` notifications.
  - **Frontend Realtime Manager** (`realtimeService.ts`): Root-level singleton with auto-reconnect, bounded FIFO queue (1,000 items) for `event_id` deduplication, and targeted React Query cache invalidation (`incidentKeys`, `dashboardKeys`, `analyticsKeys`).
  - **Live Browser Verification**: Verified live without manual refresh — test incident `"testinggg"` transitioned `PENDING` $\to$ `VERIFIED`, updating Pending Review from 2537 to 2536 and Verified Reports from 480 to 481.

---

## 2. Key Hardening Fixes & Semantic Corrections

During end-to-end runtime validation, the following architectural and presentation corrections were implemented and verified:

1. **Duplicate Cluster Singleton Semantics**: Singleton clusters (`total_member_count = 1`) display as `"1 Report"` / `"Single Incident Record"` with neutral informational badges rather than confusing `"Grouped Reports"` labels.
2. **Generic Stage Outcome Wording**: Updated generic stage execution outcome `SUCCESS_WITH_RESULTS` presentation mapping to **`"Results Found"`** (was `"Results Corroborated"`), preserving strict separation between pipeline execution and domain corroboration.
3. **Crowd Volume Signal Clarification**: Authoritative explanation builder updated to state: `"Crowd volume signal from {k} duplicate incident reports (sub-signal: {score})"` to explicitly convey diminishing-returns volume rather than $k$ independent confirmations.
4. **Credibility Assessment Timestamp Hierarchy**: `last_calculated_at` in `GET /incidents/{id}/credibility` now correctly serializes the machine assessment calculation timestamp using the safe hierarchy: `credibility_explanation.assessed_at` $\to$ `updated_at` $\to$ `created_at` $\to$ `now`.
5. **Status-Aware Verification Drawer**: Terminal verification states (`VERIFIED`, `REJECTED`, `DUPLICATE`) replace active intake mutation buttons with clean completed/closed state banners, preventing conflicting duplicate actions.
6. **Operator Access Route**: Added clean Emergency Operations Portal at `/login` with a catch-all fallback `<Route path="*" element={<Navigate to="/" replace />} />`.

---

## 3. Future Hardening & Roadmap Extensions

The following items are architected for subsequent production scale beyond the SIH MVP evaluation scope:

### Phase 14: Full-Product Hardening, Demo Scenarios & Gaps Audit
- **Objective**: Multi-hazard scenario simulations, end-to-end smoke test coverage, and hackathon presentation packaging (Mumbai Urban Deluge, Uttarakhand Flash Flood, Cyclone Landfall).

### Phase 15: Production Security & Enterprise RBAC
- **Objective**: Full OAuth2 / JWT role-based access control (RBAC), production container supervisor definitions (systemd / Kubernetes), multi-region Kafka stream migration, and signed cryptographic audit trails.
