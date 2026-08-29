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
    "timestamp": "2026-08-29T06:00:00Z",
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
    "page_size": 25,
    "total_records": 184,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "meta": { ... }
}
```

### 1.3 Error Response Envelope
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Weather report with ID rpt_123 does not exist.",
    "details": []
  },
  "meta": { ... }
}
```

---

## 2. API Endpoints Catalog

### 2.1 Citizen Reporting Endpoints

#### 1. Submit Citizen Incident Report
- **Purpose**: Allows citizens and field observers to submit a geotagged weather report with optional photos/videos.
- **Method & Path**: `POST /api/v1/reports`
- **Authentication**: None (Public; rate-limited by client IP)
- **Request Format**: `multipart/form-data`
  - `latitude`: `float` (e.g., `19.0760`) [Required]
  - `longitude`: `float` (e.g., `72.8777`) [Required]
  - `category_code`: `string` (e.g., `"FLOOD_WATERLOGGING"`) [Required]
  - `severity`: `string` (`"LOW"` | `"MODERATE"` | `"HIGH"` | `"SEVERE"`) [Required]
  - `title`: `string` (max 255 chars) [Required]
  - `description`: `string` (optional)
  - `location_name`: `string` (e.g., `"Kurla Station West, Mumbai"`) (optional)
  - `occurred_at`: `ISO8601 string` (optional, defaults to server time)
  - `media_files`: `File[]` (JPEG/PNG/MP4, max 3 files, $\le 15\text{MB}$ each)
- **Response Shape** (`201 Created`):
  ```json
  {
    "success": true,
    "data": {
      "id": "a98b065f-46e3-4c31-893f-c689fbfb6021",
      "tracking_id": "RPT-20260829-K8L9",
      "processing_status": "QUEUED",
      "verification_status": "PENDING",
      "submitted_at": "2026-08-29T06:05:00Z",
      "media_count": 1
    }
  }
  ```

---

### 2.2 Report Listing, Retrieval & Geospatial Queries

#### 2. List & Filter Reports
- **Purpose**: Paginated list of incident reports with multi-criteria filtering for public and admin views.
- **Method & Path**: `GET /api/v1/reports`
- **Authentication**: Public (PII redacted) / Admin (full details)
- **Query Parameters**:
  - `page`: `int` (default: `1`)
  - `page_size`: `int` (default: `20`, max: `100`)
  - `category`: `string` (optional)
  - `severity`: `string` (optional)
  - `status`: `string` (`"PENDING"`, `"VERIFIED"`, `"REJECTED"`, etc.)
  - `source_type`: `string` (optional)
  - `from_date`: `ISO8601 timestamp` (optional)
  - `to_date`: `ISO8601 timestamp` (optional)
  - `min_credibility`: `float` (optional, `0.0` - `1.0`)
- **Response Shape** (`200 OK`): Paginated array of `WeatherReportSummary` objects.

#### 3. Retrieve Single Report by ID or Tracking Code
- **Purpose**: Fetch detailed information for a specific report.
- **Method & Path**: `GET /api/v1/reports/{id}`
- **Authentication**: Public
- **Response Shape** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "id": "a98b065f-46e3-4c31-893f-c689fbfb6021",
      "tracking_id": "RPT-20260829-K8L9",
      "title": "Severe knee-deep waterlogging near station subway",
      "description": "Traffic completely halted. Water level rising steadily.",
      "category": { "code": "FLOOD_WATERLOGGING", "title": "Flood & Waterlogging" },
      "severity": "HIGH",
      "location": {
        "name": "Kurla Station West, Mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777
      },
      "occurred_at": "2026-08-29T05:45:00Z",
      "verification_status": "VERIFIED",
      "credibility_score": 0.88,
      "media": [
        {
          "id": "m_11a...",
          "media_type": "IMAGE",
          "url": "https://storage.platform.local/media/2026/08/29/kurla_subway.jpg",
          "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
      ]
    }
  }
  ```

#### 4. Geospatial Bounding-Box Query (Map Explorer)
- **Purpose**: High-speed retrieval of spatial incidents within a map viewport for Leaflet rendering.
- **Method & Path**: `GET /api/v1/geo/reports`
- **Authentication**: Public
- **Query Parameters**:
  - `bbox`: `string` (`min_lon,min_lat,max_lon,max_lat` e.g., `72.75,18.85,73.05,19.25`) [Required]
  - `status`: `string` (default: `"VERIFIED,PENDING"`)
  - `category`: `string` (optional)
  - `hours_ago`: `int` (default: `24`)
- **Response Shape** (`200 OK`): GeoJSON `FeatureCollection` optimized for Leaflet vector layers.

#### 5. Spatial-Temporal Clusters
- **Purpose**: Fetch aggregated incident clusters for heatmap and cluster marker rendering.
- **Method & Path**: `GET /api/v1/geo/clusters`
- **Authentication**: Public
- **Query Parameters**: `bbox`, `hours_ago`, `min_cluster_size`
- **Response Shape** (`200 OK`): List of cluster centroids, member counts, and dominant hazard categories.

---

### 2.3 Intelligence & Deep Inspection Endpoints

#### 6. Detailed Intelligence & Explainability Breakdown
- **Purpose**: Detailed algorithmic justification for credibility scoring, nearest IMD sensor corroboration, and duplicate links.
- **Method & Path**: `GET /api/v1/reports/{id}/intelligence`
- **Authentication**: Authenticated (`DEOC_OFFICER`, `ADMIN`, `MET_ANALYST`)
- **Response Shape** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "report_id": "a98b065f-46e3-4c31-893f-c689fbfb6021",
      "overall_credibility_score": 0.88,
      "scoring_factors": {
        "source_weight": 0.65,
        "spatial_cluster_bonus": 0.20,
        "sensor_corroboration_score": 0.90,
        "media_evidence_score": 0.85,
        "anomaly_penalty": 0.00
      },
      "explanation_text": "High credibility: Corroborated by Santacruz AWS (4.2 km away recording 48 mm/hr rainfall) and supported by 3 nearby citizen submissions within 1.2 km.",
      "nearest_weather_stations": [
        {
          "station_code": "IMD_BOM_04",
          "station_name": "Santacruz AWS",
          "distance_km": 4.2,
          "observed_rainfall_mm": 48.0,
          "observed_at": "2026-08-29T05:30:00Z"
        }
      ],
      "duplicate_cluster": {
        "cluster_id": "c_9981...",
        "total_reports": 4,
        "is_primary": true
      }
    }
  }
  ```

