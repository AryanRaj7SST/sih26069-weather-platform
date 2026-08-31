# National Weather Big Data Analytics Platform (SIH26069)
# End-User & Administrator Operating Manual

---

## 1. Platform Mission & Overview

The **National Weather Big Data Analytics Platform** is an AI-augmented big data analytics and situational awareness system developed for Smart India Hackathon 2026 (Problem Statement ID: `SIH26069`).

During severe meteorological events (urban waterlogging, flash floods, landslides, heavy rainfall, cyclones, thunderstorms, and heatwaves), disaster management authorities need to quickly separate credible ground reports from noise and duplicates while cross-referencing on-ground reports with physical sensors.

This platform bridges that gap by:
1. Ingesting multi-source data (citizen mobile/web reports with photo/video uploads, NDMA SACHET disaster alerts, CWC river gauge telemetry, GDELT news feeds, and Mastodon emergency posts).
2. Automatically grouping duplicate reports using spatial-temporal candidate bounding and domain-boosted text vectorization (`sparse_tfidf_ngram_v1`).
3. Calculating an explainable mathematical credibility score ($0.0000$ to $0.9800$) based on source trust, report quality, crowd volume, digital evidence, and physical sensor delta.
4. Corroborating reports reactively when late news articles or river observations arrive.
5. Providing real-time operations dashboards, an interactive situational GIS map, and an administrative verification queue for disaster authorities (**NDRF, SDRF, DEOCs**).

---

## 2. Target User Personas & Permissions

| User Persona | Primary Interface | Available In-Platform Capabilities |
| :--- | :--- | :--- |
| **Public Citizen / Ground Observer** | Home (`/`), Report Intake (`/report`), Report Tracking (`/track-report`). | Submit localized weather reports with photos/GPS, receive a unique Tracking ID, inspect processing status and verification timeline. |
| **Emergency Control Room Operator (DEOC / SDRF / NDRF)** | Operator Gateway (`/login`), Verification Queue (`/admin/queue`), Executive Dashboard (`/dashboard`), Live Map (`/live-map`), Incident Explorer (`/incidents`), Deep-Dive (`/incidents/:id`). | Triage incoming reports prioritized by severity and machine credibility, inspect supporting evidence and physical sensor data, execute verification actions (`VERIFIED`, `UNDER_REVIEW`, `REJECTED`, `DUPLICATE`), and view audit history. |
| **Disaster Analyst & Command Leadership** | Analytics Platform (`/analytics`), Situational GIS Map (`/live-map`). | Inspect regional incident distributions, 24h/7d activity trends, and multi-source corroboration density across districts. |

---

## 3. Application Navigation & Screen Inventory

The current frontend contains 10 user-facing screens, identified and documented below, accessible via desktop header navigation and mobile bottom navigation:

```
[ Navigation Structure ]
├── Home (/)                     → Public advisories, map preview, and recent verified reports
├── Submit Report (/report)      → Single-page citizen report intake form with 6 logical sections
├── Track Report (/track-report) → Tracking ID search, 4-step progress stepper, trust score card
├── Dashboard (/dashboard)       → Executive KPI cards, regional/hazard filters, situational mini-map
├── Live Map (/live-map)         → Full-screen Leaflet GIS interactive incident map (500-feature bound)
├── Incidents (/incidents)       → Searchable incident directory with multi-dimension filters
├── Analytics (/analytics)       → Macro temporal trends (24h/7d/30d), regional breakdown charts
└── Operator Portal (/login)     → Operator context gateway for DEOC / SDRF / NDRF triage personnel
    └── Verification Queue (/admin/queue or /verification) → Priority triage queue & action drawer
```

---

## 4. Public Citizen Guide: Submitting a Weather Report

Citizens can submit localized incident reports directly through modern mobile and desktop web browsers without creating an account.

### 4.1 Form Structure & Submission Fields (`/report`)

The intake form on `/report` is a single-page structured form containing 6 logical sections:

1. **Location Section (`LocationSection`)**:
   - **GPS Auto-Fill**: Click **"Use Current Location"** to allow browser geolocation to populate latitude and longitude coordinates.
   - **Manual Coordinates**: If GPS is unavailable, enter latitude ($-90$ to $+90$) and longitude ($-180$ to $+180$) manually (default fallback: Mumbai central `19.0760, 72.8777`).
   - **Location Landmark**: Enter a descriptive location or landmark name (e.g., *"Near Dadar Station, Mumbai"*).
2. **Hazard Category Section (`CategorySection`)**:
   - Select the primary observed weather event:
     - `HEAVY_RAINFALL` — Torrential rain / cloudburst
     - `FLOODING` — River / coastal inundation
     - `WATERLOGGING` — Urban street submergence / drainage overflow
     - `CYCLONE` — Severe storm / high-velocity gales
     - `LANDSLIDE` — Mudslide / slope failure
     - `THUNDERSTORM` — Lightning / squalls
     - `HEATWAVE` — Extreme heat conditions
     - `AIR_QUALITY` — Smog / hazardous AQI
     - `OTHER` — Unclassified hazard
