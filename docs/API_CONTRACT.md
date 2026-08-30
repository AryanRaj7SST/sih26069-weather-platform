# RESTful API Contract & Endpoint Specifications

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)
**Base URL**: `/api/v1`
**Standard Response Format**: All responses adhere to a consistent JSON envelope.
**Total Operations**: 23 operations across 22 canonical paths.

---

## 1. Standard Request & Response Envelopes

### 1.1 Success Response Envelope
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-08-31T03:00:00.000Z",
    "request_id": "req_01HZX89AB..."
  }
}
```

### 1.2 Paginated Response Envelope
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_records": 184,
    "total_pages": 10,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2026-08-31T03:00:00.000Z",
    "request_id": "req_01HZX89AB..."
  }
}
```

### 1.3 Error Response Envelope
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Incident with ID e53b4916-df63-4564-82e8-f10e76272a03 does not exist.",
    "details": []
  },
  "meta": {
    "timestamp": "2026-08-31T03:00:00.000Z",
    "request_id": "req_01HZX89AB..."
  }
}
```

---

## 2. Authentication & Authorization Model

> [!NOTE]
> **Current MVP Architecture**: In accordance with the hackathon evaluation scope, triage mutations (`/api/v1/verification/*`) operate unauthenticated for evaluator testing. Mutations are automatically bound to the institutional reviewer (`officer@deoc.gov.in`, `DEOC_OFFICER`) in `verification_events`. Full OAuth2 / JWT authentication is deferred for production security hardening.

---

## 3. Complete API Catalog (22 Paths / 23 Operations)

### 3.1 System Health & Metadata

#### 1. Root Information
- **Method & Path**: `GET /`
- **Purpose**: System identification and platform version status.
- **Response Shape** (`200 OK`):
  ```json
  {
    "name": "National Weather Big Data Analytics Platform",
    "version": "0.1.0",
    "status": "online",
    "docs_url": "/docs"
  }
  ```

#### 2. Health & Dependency Readiness
- **Method & Path**: `GET /api/v1/health`
- **Purpose**: Verifies PostgreSQL connection, PostGIS spatial extension, and Redis reachability.
- **Response Shape** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "environment": "development",
    "database": "connected",
    "redis": "connected",
    "version": "0.1.0"
  }
  ```

---

### 3.2 Citizen & Multi-Source Report Ingestion

#### 3. Submit Citizen Incident Report
- **Method & Path**: `POST /api/v1/reports`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `title`: `string` (min: 5, max: 255)
  - `description`: `string` (optional, max: 2000)
  - `latitude`: `float` (range: `-90.0` to `90.0`)
  - `longitude`: `float` (range: `-180.0` to `180.0`)
  - `location_name`: `string` (optional, max: 255)
  - `reported_category`: `string` (e.g., `"FLOOD_WATERLOGGING"`)
  - `severity`: `string` (`"LOW"`, `"MODERATE"`, `"HIGH"`, `"SEVERE"`, `"CRITICAL"`)
  - `occurred_at`: `datetime ISO 8601` (optional, defaults to now)
  - `photo`: `binary file` (optional, JPEG/PNG/WebP, max 15 MB)
- **Response Shape** (`201 Created`):
  ```json
  {
    "success": true,
    "data": {
      "id": "e53b4916-df63-4564-82e8-f10e76272a03",
      "tracking_id": "RPT-20260831-X9K2",
      "title": "Severe waterlogging near Kurla station",
      "verification_status": "PENDING",
      "created_at": "2026-08-31T03:00:00Z"
    }
  }
  ```

#### 4. List Ingested Reports
- **Method & Path**: `GET /api/v1/reports`
- **Query Parameters**: `page`, `page_size`, `status`, `category`, `severity`, `min_lat`, `max_lat`, `min_lon`, `max_lon`
- **Response Shape** (`200 OK`): Paginated envelope of report summaries.

#### 5. Get Report by Reference Tracking ID or UUID
- **Method & Path**: `GET /api/v1/reports/{id}`
- **Path Parameter**: `id` — Reference tracking ID (`RPT-...`) or report UUID.
- **Purpose**: Public citizen tracking and report status lookup.
- **Response Shape** (`200 OK`): Full report detail with media metadata and verification status.

---

### 3.3 Incident Intelligence & Deep Dive

#### 6. List Filtered Operational Incidents
- **Method & Path**: `GET /api/v1/incidents`
- **Query Parameters**:
  - `page`: `int` (default: 1)
  - `page_size`: `int` (default: 20, max: 100)
  - `category`: `string` (optional)
  - `severity`: `string` (optional)
  - `verification_status`: `string` (optional)
  - `search`: `string` (searches title, location, tracking ID)
- **Response Shape** (`200 OK`): Paginated array of `IncidentCardData`.

#### 7. Get Full Incident Detail
- **Method & Path**: `GET /api/v1/incidents/{id}`
- **Purpose**: Incident summary, media attachments, cluster links, and audit history.
- **Response Shape** (`200 OK`): `IncidentDetailData` object.

#### 8. Get Operator Deep Detail
- **Method & Path**: `GET /api/v1/incidents/{id}/operator-detail`
- **Purpose**: Full forensic operator inspection view with unredacted source attributes for authorized DEOC triage.

#### 9. Get Explainable Credibility Breakdown
- **Method & Path**: `GET /api/v1/incidents/{id}/credibility`
- **Response Shape** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "incident_id": "e53b4916-df63-4564-82e8-f10e76272a03",
      "score": 0.9613,
      "is_machine_assessed": true,
      "label": "VERY_HIGH_CREDIBILITY",
      "base_trust_prior": 0.50,
      "engine_version": "v1",
      "policy_version": "v1",
      "explanation_text": "Machine-assessed credibility score of 0.9613.",
      "positive_drivers": [
        "Moderate baseline source trust (0.60).",
        "Crowd volume signal from 19 duplicate incident reports (sub-signal: 1.00).",
        "Digital evidence corroboration across 22 distinct provenance groups (score: 0.93)."
      ],
      "negative_drivers": [],
      "uncertainty_flags": [],
      "last_calculated_at": "2026-08-31T03:00:00Z"
    }
  }
  ```

#### 10. Get Orchestration Intelligence Stages
- **Method & Path**: `GET /api/v1/incidents/{id}/intelligence`
- **Purpose**: Stage execution telemetry (`LOCATION`, `DUPLICATE`, `EVIDENCE`, `OBSERVATION`, `CREDIBILITY`).

#### 11. Get Linked Digital Evidence
- **Method & Path**: `GET /api/v1/incidents/{id}/evidence`
- **Purpose**: Corroborated news articles, social posts, and official alerts.

#### 12. Get Corroborating Physical Observations
- **Method & Path**: `GET /api/v1/incidents/{id}/observations`
- **Purpose**: Weather telemetry from proximate IMD AWS and CWC river gauges.

#### 13. Get Duplicate Cluster Topology
- **Method & Path**: `GET /api/v1/incidents/{id}/cluster`
- **Purpose**: Cluster membership, centroid coordinates, and member similarity scores.

---

### 3.4 Geospatial Vector API

#### 14. Live Incident GeoJSON Features
- **Method & Path**: `GET /api/v1/geo/incidents`
- **Purpose**: Bounded GeoJSON `FeatureCollection` for Leaflet vector map rendering.
- **Query Parameters**:
  - `bbox`: `min_lon,min_lat,max_lon,max_lat` (optional, max 10° span when bounded)
  - `hours_ago`: `int` (optional)
  - `category`: Disaster category filter (optional)
  - `verification_status`: Verification status filter (optional)
- **Server-Side Bound**: Returns up to **500 features** (`LIMIT 500`).
- **Response Shape** (`200 OK`):
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "id": "e53b4916-df63-4564-82e8-f10e76272a03",
        "geometry": {
          "type": "Point",
          "coordinates": [72.8777, 19.0760]
        },
        "properties": {
          "tracking_id": "RPT-20260831-X9K2",
          "title": "Severe waterlogging near Kurla station",
          "category": "FLOOD_WATERLOGGING",
          "severity": "HIGH",
          "verification_status": "VERIFIED",
          "credibility_score": 0.9613,
          "occurred_at": "2026-08-31T02:30:00Z"
        }
      }
    ]
  }
  ```

---

### 3.5 Verification & Triage Operations

#### 15. Priority Verification Queue
- **Method & Path**: `GET /api/v1/verification/queue`
- **Query Parameters**: `page`, `page_size`, `category`, `severity`, `status`
- **Purpose**: Backlog of `PENDING` and `UNDER_REVIEW` reports ranked by priority.

#### 16. Authorize and Verify Incident
- **Method & Path**: `POST /api/v1/verification/{id}/verify`
- **Request Body**:
  ```json
  {
    "notes": "Confirmed with Mumbai DEOC Flood Control Room.",
    "broadcast_alert": true
  }
  ```
- **Response Shape** (`200 OK`): Updated report with `verification_status = "VERIFIED"`.

#### 17. Reject False Alarm or Spam
- **Method & Path**: `POST /api/v1/verification/{id}/reject`
- **Request Body**:
  ```json
  {
    "rejection_reason": "INACCURATE_LOCATION",
    "notes": "Photo belongs to historical 2021 archive."
  }
  ```
- **Response Shape** (`200 OK`): Updated report with `verification_status = "REJECTED"`.

#### 18. Merge as Duplicate
- **Method & Path**: `POST /api/v1/verification/{id}/mark-duplicate`
- **Request Body**:
  ```json
  {
    "primary_report_id": "c8f7952a-cf91-4cf4-9279-d75d5a2d67ea",
    "notes": "Duplicate citizen submission for Kurla bridge flooding."
  }
  ```
- **Response Shape** (`200 OK`): Updated report with `verification_status = "DUPLICATE"`.

#### 19. Place Under Review
- **Method & Path**: `POST /api/v1/verification/{id}/review`
- **Request Body**:
  ```json
  {
    "notes": "Awaiting ground scout confirmation."
  }
  ```
- **Response Shape** (`200 OK`): Updated report with `verification_status = "UNDER_REVIEW"`.

---

### 3.6 Analytics & Dashboard Server Aggregations

#### 20. Dashboard Summary Aggregation
- **Method & Path**: `GET /api/v1/dashboard/summary`
- **Query Parameters**: `time_range` (`24h`, `48h`, `7d`, `30d`, `all`), `category`, `severity`, `status`, `bbox`
- **Response Shape** (`200 OK`): SQL-aggregated KPIs, total reports, verified count, under review, high severity count, diurnal curve, and category breakdown.

#### 21. Activity Trends Time-Series
- **Method & Path**: `GET /api/v1/analytics/trends`
- **Query Parameters**: `time_range`, `interval` (`hour`, `day`), `category`, `severity`, `status`, `bbox`
- **Response Shape** (`200 OK`): Time-bucketed volume and verification progression.

#### 22. Regional Demographics Distribution
- **Method & Path**: `GET /api/v1/analytics/regional`
- **Query Parameters**: `time_range`, `category`, `severity`, `status`, `bbox`
- **Response Shape** (`200 OK`): Two-tier regional aggregation (urban clusters and state boundaries).

---

### 3.7 Real-Time Event Streaming

#### 23. Real-Time Server-Sent Events (SSE) Stream
- **Method & Path**: `GET /api/v1/events/stream`
- **Transport**: Persistent HTTP `text/event-stream; charset=utf-8`
- **Query / Header Parameters**: `Last-Event-ID` header or `?last_event_id=...` query parameter (Redis sequence cursor).
- **Heartbeats**: Emits comment keepalives (`: keepalive\n\n`) every 15 seconds.
- **Event Types**:
  1. `report.created`
  2. `report.verification_changed`
  3. `report.intelligence_ready`
  4. `cluster.updated`
  5. `system.resync_required`
- **SSE Framing**:
  ```http
  id: 1788095860922-0
  event: report.verification_changed
  data: {"event_id":"550e8400-e29b-41d4-a716-446655440000","event_type":"report.verification_changed","occurred_at":"2026-08-31T03:00:00Z","entity_id":"rep-92bc018a","tracking_id":"RPT-2026-8921","payload":{"previous_status":"PENDING","new_status":"VERIFIED"}}
  ```
