# Product Requirements Document (PRD)

**Project Title**: National Weather Big Data Analytics Platform
**Smart India Hackathon 2026 — Problem Statement ID**: `SIH26069`
**Category**: Big Data Analytics / Disaster Management / Public Safety
**Target Beneficiaries**: National & State Disaster Response Forces (NDRF, SDRF), District Emergency Operations Centers (DEOCs), Municipal Corporations, Meteorological Analysts, and the General Public.

---

## 1. Executive Summary & Problem Context
Extreme weather phenomena (flash floods, urban waterlogging, cloudbursts, severe cyclonic storms, heatwaves, and hailstorms) have escalated in frequency and localized severity across India. While the India Meteorological Department (IMD) maintains advanced Doppler weather radars, satellite feeds, and Automatic Weather Stations (AWS), hyper-local micro-climate events often unfold at spatial scales smaller than the sensor grid.

Simultaneously, citizens and local responders on the ground capture real-time observations and imagery, yet this crowdsourced data suffers from noise, misinformation, duplicates, and lack of meteorological validation.

The **National Weather Big Data Analytics Platform (SIH26069)** solves this gap by synthesizing official government meteorological data, public feeds, and citizen crowdsourced reports into a unified, high-throughput intelligence pipeline. The platform performs real-time ingestion, AI-driven event classification, spatial-temporal deduplication, explainable credibility scoring, and geospatial visualization for rapid administrative verification and emergency response.

---

## 2. Requirement Classification Framework
To maintain rigorous documentation integrity, all platform requirements are divided into four distinct tiers:

```
┌───────────────────────────────────────────────────────────┐
│ 1. Explicit SIH Requirements (Foundational Mandate)       │
├───────────────────────────────────────────────────────────┤
│ 2. Submitted Solution Concepts (Baseline Product Concept) │
├───────────────────────────────────────────────────────────┤
│ 3. Engineering Decisions for MVP (Pragmatic Scope)        │
├───────────────────────────────────────────────────────────┤
│ 4. Future Scalability & Production Extensions             │
└───────────────────────────────────────────────────────────┘
```

---

## 3. Scope & Requirement Breakdown

### Tier 1: Explicit SIH Requirements
- **Big Data Analytics Engine**: Ability to ingest, process, and analyze heterogeneous weather data streams from multiple sources at scale. — **IMPLEMENTED** (Adapters for IMD, NDMA, CWC, Mastodon, GDELT + server-side analytics API).
- **National Scale Geospatial Processing**: High-performance querying of spatial coordinates, bounding boxes, administrative boundaries, and proximity radii across Indian states and districts. — **IMPLEMENTED** (PostGIS `SRID 4326` + GiST indexes + bounded GeoJSON vector endpoint).
- **Decision Support for Disaster Management**: Actionable intelligence, severity metrics, and early trend detection for disaster response bodies. — **IMPLEMENTED** (Executive Dashboard, LiveMap, Verification Queue, Explainable Credibility Scorer).

### Tier 2: Submitted Solution Baseline Concepts
- **Citizen Weather & Event Reporting**: Mobile-friendly citizen reporting form with photo upload, reverse geocoding, and instant reference tracking ID. — **IMPLEMENTED** (`/report`, `/track-report`, `POST /api/v1/reports`).
- **Multi-Source Ingestion**: Ingestion of IMD weather station observations, NDMA SACHET alerts, CWC river telemetry, Mastodon posts, and GDELT disaster news. — **IMPLEMENTED** (`back-end/app/ingestion/`).
- **Intelligence & Triage Pipeline**:
  - Automated syntactic and semantic validation. — **IMPLEMENTED**
  - Event classification (6 disaster categories). — **IMPLEMENTED**
  - Duplicate detection and spatial-temporal clustering ($R \le 2.5\text{ km}$, $\Delta T \le 120\text{ min}$). — **IMPLEMENTED**
  - Explainable credibility scoring ($0.0000$ to $0.9800$) with transparent component breakdown. — **IMPLEMENTED**
  - Meteorological sensor corroboration against proximate IMD AWS and CWC river gauges. — **IMPLEMENTED**