3. **Severity Rating Section (`SeveritySection`)**:
   - Choose the perceived severity pill:
     - `LOW` — Minor inconvenience, normal traffic movement
     - `MODERATE` — Notable impact, localized delays
     - `HIGH` — Dangerous conditions, property risk, road closures
     - `SEVERE` — Immediate life threat, structural destruction, evacuation needed
4. **Additional Details Section (`AdditionalDetailsSection`)**:
   - **Title (Required)**: 3 to 255 characters summarizing the event (e.g., *"Severe waterlogging under Kurla railway bridge"*).
   - **Description (Optional)**: Up to 5,000 characters detailing depth, trapped vehicles, or power outages.
   - **Occurred At (Optional)**: Time of incident if reporting after the event.
5. **Media Attachment Section (`MediaUploadSection`)**:
   - Upload up to **3 media files** (photos or short video clips).
   - **Accepted Formats**: `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/quicktime` (`.mov`).
   - **Size Limit**: Maximum **15 MB** per file. Files are uploaded directly to MinIO Object Storage with SHA-256 validation; binary media is never stored directly in the database.
6. **Contact Information Section (`ContactInfoSection`) [Optional]**:
   - Reporter name and phone/email for emergency verification contact.

### 4.2 Submission Outcome & Tracking ID

- Submitting the form sends a `multipart/form-data` request to `POST /api/v1/reports`.
- The report is persisted in PostgreSQL `weather_reports` with initial status `processing_status = 'QUEUED'` and `verification_status = 'PENDING'`.
- A unique **Tracking ID** is assigned (format: `RPT-YYYYMMDD-XXXXXXXX`, e.g., `RPT-20260831-B848D18A`).
- A **Success Modal** is displayed showing:
  - The assigned Tracking ID.
  - A copyable tracking link and QR code.
  - A direct link to track report progress at `/track-report?id=...`.

---

## 5. Public Citizen Guide: Tracking Your Report

Citizens can check the real-time processing and administrative verification status of any submitted report at `/track-report`.

### 5.1 Lookup & Information Cards (`/track-report`)

1. Enter the alphanumeric tracking ID (e.g., `RPT-20260831-B848D18A`) into the search bar.
2. The page renders 4 authoritative information cards:
   - **Report Status Banner**: Current administrative verification status badge (`PENDING`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `DUPLICATE`), assigned severity, and submission timestamp.
   - **Verification Pipeline Stepper (UI Visualization)**:
     - Stage 1: *Report Intake* (Timestamped and validated)
     - Stage 2: *Automated Corroboration* (Location verified, duplicate clustered, AWS sensors evaluated)
     - Stage 3: *Authority Verification* (Operator triage assessment)
     - Stage 4: *Operational Outcome* (`VERIFIED`, `REJECTED`, `DUPLICATE`, or awaiting decision)
   - **Trust & Credibility Score Card**: Displays the machine credibility score ($0.0000$ to $0.9800$ or percentage) with source trust and quality indicators.
   - **Location & Submitted Evidence Cards**: Displays the mini Leaflet map marker and uploaded media attachments.

---

## 6. Background Processing Sequence: Automated Pipeline

When a citizen submits a report or an external feed publishes an alert, the system executes an automated, decoupled background chain:

```
[ Citizen Form / External Feed ]
              ↓
  1. POST /api/v1/reports
              ↓
  2. PostgreSQL DB Persistence (weather_reports, status = 'QUEUED')
     + Transactional Outbox (realtime_outbox, event = 'incident.ingested')
              ↓
  3. Outbox Relay Worker (run_outbox_worker)
     Polls outbox (SKIP LOCKED), publishes to Redis Streams
              ↓
  4. Redis Stream Buffer (stream:weather:orchestration)
              ↓
  5. Orchestration Dispatcher (run_dispatcher)
     Executes 5-Stage IncidentPipeline:
       Stage 1: LOCATION    → PostGIS geocoding & boundary validation
       Stage 2: DUPLICATE   → PostGIS radius (2.5km, 3h) + TF-IDF n-gram vectorizer
       Stage 3: EVIDENCE    → GDELT news & Mastodon post spatial-temporal matching
       Stage 4: OBSERVATION → IMD AWS / CWC river gauge proximity corroboration
       Stage 5: CREDIBILITY → Multi-factor mathematical scoring (0.0000 to 0.9800)
              ↓
  6. Database Persistence (status = 'COMPLETED', readiness = 'INTELLIGENCE_READY')
     + Outbox Write (realtime_outbox, event = 'report.intelligence_ready')
              ↓
  7. Outbox Worker relays to stream:weather:realtime
              ↓
  8. FastAPI Server-Sent Events (/api/v1/events/stream)
              ↓
  9. Frontend RealtimeService (Singleton EventSource)
              ↓
 10. React Query Cache Invalidation (Live Dashboard / Queue / Map Update without Refresh)
```

> [!NOTE]
> Users do not need to refresh the page or trigger processing manually. The entire pipeline executes asynchronously in the background.

---

## 7. Operations Dashboard Guide (`/dashboard`)

The Executive Operations Dashboard provides emergency control room personnel with macro situational awareness across active incidents.

