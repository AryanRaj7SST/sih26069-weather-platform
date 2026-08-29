# System Architecture & Technical Design

**Problem Statement ID**: `SIH26069`  
**Platform**: National Weather Big Data Analytics Platform

---

## 1. High-Level Architecture Overview

The system is architected as an asynchronous, event-driven data processing pipeline backed by a high-performance spatial database and modern reactive frontend. 

```mermaid
flowchart TD
    subgraph Data_Sources["Data Sources & Ingestion Layer"]
        C_SRC["Citizen Submissions (Web App)"]
        IMD_SRC["IMD AWS / Alerts (Open Feeds)"]
        RSS_SRC["Disaster RSS / Open Feeds"]
        DGOV_SRC["Data.gov.in Portals"]
        DEMO_SRC["Simulated Social / Public Feeds"]
    end

    subgraph Ingestion_Adapters["Pluggable Ingestion Adapters"]
        ADAPT["Adapter Layer (Normalization, Schema Validation, Idempotency)"]
    end

    subgraph Streaming_Buffer["Buffering & Queueing"]
        R_STREAM["Redis Stream (event:raw_ingestion)"]
    end

    subgraph Intelligence_Engine["Intelligence & Analytics Engine"]
        SPAM["1. Spam & Anomaly Filter"]
        CLASS["2. Event Classifier (Rule-based + NLP)"]
        DEDUP["3. Deduplication & Spatial-Temporal Clustering (FastEmbed + PostGIS)"]
        CORROB["4. IMD Sensor Corroboration"]
        CRED["5. Explainable Credibility Scoring"]
    end

    subgraph Storage_Layer["System of Record & Storage"]
        PG[("PostgreSQL 16 + PostGIS\n(Entities, Spatiotemporal Indexes, Metrics)")]
        MINIO[("MinIO / S3 Object Storage\n(Media Photos/Videos/Blobs)")]
        R_CACHE[("Redis Cache\n(Aggregations & Leaderboards)")]
    end

    subgraph API_Realtime["API & Real-time Layer"]
        FASTAPI["FastAPI REST Application"]
        SSE_PUB["Real-time Notification Channel (SSE / WS)"]
    end

    subgraph Frontend_App["Presentation Layer (React + Vite + Leaflet + Recharts)"]
        MAP_EXP["Interactive Map Explorer"]
        DASH["Analytics Dashboard & KPI Cards"]
        QUEUE["Admin Verification & Triage Queue"]
        CITIZEN_UI["Citizen Reporting Web Portal"]
    end

    C_SRC --> ADAPT
    IMD_SRC --> ADAPT
    RSS_SRC --> ADAPT
    DGOV_SRC --> ADAPT
    DEMO_SRC --> ADAPT

    ADAPT -->|Raw Payloads| R_STREAM
    ADAPT -->|Media Uploads| MINIO

    R_STREAM --> Intelligence_Engine
    SPAM --> CLASS --> DEDUP --> CORROB --> CRED

    CRED -->|Persist Records & Clusters| PG
    CRED -->|Update In-Memory Fast Lookup| R_CACHE
    CRED -->|Publish Verified/Live Events| SSE_PUB

    PG <--> FASTAPI
    R_CACHE <--> FASTAPI
    FASTAPI <--> Frontend_App
    SSE_PUB -.->|Push Live Updates| Frontend_App
```

---

## 2. Ingestion Subsystem (Pluggable Adapters)

To guarantee extensibility across heterogeneous data feeds, all ingestion modules implement a standardized `BaseIngestionAdapter` interface.

```
back-end/app/ingestion/
├── base.py              # BaseIngestionAdapter abstract interface
├── registry.py          # Adapter registration and discovery
├── citizen/             # Citizen crowdsourced submissions
├── imd/                 # India Meteorological Department API / AWS scraper
├── rss/                 # National Disaster Management & Weather RSS feeds
├── data_gov/            # Data.gov.in open weather data integration
└── seed_demo/           # Deterministic demo generator for testing & demonstrations
```

### Integration Status Matrix

