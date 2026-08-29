# RESTful API Contract & Endpoint Specifications

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)  
**Base URL**: `/api/v1`  
**Standard Response Format**: All responses adhere to a consistent JSON envelope.

---

## 1. Standard Request & Response Envelopes

### 1.1 Success Response Envelope
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-08-29T21:02:19.439Z",
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
    "timestamp": "2026-08-29T21:02:19.439Z",
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
    "timestamp": "2026-08-29T21:02:19.439Z",
    "request_id": "req_01HZX89AB..."
  }
}
```

---

## 2. Authentication & Authorization Model

> [!NOTE]
> **MVP Status**: In the Smart India Hackathon MVP environment, operational endpoints are open for evaluator and operator triage. Audit logging automatically binds triage mutations to the institutional reviewer (`officer@deoc.gov.in`, role `DEOC_OFFICER`). Full OAuth2 / JWT bearer token validation is scoped for production security hardening.

---

## 3. Incident Intelligence Endpoints Catalog

### 3.1 Incident Explorer & Deep Dive

#### 1. List Operational Incidents
- **Method & Path**: `GET /api/v1/incidents`
- **Purpose**: Paginated list of weather incidents with multi-criteria filtering.
- **Query Parameters**:
  - `page`: `int` (default: `1`)
  - `page_size`: `int` (default: `20`, max: `100`)
  - `category`: `string` (e.g., `"FLOOD_WATERLOGGING"`)
  - `severity`: `string` (`"LOW"`, `"MODERATE"`, `"HIGH"`, `"SEVERE"`)
  - `verification_status`: `string` (`"PENDING"`, `"UNDER_REVIEW"`, `"VERIFIED"`, `"REJECTED"`, `"DUPLICATE"`)
  - `search`: `string` (searches tracking ID, title, location)
- **Response Shape** (`200 OK`): Paginated envelope containing array of `IncidentCardData` summaries.

#### 2. Get Full Incident Detail
- **Method & Path**: `GET /api/v1/incidents/{id}`
- **Purpose**: Comprehensive incident overview including media attachments, cluster summaries, and verification audit trail.
- **Path Parameter**: `id` — UUID or Tracking ID string.
- **Response Shape** (`200 OK`): `IncidentDetailData` object.

#### 3. Get Machine Credibility Breakdown
- **Method & Path**: `GET /api/v1/incidents/{id}/credibility`
- **Purpose**: Explainable algorithmic credibility assessment with positive/negative drivers and uncertainty flags.
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
        "Moderate baseline source trust (0.60) from SRC_PIPE_fe2e8cd3.",
        "Crowd volume signal from 19 duplicate incident reports (sub-signal: 1.00).",
        "Digital evidence corroboration across 22 distinct provenance groups (score: 0.93).",
        "Multi-source diversity boost (×1.12) from 3 independent families (CITIZEN, NEWS, SOCIAL)."
      ],
      "negative_drivers": [],
      "uncertainty_flags": [],
      "last_calculated_at": "2026-08-29T21:02:19.439252Z"
    }
  }
  ```
  *Note on `last_calculated_at`*: Represents the exact timestamp of the current machine credibility calculation, resolved via: `credibility_explanation["assessed_at"]` $\to$ `updated_at` $\to$ `created_at` $\to$ server UTC time.

#### 4. Get Orchestration Intelligence Stages
- **Method & Path**: `GET /api/v1/incidents/{id}/intelligence`
- **Purpose**: Execution status and per-stage telemetry across the 5 canonical pipeline stages (`LOCATION`, `DUPLICATE`, `EVIDENCE`, `OBSERVATION`, `CREDIBILITY`).
- **Canonical Stage Outcomes (`StageOutcome`)**:
  - `SUCCESS_WITH_RESULTS` (UI: *"Results Found"*)
  - `SUCCESS_WITH_NO_MATCH` (UI: *"No Matches Found"*)
  - `SUCCESS_WITH_INSUFFICIENT_DATA` (UI: *"Insufficient Data"*)
  - `SKIPPED_NOT_APPLICABLE`
  - `SKIPPED_STALE`
  - `RETRYABLE_FAILURE`
  - `PERMANENT_FAILURE`