### 7.1 Key Performance Indicator (KPI) Cards

- **Total Active Events**: Total count of weather incidents matching the active filter scope. Sourced from PostgreSQL server-side aggregation (`GET /api/v1/dashboard/summary`).
- **Critical & Severe Incidents**: Count of incidents flagged with `HIGH` or `SEVERE` severity.
- **Verified Incidents**: Number of incidents confirmed by disaster management operators (`verification_status = 'VERIFIED'`).
- **High Credibility Reports**: Number of incidents evaluated with algorithmic credibility score $\ge 0.70$.

### 7.2 Interactive Filter Bar

Filters combine dynamically across summary KPIs, charts, and map layers:
- **Time Range**: `24h` (last 24 hours), `48h` (last 48 hours), `7d` (last 7 days), `ALL` (all-time).
- **Hazard Category**: Filter by hazard (`FLOODING`, `HEAVY_RAINFALL`, `CYCLONE`, etc.) or `ALL`.
- **Region**: Filter by geographic bounding boxes (`MUMBAI_MMR`, `DELHI_NCR`, `BENGALURU_URBAN`, `CHENNAI_METRO`, `ASSAM_VALLEY`, `ALL`).
- **Verification Status**: Filter by `ALL`, `PENDING`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `DUPLICATE`.

### 7.3 Visual Analytics & Recent Incident Feed

- **Incident Trend Card**: Multi-hour/day line chart showing incident submission frequency.
- **Hazard Distribution Card**: Donut chart breakdown showing proportions of rainfall vs. flooding vs. storm damage.
- **Verification Status Card**: Bar breakdown of triage progress.
- **Situational Map Widget**: Embedded interactive Leaflet mini-map displaying geo-located incidents.
- **Recent Incident Feed**: Bounded list of the 6 most recent reports with direct click-through to the deep-dive intelligence page (`/incidents/:id`).

---

## 8. Situational GIS Map Guide (`/live-map`)

The Situational Live Map provides a full-viewport geospatial command interface for spatial analysis.

### 8.1 Map Features & Controls

- **Interactive Pan & Zoom**: Standard Leaflet map gestures with custom zoom controls and administrative boundaries.
- **Severity-Coded Markers**:
  - 🔴 **Red**: `SEVERE` incident
  - 🟠 **Orange**: `HIGH` incident
  - 🟡 **Yellow**: `MODERATE` incident
  - 🟢 **Green**: `LOW` incident
- **Incident Slide-Over Drawer**: Clicking any map marker opens a slide-over panel displaying:
  - Incident Title, Hazard Badge, Severity, and Location Name.
  - Machine Credibility Score and Classification.
  - Administrative Verification Status.
  - Linked Digital Evidence & Physical Station Telemetry summaries.
  - Direct button: **"Open Full Intelligence Deep-Dive"** (`/incidents/:id`).
- **Map Filter Controls**: Floating top bar to toggle time windows (`24h`, `48h`, `7d`, `ALL`), hazard categories, and operational verification statuses.

> [!IMPORTANT]
> **The 500-Feature Rendering Bound**: GeoJSON map queries enforce an intentional server-side bound (`LIMIT 500` on `GET /api/v1/geo/incidents`). This protects browser memory and rendering performance during high-volume event spikes. Summary KPI totals remain authoritatively computed across all records in the database.

---

## 9. Incident Intelligence Deep-Dive Guide (`/incidents/:id`)

The Incident Deep-Dive screen provides a 5-dimension inspection view for any weather report in the system.

```
[ Incident Detail Header: Title, Tracking ID, Hazard Badge, Severity, Verification Status, Readiness ]
  ├── 1. Machine Credibility Section (Score, Prior, Quality, Crowd, Evidence, Physical Delta, Diversity)
  ├── 2. Pipeline Execution Telemetry (LOCATION, DUPLICATE, EVIDENCE, OBSERVATION, CREDIBILITY)
  ├── 3. Duplicate Cluster Section (Spatial Radius, Centroid, Cluster Size, Linked Duplicate IDs)
  ├── 4. Linked Digital Evidence (GDELT News Articles, Mastodon Social Posts, Relevance Tiers)
  ├── 5. Physical Station Observations (IMD AWS Rainfall, CWC River Gauge Levels, Distance, Delta)
  └── 6. Media Gallery & Geolocation Mini-Map (MinIO Uploaded Photos/Videos with SHA-256 Hashes)
```

---

## 10. Explainable Machine Credibility Guide

The platform uses a deterministic, transparent scoring engine ($0.0000$ to $0.9800$) rather than an unexplainable black-box AI model.

### 10.1 Score Formula Breakdown

$$\text{Score} = \min\left(0.98, \left[\text{Prior} \times \text{Quality} + \sum \text{Signals} - \text{Penalties}\right] \times \text{Diversity}\right)$$

1. **Source Class Prior Trust**:
   - `OFFICIAL_PORTAL` / `IMD_AWS` / `NDMA_SACHET`: Prior = $0.85$ – $0.92$
   - `CITIZEN_REPORT` (Anonymous / Web): Prior = $0.60$
   - `SOCIAL_MEDIA`: Prior = $0.40$