---

### 2.4 Disaster Management & Administrative Triage Endpoints

#### 7. Admin Verification Queue
- **Purpose**: Backlog of unverified and high-urgency reports awaiting officer triage.
- **Method & Path**: `GET /api/v1/admin/verification-queue`
- **Authentication**: Authenticated (`DEOC_OFFICER`, `ADMIN`)
- **Query Parameters**: `priority` (`"HIGH"`, `"NORMAL"`), `category`, `jurisdiction`, `page`, `page_size`
- **Response Shape** (`200 OK`): Priority-ranked queue of reports with credibility scores and corroboration badges.

#### 8. Verify Report
- **Purpose**: Authorize a weather report as confirmed ground truth.
- **Method & Path**: `POST /api/v1/admin/reports/{id}/verify`
- **Authentication**: Authenticated (`DEOC_OFFICER`, `ADMIN`)
- **Request Body**:
  ```json
  {
    "notes": "Confirmed with Ward L Flood Control Unit. SDRF unit notified.",
    "broadcast_alert": true
  }
  ```
- **Response Shape** (`200 OK`): Updated report with status `"VERIFIED"` and verification event audit ID.

#### 9. Reject Report (False/Hoax)
- **Purpose**: Reject false alarm or spam report.
- **Method & Path**: `POST /api/v1/admin/reports/{id}/reject`
- **Authentication**: Authenticated (`DEOC_OFFICER`, `ADMIN`)
- **Request Body**:
  ```json
  {
    "rejection_reason": "INACCURATE_LOCATION",
    "notes": "Photo is from 2021 archive, not current event."
  }
  ```
- **Response Shape** (`200 OK`): Updated report with status `"REJECTED"`.

#### 10. Mark Report as Duplicate
- **Purpose**: Merge redundant report into an existing cluster.
- **Method & Path**: `POST /api/v1/admin/reports/{id}/mark-duplicate`
- **Authentication**: Authenticated (`DEOC_OFFICER`, `ADMIN`)
- **Request Body**:
  ```json
  {
    "primary_report_id": "target_report_uuid"
  }
  ```
- **Response Shape** (`200 OK`): Updated report with status `"DUPLICATE"`.

---

### 2.5 Analytics & System Health Endpoints

#### 11. Dashboard Summary & KPI Metrics
- **Purpose**: High-level telemetry for the executive dashboard overview.
- **Method & Path**: `GET /api/v1/dashboard/summary`
- **Authentication**: Public / Authenticated
- **Response Shape** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "active_critical_alerts": 7,
      "reports_last_24h": 342,
      "verification_rate_pct": 89.4,
      "active_clusters_count": 14,
      "dominant_hazard": "FLOOD_WATERLOGGING",
      "severity_distribution": {
        "CRITICAL": 12,
        "SEVERE": 45,
        "HIGH": 110,
        "MODERATE": 130,
        "LOW": 45
      }
    }
  }
  ```

#### 12. Analytics Time-Series & Trends
- **Purpose**: Temporal aggregation for Recharts visualizations.
- **Method & Path**: `GET /api/v1/analytics/trends`
- **Query Parameters**: `interval` (`"hour"`, `"day"`), `from_date`, `to_date`, `category`
- **Response Shape** (`200 OK`): Time-series array with report volumes, average rainfall, and verification ratios.

#### 13. System Health & Ingestion Adapter Status
- **Purpose**: Telemetry on backend adapters, Redis stream lag, and database connections.
- **Method & Path**: `GET /api/v1/health` & `GET /api/v1/sources/status`
- **Authentication**: Public (basic) / Admin (detailed adapter telemetry)
- **Response Shape** (`200 OK`): Database ping, Redis latency, S3 connection, and per-adapter last-polled timestamps.