- **Centralized Data Storage**: PostgreSQL 16 + PostGIS unified repository with spatial GiST indexing and MinIO binary media storage. — **IMPLEMENTED**
- **Real-Time Interactive Dashboard**:
  - Dynamic Map Explorer displaying live events with Leaflet and bounded GeoJSON layers. — **IMPLEMENTED**
  - Multi-dimensional filtering (Category, Severity, Status, Bounding Box, Time Range). — **IMPLEMENTED**
  - Server-aggregated KPI cards, temporal trends, and regional risk summaries. — **IMPLEMENTED**
- **Administrative Verification Queue**:
  - Prioritized triage queue for authorized disaster management officers. — **IMPLEMENTED**
  - Side-by-side evidence inspection (photos, sensor readings, AI credibility breakdown). — **IMPLEMENTED**
  - Triage actions: Verify, Reject, Flag Duplicate, or Place Under Review. — **IMPLEMENTED**

### Tier 3: Engineering Decisions for MVP (Current Build Scope)
- **Primary System of Record**: PostgreSQL 16+ with PostGIS spatial extension. — **IMPLEMENTED**
- **Media Storage**: S3-compatible Object Storage (MinIO locally) with SHA-256 integrity verification. — **IMPLEMENTED**
- **Transactional Real-Time Outbox & SSE**: PostgreSQL outbox table, independent worker process, Redis Streams buffer (`stream:weather:realtime`), and FastAPI Server-Sent Events (`/api/v1/events/stream`). — **IMPLEMENTED**
- **State Machine for Verification**: Explicit states: `PENDING`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `DUPLICATE`. — **IMPLEMENTED**
- **Lightweight AI / NLP**: Local text embedding vector similarity (FastEmbed) for semantic duplicate grouping. — **IMPLEMENTED**
- **Single Monorepo Architecture**: Clean separation between `/front-end` (React + Vite + Tailwind + shadcn/ui) and `/back-end` (FastAPI + SQLAlchemy 2.0 Async + Pydantic v2). — **IMPLEMENTED**

### Tier 4: Future Scalability & Production Extensions
- **Enterprise Messaging**: Migration from Redis Streams to Apache Kafka for multi-region streaming. — **FUTURE EXTENSION**
- **Multimodal Deep Learning**: Fine-tuned Vision-Language Models (VLM) for flood depth estimation from citizen photos. — **FUTURE EXTENSION**
- **CAP Dissemination**: Automated outbound Common Alerting Protocol broadcast to NDMA SACHET. — **FUTURE EXTENSION**
- **Production RBAC / JWT**: Institutional OAuth2 / JWT bearer authentication and role permissions. — **DEFERRED PRODUCTION HARDENING**

---

## 4. User Personas & Core Workflows

```mermaid
journey
    title Core User Journeys
    section Citizen Reporting
      Spot severe waterlogging: 5: Citizen
      Open citizen web app: 5: Citizen
      Capture photo & GPS pin: 5: Citizen
      Submit report: 5: Citizen
      Receive reference tracking ID: 5: Citizen
    section Automated Ingestion & Intelligence
      Redis stream ingestion: 5: Platform
      Deduplication & Clustering: 5: Platform
      IMD Sensor Corroboration: 5: Platform
      Credibility Scoring (0.0-1.0): 5: Platform
    section Disaster Management / Admin
      Inspect Live Verification Queue: 5: DEOC Officer
      Review high-credibility flood cluster: 5: DEOC Officer
      Confirm verification: 5: DEOC Officer
      Observe Real-Time Dashboard Update: 5: DEOC Officer
```

---

## 5. Non-Functional Requirements (NFRs) & Scope Calibration

| Dimension | Target Specification & Implementation Reality | Status |
| :--- | :--- | :---: |
| **Ingestion Latency** | End-to-end ingestion and initial scoring in $< 1.5\text{ seconds}$ under standard load. | **MET** |
| **Map Rendering** | Bounded GeoJSON query returning up to 500 spatial features (`LIMIT 500`) for 60 FPS Leaflet rendering; macro totals derived authoritatively from `/api/v1/dashboard/summary`. | **MET** |
| **Availability & Resilience** | Pluggable adapter isolation; failure of external feeds does not block citizen intake or dashboard availability. | **MET** |
| **Data Integrity** | Zero data loss for accepted citizen submissions; media SHA-256 checksums stored for auditability. | **MET** |
| **Security & Privacy** | Citizen phone numbers and sensitive operator notes redacted from public endpoints; production OAuth2/JWT RBAC deferred. | **MET (MVP Boundary)** |