2. **Report Quality Factor**: Scored between $0.70$ and $1.00$ based on coordinate precision, description length, and validated photo attachment.
3. **Crowd Volume Signal**:
   - Duplicate reports clustered within $2.5\text{ km}$ and $3\text{ hours}$ contribute a diminishing-returns reinforcement signal ($+0.05$ to $+0.30$).
   - Duplicate reports are **never** summed as independent proofs.
4. **Digital Evidence Provenance Signal**:
   - Matched GDELT news articles and Mastodon emergency posts add $+0.10$ to $+0.35$ depending on relevance tier (`SUPPORTING`, `RELATED`, `CONTEXTUAL`).
5. **Physical Station Telemetry Delta**:
   - Proximity to automated weather stations (IMD AWS) or river gauges (CWC) recording corroborating conditions (e.g., rainfall $\ge 20\text{mm/h}$ or river level above warning stage) adds $+0.15$ to $+0.50$.
6. **Cross-Source Diversity Multiplier**:
   - When an incident has confirmations across multiple independent provenance tiers (Citizen + Sensor + News), a $+6\%$ diversity multiplier is applied.
7. **Machine Credibility Hard Ceiling**:
   - Uncorroborated single citizen report cap: $\le 0.6500$
   - Absolute algorithmic ceiling: $\le 0.9800$ (No automated system reaches $1.0000$; ground truth is reserved for human verification).

### 10.2 Credibility Classification Tiers

| Score Range | Classification Badge | Operational Meaning |
| :---: | :--- | :--- |
| **0.80 – 0.98** | `VERY_HIGH` | Strongly corroborated by multiple physical sensors and independent digital evidence. |
| **0.65 – 0.79** | `HIGH` | Verified source prior with high report quality or positive local sensor corroboration. |
| **0.45 – 0.64** | `MODERATE` | Plausible citizen report with standard metadata; awaiting secondary sensor confirmation. |
| **0.25 – 0.44** | `LOW` | Uncorroborated, sparse details, or minor sensor contradiction. |
| **0.00 – 0.24** | `VERY_LOW` | High contradiction against physical baselines or flagged as probable hoax/spam. |

> [!IMPORTANT]
> **Machine Credibility $\ne$ Human Verification**: The credibility score is an automated algorithmic assessment. It assists operators in prioritizing triage but does not change the incident's operational status.

---

## 11. Spatial-Temporal Duplicate Detection Guide

When multiple citizens submit reports about the same localized incident, the platform groups them into a `DuplicateCluster`.

### 11.1 The Duplicate Detection Algorithm

The live production duplicate detection engine uses a 4-factor gated composite pipeline:

1. **Spatial Candidate Bounding**: PostGIS spatial filter $\text{ST\_DWithin}(\text{geom}, 2500\text{m})$ (candidate must be within $2.5\text{ km}$).
2. **Temporal Windowing**: Incident timestamp difference $|t_1 - t_2| \le 3\text{ hours}$.
3. **Semantic Text Representation (`sparse_tfidf_ngram_v1`)**:
   - Domain synonym normalization (e.g., *"waterlogging"* $\leftrightarrow$ *"flooding"* $\leftrightarrow$ *"submerged"*).
   - Domain term boosting ($\times 2.5$ weighting on high-salience weather keywords).
   - Word unigrams, word bigrams, and character 4-grams with cosine similarity.
   *(Note: FastEmbed / ONNX models are not used in the live duplicate path to eliminate heavy runtime dependencies).*
4. **Composite Scoring & Hard Gates**:
   $$\text{Composite Score} = 0.35 \times \text{Spatial} + 0.25 \times \text{Temporal} + 0.25 \times \text{Semantic} + 0.15 \times \text{Category}$$
   - Candidate rejected if distance $> 2500\text{m}$, time delta $> 3\text{h}$, semantic similarity $< 0.50$, or composite score $< 0.55$.

### 11.2 What Operators See

- If an incident is clustered, the **Duplicate Cluster Card** displays:
  - Cluster centroid coordinates.
  - Number of member reports in the cluster.
  - List of linked report IDs with timestamps and distances.
  - Primary anchor incident identifier.

---

## 12. Digital Evidence & Physical Observations Guide

### 12.1 Digital Evidence Items (`evidence_items`)
- **Sources**: GDELT DOC 2.0 Global News and Mastodon Public Hashtag Feeds.
- **Display**: Shown in the **Linked Digital Evidence** section with headline, publisher, published date, relevance score, and source link.
- **Relevance Tiers**:
  - `SUPPORTING` ($\ge 0.65$ similarity): Directly confirms localized extreme weather impact.
  - `RELATED` ($0.45 – 0.64$ similarity): Mentions regional storm conditions in the surrounding district.
  - `CONTEXTUAL` ($0.35 – 0.44$ similarity): Background meteorological advisory.