- **Overall Readiness States (`OverallReadiness`)**: `INTELLIGENCE_PENDING`, `INTELLIGENCE_READY`, `INTELLIGENCE_PARTIAL`, `INTELLIGENCE_FAILED`.

#### 5. Get Linked Digital Evidence
- **Method & Path**: `GET /api/v1/incidents/{id}/evidence`
- **Purpose**: Paginated list of corroborated news articles, RSS alerts, and social posts with relationship weights (`CORROBORATING`, `RELATED_EVENT`, `CONTRADICTORY`).

#### 6. Get Corroborating Physical Observations
- **Method & Path**: `GET /api/v1/incidents/{id}/observations`
- **Purpose**: Paginated physical sensor corroboration telemetry from nearby IMD Automatic Weather Stations and CWC river gauges.

#### 7. Get Duplicate Cluster Topology
- **Method & Path**: `GET /api/v1/incidents/{id}/cluster`
- **Purpose**: Clustered member reports, similarity scores, and centroid representative report details.

---

## 4. Geospatial & Map Endpoints

#### 8. Live Incident GeoJSON Features
- **Method & Path**: `GET /api/v1/geo/incidents`
- **Purpose**: High-performance GeoJSON `FeatureCollection` for Leaflet map vector rendering.
- **Query Parameters**:
  - `min_lat`, `max_lat`, `min_lon`, `max_lon`: Bounding box coordinates (optional)
  - `category`: Disaster category filter (optional)
  - `verification_status`: Verification filter (optional)
- **Response Shape** (`200 OK`): GeoJSON `FeatureCollection` with `Point` geometries (`SRID 4326`). Reports without valid coordinates are safely omitted from spatial features.

---

## 5. Administrative Verification & Triage Endpoints

#### 9. Priority Verification Queue
- **Method & Path**: `GET /api/v1/verification/queue` (or `GET /api/v1/reports?status=PENDING,UNDER_REVIEW`)
- **Purpose**: Priority-ranked triage backlog for emergency control room operators.

#### 10. Authorize and Verify Incident
- **Method & Path**: `POST /api/v1/verification/{id}/verify` (also available via `POST /api/v1/incidents/{id}/verify`)
- **Request Body**:
  ```json
  {
    "notes": "Confirmed with Mumbai DEOC Flood Control Room.",
    "broadcast_alert": true
  }
  ```
- **Response Shape** (`200 OK`): Updated incident with `verification_status = "VERIFIED"` and new `VerificationEvent` audit record.

#### 11. Reject False Alarm or Spam
- **Method & Path**: `POST /api/v1/verification/{id}/reject`
- **Request Body**:
  ```json
  {
    "rejection_reason": "INACCURATE_LOCATION",
    "notes": "Photo belongs to historical 2021 archive."
  }
  ```
- **Response Shape** (`200 OK`): Updated incident with `verification_status = "REJECTED"`.

#### 12. Merge as Duplicate
- **Method & Path**: `POST /api/v1/verification/{id}/mark-duplicate`
- **Request Body**:
  ```json
  {
    "primary_report_id": "c8f7952a-cf91-4cf4-9279-d75d5a2d67ea",
    "notes": "Duplicate citizen submission for Kurla bridge flooding."
  }
  ```
- **Response Shape** (`200 OK`): Updated incident with `verification_status = "DUPLICATE"`.

#### 13. Place Under Review
- **Method & Path**: `POST /api/v1/verification/{id}/review`
- **Request Body**:
  ```json
  {
    "notes": "Awaiting SDRF ground scout confirmation."
  }
  ```
- **Response Shape** (`200 OK`): Updated incident with `verification_status = "UNDER_REVIEW"`.