| Source Category | Integration Status | Protocol / Format | Polling / Push | Error Handling Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Citizen Reports** | **REAL INTEGRATION** | HTTP `multipart/form-data` | Real-time Push | Immediate client validation + async queuing |
| **IMD AWS / Alerts** | **REAL INTEGRATION** | HTTP REST / JSON / XML | Periodic Polling (5–15 min) | Exponential backoff with local fallback cache |
| **Public RSS Feeds** | **REAL INTEGRATION** | XML / Atom / GeoRSS | Periodic Polling (10 min) | Idempotent GUID deduplication |
| **Data.gov.in** | **PLANNED INTEGRATION** | OGD Platform API (JSON) | Hourly Polling | Rate-limited polling with API key rotation |
| **Social Media Feeds** | **DEMO/SEED SOURCE** | Synthetic JSON Generator | Event-driven simulation | Seed stream labeled as synthetic |

---

## 3. Intelligence Pipeline Architecture

The intelligence pipeline processes incoming reports sequentially before committing finalized state to the database:

```mermaid
flowchart LR
    A["Raw Ingestion Payload"] --> B["1. Validation & Cleansing"]
    B --> C["2. Event Classification"]
    C --> D["3. Spatial-Temporal Clustering"]
    D --> E["4. Sensor Corroboration"]
    E --> F["5. Explainable Credibility Calculation"]
    F --> G["6. Triage Queue Assignment"]
```

### Step 1: Validation & Cleansing
- Geospatial boundary checks (valid lat/long coordinates within Indian territory `[6.0, 68.0]` to `[38.0, 98.0]`).
- Time sanity checks (rejection of timestamps skewed $> 24\text{ hours}$ in future or $> 7\text{ days}$ in past).
- Media file integrity validation (MIME sniffing, file size limit $\le 15\text{ MB}$, SHA-256 hash).

### Step 2: Event Classification
- Multi-hazard taxonomy assignment:
  - `FLOOD_WATERLOGGING`
  - `THUNDERSTORM_LIGHTNING`
  - `CYCLONE_HIGH_WIND`
  - `HEAVY_RAINFALL`
  - `LANDSLIDE`
  - `HEATWAVE`
  - `HAILSTORM`
  - `OTHER_SEVERE`
- Hybrid classification: Rule-based keyword engine combined with lightweight vector similarity.

### Step 3: Spatial-Temporal Deduplication & Clustering
- Spatial window: radius $R \le 2.5\text{ km}$ via PostGIS `ST_DWithin`.
- Temporal window: time difference $\Delta T \le 120\text{ minutes}$.
- Text semantic similarity: Cosine distance $< 0.25$ over FastEmbed vector embeddings.
- Matching reports are grouped into a `duplicate_clusters` entity with a designated primary report.

### Step 4: Meteorological Corroboration
- Spatial query for the nearest IMD Automatic Weather Station (AWS) within a $25\text{ km}$ radius.
- Corroboration check: If citizen reports heavy rain ($> 30\text{ mm/hr}$) and the nearest AWS records $> 20\text{ mm/hr}$ precipitation within $\pm 2\text{ hours}$, boost corroboration confidence.

### Step 5: Explainable Credibility Scoring Algorithm
Credibility is calculated as a deterministic, mathematically bounded composite score ($C \in [0.0000, 0.9800]$):

1. **Base Trust Prior Anchor ($B$)**:
   $$B = w_{\text{prior}} S_{\text{prior}} + w_{\text{qual}} S_{\text{qual}}$$
   Anchored on source family reliability ($S_{\text{prior}} \in [0.40, 1.00]$) and report quality ($S_{\text{qual}}$).

2. **External Corroboration Support ($S_{\text{support}}$)**:
   $$S_{\text{support}} = \min\left(1.0, 0.30 S_{\text{crowd}} + 0.50 S_{\text{evidence}} + 0.50 S_{\text{observation}}\right)$$
   - $S_{\text{crowd}} \in [0.0, 1.0]$: Crowd volume signal with diminishing returns ($1.0 - \exp(-(k - 1) / 3.0)$ for $k$ cluster members).
   - $S_{\text{evidence}} \in [0.0, 1.0]$: Grouped digital evidence score with logarithmic diminishing returns per provenance group ($1.0 + 0.20 \ln(1 + \text{count} - 1)$).
   - $S_{\text{observation}} \in [0.0, 1.0]$: Physical sensor corroboration from nearby IMD Automatic Weather Stations and CWC river gauges.

3. **Multi-Source Diversity Multiplier ($D$)**:
   $$D = 1.0 + 0.06 \times (n_{\text{independent\_families}} - 1)$$
   Calculated across participating distinct source families (`CITIZEN`, `IMD_AWS`, `CWC_GAUGE`, `NEWS_GDELT`, `NDMA_SACHET`, `SOCIAL_MASTODON`).