### 12.2 Physical Sensor Observations (`weather_observations`)
- **Sources**: IMD Automatic Weather Stations (AWS) and CWC National Water Data Portal river gauges.
- **Display**: Shown in the **Physical Station Observations** section with Station Code, Sensor Type, Distance to Incident (in meters), Recorded Metric (e.g. $68\text{ mm/h}$ rainfall or $351.95\text{ m}$ river water level), and Freshness Window.
- **Corroboration Levels**:
  - `CORROBORATING` ($\ge 0.70$): Sensor physically validates reported flood/rainfall thresholds.
  - `CONSISTENT` ($0.45 – 0.69$): Sensor indicates elevated rainfall or rising water trend.
  - `WEAK` ($0.25 – 0.44$): Sensor within distance but values are borderline.
  - `CONTRADICTING`: Sensor reports dry/normal conditions despite severe flooding claim.

### 12.3 Late Reactive Corroboration Flow

External news articles, social posts, and river gauge telemetry often arrive minutes or hours after a citizen report is submitted.

1. Late evidence or observation records are ingested by background workers and persisted to PostgreSQL.
2. The transactional outbox stages an orchestration trigger.
3. `OrchestrationDispatcher` identifies all proximate active incidents within spatial radius ($25\text{ km}$ for evidence, $35\text{ km}$ for CWC river gauges).
4. Dispatcher executes single-stage credibility recalculation on affected incidents.
5. Outbox emits a `report.intelligence_ready` event to `stream:weather:realtime`.
6. FastAPI pushes an SSE event to all connected browser dashboards.
7. React Query invalidates cached incident queries and automatically updates the credibility score and evidence cards **without requiring a page refresh**.

---

## 13. Operator & Admin Guide: Verification Queue (`/admin/queue`)

Disaster management operators (DEOC / SDRF / NDRF) use the **Verification Queue** to evaluate incident reports and record official operational decisions.

### 13.0 Operator Portal Gateway (`/login`)
The `/login` screen serves as an **Operator Context & Navigation Gateway (Demo Environment)**. It displays designated reviewer context (e.g. `DEOC Officer`, `officer@deoc.gov.in`) and direct navigation links to `/admin/queue` and `/incidents`. It does **not** enforce credential submission or issue JWT session tokens in the MVP environment. Production OAuth2 / JWT role-based access control (RBAC) is deferred for production hardening.

### 13.1 Triage Queue Interface

- **Active Queue Tab**: Displays all unprocessed reports with status `PENDING` or `UNDER_REVIEW`.
- **Queue Table Columns**:
  - Priority Rank (computed from severity + machine credibility)
  - Incident Tracking ID & Title
  - Hazard Category Badge
  - Severity Level
  - Location Landmark / Coordinates
  - Machine Credibility Score
  - Submission Age / Timestamp
  - Quick Action Button: **"Inspect & Review"**
- **Queue Filters**: Filter queue by status (`ACTIVE`, `PENDING`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `DUPLICATE`), hazard category, severity, and text search.

### 13.2 Review Drawer & Operational Actions (`ReviewReportDrawer`)

Clicking on any incident in the table opens the **Review Drawer** displaying side-by-side evidence:
- Full incident description, reporter contact info (if provided).
- Location mini-map with exact coordinates.
- MinIO photo/video attachment preview.
- Machine credibility breakdown and linked sensor telemetry.

#### Available Operator Actions:

1. **Verify Report (Authorize)**:
   - Click **"Verify Report"**.
   - Enter optional operational notes (e.g., *"Confirmed with local police station 4"*).
   - System transitions status to `VERIFIED`.
   - The incident appears with a `VERIFIED` status badge across incident lists, map markers, and dashboard filter views.
2. **Place Under Review**:
   - Click **"Review"**.
   - Enter optional operational notes.
   - System transitions status to `UNDER_REVIEW` (signals to other operators that an officer is actively investigating).
3. **Reject Report (Hoax / Inaccurate)**:
   - Click **"Reject"** to open the rejection sub-form.
   - Select required **Rejection Reason**:
     - `INACCURATE_LOCATION` — Coordinates do not match reported landmark
     - `SPAM_OR_HOAX` — Fabricated report or prank
     - `OUTDATED_EVENT` — Old weather media from previous years
     - `INSUFFICIENT_EVIDENCE` — Cannot be substantiated
     - `DUPLICATE_REPORT` — Redundant submission
     - `OTHER` — Custom reason
   - Enter optional operator notes and click **"Confirm Rejection"**. System transitions status to `REJECTED`.
4. **Mark as Duplicate**:
   - Click **"Duplicate"** to open the duplicate sub-form.
   - Optionally enter the Primary Parent Incident ID and notes.
   - Click **"Confirm Duplicate"**. System transitions status to `DUPLICATE`.

---

## 14. Verification State Machine & Operational Rules

The platform enforces a strict finite state machine for incident verification:

```
                  ┌──────────────────────┐
                  │       PENDING        │
                  └──────────┬───────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │ UNDER_REVIEW │ │   VERIFIED   │ │   REJECTED   │
     └──────┬───────┘ └──────────────┘ └──────────────┘
            │                ▲                ▲
            ├────────────────┘                │
            ├─────────────────────────────────┤
            ▼                                 ▼
     ┌──────────────┐                  ┌──────────────┐
     │  DUPLICATE   │                  │   REJECTED   │
     └──────────────┘                  └──────────────┘
```

