# RESTful API Contract & Endpoint Specifications

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)
**Base URL**: `/api/v1`
**Standard Response Format**: All responses adhere to a consistent JSON envelope.
**Total Operations**: 23 operations across 22 canonical paths.
**Status**: **SYNCHRONIZED WITH CURRENT CODE & OPENAPI SPECIFICATION**

---

## 1. Standard Request & Response Envelopes

### 1.1 Success Response Envelope
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-08-31T13:25:33.000000Z",
    "request_id": "req_bb864a4b25db"
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
    "total_records": 7256,
    "total_pages": 363,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2026-08-31T13:25:33.000000Z",
    "request_id": "req_bb864a4b25db"
  }
}
```

### 1.3 Error Response Envelope
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Incident with ID fbb34eb2-ce5c-4e86-8b39-8666b26273a4 does not exist.",
    "details": []
  },
  "meta": {
    "timestamp": "2026-08-31T13:25:33.000000Z",
    "request_id": "req_bb864a4b25db"
  }
}
```

---

## 2. Authentication & Authorization Model

> [!NOTE]
> **Current MVP Architecture**: Operator verification endpoints are currently unauthenticated for the MVP/demo environment. Production JWT/RBAC is deferred.

---

## 3. Complete API Catalog (22 Paths / 23 Operations)

### 3.1 System Health & Metadata

#### 1. Root Information
- **Method & Path**: `GET /`
- **Purpose**: System identification and platform version status.
- **Response** (`200 OK`):
  ```json
  {
    "name": "National Weather Big Data Analytics Platform",
    "version": "0.1.0",
    "status": "online",
    "docs_url": "/docs"
  }
  ```