4. **Corroboration Lift ($\Delta$) & Bounded Ceiling**:
   $$\Delta = (1.0 - B) \times \min\left(1.0, S_{\text{support}} \times D\right)$$
   $$C = \min\left(B + \Delta - P_{\text{contradiction}}, 0.9800\right)$$

The response payload exposes the exact driver breakdown and uncertainty flags in a structured `credibility_explanation` document.

### Step 6: Verification State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: Ingestion Complete
    PENDING --> UNDER_REVIEW: Operator Opens Triage
    PENDING --> VERIFIED: Operator Confirms Ground Truth
    PENDING --> REJECTED: Operator Marks False/Hoax
    PENDING --> DUPLICATE: Operator Merges into Cluster
    UNDER_REVIEW --> VERIFIED: Operator Confirms Ground Truth
    UNDER_REVIEW --> REJECTED: Operator Marks False/Hoax
    UNDER_REVIEW --> DUPLICATE: Operator Merges into Cluster
    VERIFIED --> [*]: Terminal State (Completed)
    REJECTED --> [*]: Terminal State (Closed)
    DUPLICATE --> [*]: Terminal State (Closed)
```

---

## 4. Centralized Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL 16 + PostGIS                  │
│  - System of Record                                         │
│  - Spatial Geometry Columns (SRID 4326)                     │
│  - GiST Indexes for Ultra-Fast Proximity Queries            │
│  - Full Relational Integrity (Foreign Keys, Constraints)    │
└─────────────────────────────────────────────────────────────┘
                               ▲
                               │ Metadata & S3 Keys
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                MinIO / S3 Object Storage                    │
│  - Citizen Incident Photos (JPEG, PNG, WebP)                │
│  - Video Clips (MP4, WebM)                                  │
│  - Raw Unstructured Satellite / Radar Raster Artifacts      │
└─────────────────────────────────────────────────────────────┘
                               ▲
                               │ Invalidation / Streams
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Redis 7+ (In-Memory Tier)                  │
│  - Redis Streams (event buffer for async worker consumers)  │
│  - Spatial Geohash Caching for Map Tile Rendering           │
│  - Real-time Pub/Sub for Server-Sent Events (SSE)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Real-Time Event & Notification Flow

1. **Submission Event**: Citizen submits a report $\rightarrow$ FastAPI validates payload and generates an S3 presigned URL for media.
2. **Stream Enqueue**: Event metadata is pushed onto Redis Stream `stream:weather:events`.
3. **Worker Processing**: Background worker consumes from Redis Stream, executes classification, clustering, sensor corroboration, and credibility calculation, then commits to PostgreSQL.
4. **Broadcast Channel**: On state transition or high-severity detection, worker publishes notification to Redis Pub/Sub `pubsub:weather:updates`.
5. **Client Stream (SSE)**: FastAPI SSE endpoint streams JSON updates to connected Disaster Management Dashboards without requiring page polling.

---

## 6. Frontend Presentation Architecture

The user interface is engineered as an enterprise-grade disaster intelligence platform built with React, Vite, Tailwind CSS, and shadcn/ui.

### Planned Application Screens

```
front-end/src/pages/
├── 1. Landing / Public Overview        (Home, current national weather bulletin, CTA)
├── 2. Citizen Report Portal            (Mobile-friendly report submission form with map pin)
├── 3. Report Status & Tracking         (Tracking reference view, processing status)
├── 4. Main Disaster Dashboard          (KPI metrics, regional severity breakdown, live feed)
├── 5. Interactive Map Explorer         (Leaflet GIS map, heatmaps, layer toggles, cluster pins)
├── 6. Incident Detail View             (Deep dive, media viewer, sensor corroboration, credibility breakdown)
├── 7. Admin Authentication             (Secure login with MFA and role verification)
├── 8. Admin Verification Queue         (Triage backlog with bulk filtering and urgency ranking)
├── 9. Admin Review & Triage Detail     (Side-by-side evidence inspection, verification action panel)
├── 10. Analytics & Trend Analysis      (Recharts historical trends, seasonal flood curves, hazard frequency)
└── 11. System Health & Sources Status  (Data pipeline latency, adapter uptime, error telemetry)
```