### 14.1 Valid & Invalid State Transitions

| Current State | Permitted Next States | Forbidden Transitions (Blocked by System) |
| :--- | :--- | :--- |
| `PENDING` | `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `DUPLICATE` | N/A |
| `UNDER_REVIEW` | `VERIFIED`, `REJECTED`, `DUPLICATE` | Cannot return to `PENDING` |
| `VERIFIED` | *(Terminal State)* | Cannot transition to `REJECTED`, `DUPLICATE`, `PENDING` |
| `REJECTED` | *(Terminal State)* | Cannot transition to `VERIFIED`, `UNDER_REVIEW`, `PENDING` |
| `DUPLICATE` | *(Terminal State)* | Cannot transition to `VERIFIED`, `UNDER_REVIEW`, `PENDING` |

### 14.2 Human Override Invariance

- Automated intelligence calculations (`IncidentPipeline`) and late reactive re-corroboration **never** overwrite an operator's human verification decision.
- Every operator action writes an audit record to the verification audit history recorded in the `verification_events` database table containing:
  - Incident ID
  - Operator Username / ID
  - Prior Status $\rightarrow$ New Status
  - Rejection Reason (if rejected)
  - Operator Notes
  - Action Timestamp

---

## 15. External Data Feeds & Provider Transparency

The platform integrates with both official government portals and open digital feeds:

| Data Source | Type & Endpoint | Ingestion Frequency | Location Precision | Operational Trust Level | Current Environment Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **NDMA SACHET** | National Disaster Alert Feed (`sachet.ndma.gov.in`) | Hourly / On-Demand | District / State Polygon | **Official High Trust** (Prior $0.85$) | **LIVE PROVIDER VERIFIED** (Real HTTP POST verified, 66 alerts parsed). |
| **CWC NWDP** | National Water Data Portal River Gauges (`nwdp.nwic.gov.in`) | Scheduled (30 min) | Exact Station GPS ($<10\text{m}$) | **Physical Telemetry High Trust** (Prior $0.92$) | **LIVE PROVIDER VERIFIED** (Real HTTP GET verified, 5 live records parsed in proof; default fetch limit 50). |
| **GDELT DOC 2.0** | Global Disaster News Headlines (`api.gdeltproject.org`) | Polled ($\ge 5.0\text{s}$ interval) | City / Region Text Match | **Secondary Media Evidence** (Prior $0.40$) | **LIVE PROVIDER & INTELLIGENCE VERIFIED** (Real HTTP GET verified, 50 articles parsed, rate limited $\ge 5.0\text{s}$). |
| **Mastodon Social** | Public Emergency Hashtag Posts (`mastodon.social`) | Polled ($\ge 1.0\text{s}$ interval) | Keyword Match (No native GPS) | **Crowdsourced Social Signal** (Prior $0.35$) | **LIVE PROVIDER / INGESTION VERIFIED** (Real HTTP GET verified, 179 posts parsed, rate limited $\ge 1.0\text{s}$). |
| **IMD Nowcast** | Automated Weather Stations & Nowcast (`api.imd.gov.in`) | Scheduled | Station GPS | **Physical Telemetry High Trust** (Prior $0.90$) | **NOT LIVE VERIFIED** (Official production API requires institutional credentials/IP whitelisting; handled via graceful mock/error fallback). |
| **DemoSeed** | Synthetic Emergency Weather Generator | Local Dev Utility | City Landmarks | **Test / Evaluation Only** | **DEVELOPMENT UTILITY** (Not scheduled in production). |

---

## 16. Real-Time Streaming & SSE Transport

The platform uses FastAPI Server-Sent Events (`GET /api/v1/events/stream`) backed by Redis Streams (`stream:weather:realtime`):

- **Event Deduplication**: The frontend `RealtimeService` maintains a bounded 1,000-item FIFO ring buffer of processed event IDs to prevent duplicate UI notifications.
- **Cache Invalidation**: When an event is received, React Query automatically invalidates the specific query keys (`dashboard-summary`, `incidents`, `incident-{id}`, `verification-queue`), triggering an immediate background REST refetch.
- **Heartbeats & Reconnection**: Comment heartbeats (`: heartbeat`) keep long-lived SSE connections alive across reverse proxies. If a network disruption occurs, `RealtimeService` automatically reconnects with exponential backoff.

---

## 17. Error Handling & Troubleshooting Guide

### 17.1 User-Visible Errors & Resolutions

| Error Message / Symptom | Problem Type | Cause | User / Operator Resolution |
| :--- | :--- | :--- | :--- |
| *"Please provide location coordinates using GPS or landmark"* | User Validation Error | Coordinate fields empty during citizen submission. | Click "Use Current Location" or enter valid decimal latitude/longitude. |
| *"Title must be at least 3 characters long"* | User Validation Error | Report title is too short. | Provide a descriptive incident title (e.g. *"Flooding on SV Road"*). |
| *"exceeds the 15MB file size limit"* | User File Error | Uploaded photo/video is too large. | Compress file or upload media $\le 15\text{ MB}$. |
| *"You can upload a maximum of 3 media files"* | User File Error | Attempted to attach more than 3 files. | Select up to 3 photos/videos. |
| *"Tracking ID not found"* | Lookup Notice | Typo in tracking ID. | Verify tracking ID format (`RPT-YYYYMMDD-XXXXXXXX`). |
| *"Feed Unavailable" / "Incident Unavailable"* | System Connection Error | FastAPI backend is offline or unreachable. | Check if backend API server is running on `http://127.0.0.1:8000`. |
| *Real-time updates not appearing without refresh* | Stream Disconnected | Outbox worker or Redis is stopped. | Verify `python -m app.workers.run_outbox_worker` is running in Terminal 4. |
| *IMD 401 Unauthorized in worker logs* | External Gateway Limitation | IMD API requires institutional IP whitelisting. | Expected behavior for local evaluation; scheduler logs warning and continues with NDMA/CWC feeds. |
| *GDELT 429 Too Many Requests in logs* | Rate Limit Window | Outbound queries made faster than once every 5s. | Adapter automatically throttles ($\ge 5.0\text{s}$ spacing). If manually probed, wait 6 seconds before retrying. |