#### 2. Service Health Check
- **Method & Path**: `GET /api/v1/health`
- **Purpose**: Verifies PostgreSQL connection, PostGIS spatial extension, and Redis reachability.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "status": "healthy",
      "service": "National Weather Big Data Analytics Platform",
      "environment": "development",
      "version": "0.1.0"
    },
    "meta": {
      "timestamp": "2026-08-31T13:25:33.000000Z"
    }
  }
  ```

---

### 3.2 Citizen Reporting & Tracking

#### 3. List & Filter Incident Reports
- **Method & Path**: `GET /api/v1/reports`
- **Query Parameters**: `page` (int), `page_size` (int), `category` (string), `severity` (string), `verification_status` (string).
- **Response** (`200 OK`): Paginated envelope containing `weather_reports` summaries.

#### 4. Submit Citizen Incident Report
- **Method & Path**: `POST /api/v1/reports`
- **Content-Type**: `multipart/form-data` or `application/json`
- **Behavior**: Atomically persists report in PostgreSQL, assigns tracking ID (`RPT-...`), stages `report.created` (UI) and `orchestration.incident_ingested` (intelligence pipeline) outbox rows.
- **Response** (`201 Created`):
  ```json
  {
    "success": true,
    "data": {
      "id": "fbb34eb2-ce5c-4e86-8b39-8666b26273a4",
      "tracking_id": "RPT-20260831-B848D18A",
      "title": "Severe waterlogging near metro station",
      "verification_status": "PENDING",
      "credibility_score": 0.537,
      "created_at": "2026-08-31T12:21:18.759718Z"
    }
  }
  ```

#### 5. Retrieve Single Report by ID or Tracking Code
- **Method & Path**: `GET /api/v1/reports/{id}`
- **Path Parameter**: `id` — UUID or `tracking_id` string (e.g. `RPT-20260831-B848D18A`).
- **Response** (`200 OK`): Public report status, timeline, and resolution data.

---

### 3.3 Incident Explorer & Intelligence Endpoints

#### 6. List & Filter Operational Incidents
- **Method & Path**: `GET /api/v1/incidents`
- **Query Parameters**: `page`, `page_size`, `status`, `category`, `severity`, `readiness`, `search`.
- **Response** (`200 OK`): Paginated envelope containing list of operational incidents.

#### 7. Retrieve Incident Detail
- **Method & Path**: `GET /api/v1/incidents/{id}`
- **Response** (`200 OK`): Full incident detail including credibility score, category, coordinates, and summary counts.

#### 8. Retrieve Operator Incident Detail
- **Method & Path**: `GET /api/v1/incidents/{id}/operator-detail`
- **Response** (`200 OK`): Extended incident detail for administrative operators with raw metadata.

#### 9. Retrieve Machine Credibility Breakdown
- **Method & Path**: `GET /api/v1/incidents/{id}/credibility`
- **Response** (`200 OK`): Explainable breakdown of credibility drivers, weights, and confidence flags.

#### 10. Retrieve Duplicate Cluster Details
- **Method & Path**: `GET /api/v1/incidents/{id}/cluster`
- **Response** (`200 OK`): Duplicate cluster members, similarity scores, and cluster centroid coordinates.

#### 11. Retrieve Linked Digital Evidence Items
- **Method & Path**: `GET /api/v1/incidents/{id}/evidence`
- **Response** (`200 OK`): Cross-platform news, social posts, and official alerts linked to the incident.

#### 12. Retrieve Corroborating Physical Observations
- **Method & Path**: `GET /api/v1/incidents/{id}/observations`
- **Response** (`200 OK`): Proximate automated weather station and hydrological gauge readings with distance/time delta.

#### 13. Retrieve Intelligence Orchestration Status
- **Method & Path**: `GET /api/v1/incidents/{id}/intelligence`
- **Response** (`200 OK`): Readiness status and stage telemetry for the 5-stage pipeline (`LOCATION`, `DUPLICATE`, `EVIDENCE`, `OBSERVATION`, `CREDIBILITY`).

---

### 3.4 Geospatial & Analytics Endpoints

#### 14. Geospatial Viewport Query (GeoJSON)
- **Method & Path**: `GET /api/v1/geo/incidents`
- **Query Parameters**: `min_lat`, `min_lng`, `max_lat`, `max_lng`, `category`, `status`.
- **Behavior**: Returns bounded FeatureCollection (`LIMIT 500`) with point geometries (`SRID 4326`).
- **Response** (`200 OK`): Standard GeoJSON `FeatureCollection`.

#### 15. Get Dashboard Metric Summary
- **Method & Path**: `GET /api/v1/dashboard/summary`
- **Response** (`200 OK`): Macro KPI counts, severity breakdown, category distribution, and verification rates.

#### 16. Get Analytics Activity Trends
- **Method & Path**: `GET /api/v1/analytics/trends`
- **Query Parameters**: `window` (`24h`, `7d`, `30d`, `all`).
- **Response** (`200 OK`): Time-series bucketed volume and verification progression.

#### 17. Get Regional Incident Distribution
- **Method & Path**: `GET /api/v1/analytics/regional`
- **Response** (`200 OK`): Two-tier regional aggregation by state/district with risk rankings.

---

### 3.5 Verification & Triage Workflow

#### 18. Retrieve Operator Verification Queue
- **Method & Path**: `GET /api/v1/verification/queue`
- **Query Parameters**: `page`, `page_size`, `sort_by` (`credibility`, `severity`, `date`).
- **Response** (`200 OK`): Prioritized backlog of pending incident reports.

#### 19. Authorize and Verify Incident
- **Method & Path**: `POST /api/v1/verification/{id}/verify`
- **Request Body**: `{"notes": "Verified against IMD AWS gauge."}`
- **Behavior**: Transitions `verification_status` to `VERIFIED`, writes immutable audit row to `verification_events`, stages `report.verification_changed` outbox event.
- **Response** (`200 OK`): Updated verification envelope.

#### 20. Mark Incident Under Active Review
- **Method & Path**: `POST /api/v1/verification/{id}/review`
- **Behavior**: Transitions `verification_status` to `UNDER_REVIEW`.
- **Response** (`200 OK`): Updated verification envelope.

#### 21. Reject Incident as False / Hoax / Inaccurate
- **Method & Path**: `POST /api/v1/verification/{id}/reject`
- **Behavior**: Transitions `verification_status` to `REJECTED`.
- **Response** (`200 OK`): Updated verification envelope.

#### 22. Mark Incident as Duplicate
- **Method & Path**: `POST /api/v1/verification/{id}/mark-duplicate`
- **Behavior**: Transitions `verification_status` to `DUPLICATE`.
- **Response** (`200 OK`): Updated verification envelope.

---

### 3.6 Realtime Server-Sent Events (SSE) Transport

#### 23. Realtime Server-Sent Events (SSE) Stream
- **Method & Path**: `GET /api/v1/events/stream`
- **Headers Supported**: `Last-Event-ID` (for cursor replay from Redis Stream `stream:weather:realtime`).
- **Media-Type**: `text/event-stream`
- **Framing**:
  ```text
  id: 1725110400000-0
  event: report.created
  data: {"event_id":"...","event_type":"report.created","entity_id":"...","payload":{...}}

  : ping
  ```
- **Delivery Guarantee**: **At-least-once delivery with bounded client-side deduplication (1,000 items). No exactly-once guarantee.**