---

## 18. Complete Status Glossary

### 18.1 Processing Status (`processing_status`)
- `QUEUED`: Report ingested and staged in PostgreSQL outbox; awaiting background intelligence processing.
- `PROCESSING`: Pipeline dispatcher is actively executing the 5-stage intelligence analysis.
- `COMPLETED`: Intelligence pipeline finished; credibility score, duplicates, and corroborations persisted.
- `FAILED`: Pipeline encountered an unrecoverable exception; failure fallback credibility score assigned.

### 18.2 Verification Status (`verification_status`)
- `PENDING`: Newly submitted incident awaiting human triage review.
- `UNDER_REVIEW`: A disaster operator is actively investigating on-ground reports with local authorities.
- `VERIFIED`: Official operator confirmed the report as genuine; marked as verified across dashboards and lists.
- `REJECTED`: Official operator rejected the report as a hoax, spam, or inaccurate location.
- `DUPLICATE`: Marked as a redundant report linked to an existing primary parent incident.

### 18.3 Intelligence Readiness (`overall_readiness`)
- `INTELLIGENCE_READY`: All 5 stages evaluated successfully; complete credibility and sensor delta available.
- `NEEDS_REVIEW`: High discrepancy or low corroboration; operator review recommended.
- `FAILED_FALLBACK`: Fallback scoring applied due to stage timeout or missing spatial boundaries.

---

## 19. What the System Does Automatically vs. What Requires Human Action

### 19.1 Automatic Functions (Zero Operator Effort)
- Citizen report intake, MinIO photo streaming, and SHA-256 validation.
- Spatial-temporal candidate generation ($2.5\text{ km}$, $3\text{ hours}$) and TF-IDF duplicate scoring.
- Digital evidence matching against live GDELT news and Mastodon social streams.
- Physical sensor corroboration against IMD weather stations and CWC river gauges.
- Explainable mathematical credibility scoring ($0.0000$ to $0.9800$).
- Late reactive corroboration and live SSE dashboard updates without page reloads.
- Transactional outbox polling, at-least-once Redis stream relay, and 72-hour historical pruning.

### 19.2 Human Actions (Operator Responsibility)
- Submitting on-ground citizen disaster reports.
- Inspecting verification queue triage tables and prioritized incident deep-dives.
- Authorizing operational status transitions (`VERIFIED`, `REJECTED`, `DUPLICATE`, `UNDER_REVIEW`).
- Specifying mandatory rejection reason codes and operational audit notes.

---

## 20. What the System Does NOT Do (Operational Guardrails)

1. **Does NOT Automatically Declare Truth**: Machine credibility is an algorithmic confidence metric, not official human ground truth. The system never automatically marks reports as `VERIFIED` without human operator action.
2. **Does NOT Replace Control Room Operators**: The AI pipeline filters noise and highlights high-confidence signals; all operational response decisions remain with human commanders outside the platform.
3. **Does NOT Perform Emergency Resource Dispatching**: The platform does not have automated dispatch controls for emergency rescue teams, drainage pumps, or municipal personnel. Operational resource mobilization is conducted outside this platform via official disaster management protocols.
4. **Does NOT Fabricate GPS Coordinates**: Mastodon social posts lack native GPS; the system performs keyword-based spatial linking without fabricating synthetic lat/long points.
5. **Does NOT Scrape Full News Article Bodies**: GDELT integration queries article metadata and excerpts in `ArtList` mode to respect external bandwidth and copyright policies.
6. **Does NOT Overwrite Human Decisions**: Automated late corroboration recalculations update machine scores but **never** overwrite or revert an operator's `VERIFIED` or `REJECTED` status.
7. **Does NOT Guarantee Exactly-Once Delivery**: Redis streams operate under at-least-once delivery semantics; the frontend uses a 1,000-item ring buffer to suppress duplicate UI reactions.
8. **Does NOT Enforce Production Role-Based Access Control in MVP**: Operator verification endpoints in the development/demo environment are unauthenticated. Production OAuth2/JWT RBAC is deferred for production hardening.

---

## 21. Daily Operator Workflow (Suggested Control Room SOP)

```
┌────────────────────────────────────────────────────────────────────────┐
│               DAILY DISASTER CONTROL ROOM OPERATING PROCEDURE          │
└────────────────────────────────────────────────────────────────────────┘
  Step 1: Open Operator Dashboard (/dashboard)
          • Check Live Control Room indicator and macro event totals.
          • Inspect severe weather clusters on the situational mini-map.

  Step 2: Navigate to Priority Verification Queue (/admin/queue)
          • Sort by Priority Rank (combining SEVERE hazard + HIGH credibility).
          • Identify unreviewed incidents in the ACTIVE queue.

  Step 3: Inspect Incident Deep-Dive (/incidents/:id)
          • Review uploaded on-ground photos/videos.
          • Check physical sensor delta (e.g. CWC river gauge water level trends).
          • Check corroborating news articles and duplicate cluster size.

  Step 4: Execute Triage Action in Review Drawer
          • Click "Verify Report" to mark genuine disaster emergencies.
          • Click "Reject" with reason code if confirmed as a hoax or old media.
          • Click "Duplicate" if linked to an existing active emergency.

  Step 5: Monitor Live Situational GIS Map (/live-map)
          • Track emerging spatial clusters and monitor late reactive corroboration updates.
```

---

## 22. Frequently Asked Questions (FAQ)

**Q1: Why is my report status still `QUEUED`?**
*A: Background workers (`run_outbox_worker` and `run_dispatcher`) process reports asynchronously. In local development, ensure both worker terminals are running.*

**Q2: Why did the credibility score change after submission?**
*A: When new external data arrives (e.g. an IMD AWS weather station reports heavy rain 10 minutes later, or a GDELT news article is published), the late corroboration engine automatically recalculates credibility and pushes the updated score to the UI.*

**Q3: Why does the map show fewer markers than the total count on dashboard KPI cards?**
*A: The map enforces a 500-feature rendering limit (`LIMIT 500`) to prevent browser rendering degradation during massive disaster surges. KPI cards display the exact database-wide totals.*

**Q4: Can an operator undo a verification decision?**
*A: `VERIFIED`, `REJECTED`, and `DUPLICATE` are terminal states in the state machine to ensure audit integrity. To record a correction, operators add notes in the verification audit history.*

**Q5: Does a 90% machine credibility score mean the report is officially verified?**
*A: No. Machine credibility reflects algorithmic confidence based on sensor data and evidence. An incident is only officially verified when an authorized human operator marks it as `VERIFIED`.*

---

## 23. Getting Started in 10 Minutes: First-Time User Walkthrough

1. **Start System**: Follow the 9-terminal startup runbook in [docs/EXTERNAL_SETUP.md](EXTERNAL_SETUP.md).
2. **Open Home Page**: Visit `http://localhost:5173` to view the public disaster overview.
3. **Submit a Test Report**:
   - Go to `http://localhost:5173/report`.
   - Select `FLOODING`, severity `HIGH`, title *"Flash flooding near Dadar Station"*.
   - Click **"Use Current Location"** and attach a test photo.
   - Click **"Submit Weather Report"** and copy your **Tracking ID** (e.g. `RPT-...`).
4. **Track Your Report**: Visit `http://localhost:5173/track-report`, paste your Tracking ID, and watch the 4-stage progress stepper.
5. **Inspect Operations Dashboard**: Visit `http://localhost:5173/dashboard` to see your report reflected in KPI cards and charts.
6. **Open Incident Deep-Dive**: Click on your report in `/incidents` to inspect the 5-dimension machine credibility breakdown and duplicate cluster analysis.
7. **Triage as an Operator**:
   - Visit `http://localhost:5173/admin/queue`.
   - Click **"Inspect & Review"** on your test report.
   - Enter operator notes and click **"Verify Report"**.
   - Observe the live status badge update to `VERIFIED` across all screens without refreshing.

---

## 24. Quick Reference Summary

| Area | Public Citizen Endpoint | Operator / Admin Endpoint | API Route |
| :--- | :--- | :--- | :--- |
| **Incident Intake** | `/report` | N/A | `POST /api/v1/reports` |
| **Report Tracking** | `/track-report?id=...` | N/A | `GET /api/v1/reports/{id}` |
| **Executive Dashboard** | `/dashboard` | `/dashboard` | `GET /api/v1/dashboard/summary` |
| **Situational GIS Map** | `/live-map` | `/live-map` | `GET /api/v1/geo/incidents` |
| **Incident Directory** | `/incidents` | `/incidents` | `GET /api/v1/reports` |
| **Incident Deep-Dive** | `/incidents/:id` | `/incidents/:id` | `GET /api/v1/reports/{id}` |
| **Verification Triage Queue**| N/A | `/admin/queue` | `GET /api/v1/verification/queue` |
| **Verification Actions** | N/A | `/admin/queue` Drawer | `POST /api/v1/verification/*` |
| **Analytics Platform** | `/analytics` | `/analytics` | `GET /api/v1/analytics/*` |
| **Realtime Stream** | Background SSE | Background SSE | `GET /api/v1/events/stream` |
