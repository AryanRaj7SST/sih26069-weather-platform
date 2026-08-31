# External Services, Credentials & Configuration Guide

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)
**Status**: **SYNCHRONIZED WITH CURRENT CODE & WORKER TOPOLOGY**

---

## 1. Local Automated Setup vs. Deferred Cloud Actions

```
┌─────────────────────────────────────────────────────────────┐
│                 AUTOMATED LOCAL MVP SERVICES                │
│  - Local PostgreSQL 16 + PostGIS (Port 5432)                │
│  - Local Redis 7 Container (Port 6379)                      │
│  - Local MinIO S3 Object Storage (Ports 9000/9001)          │
│  - Local Alembic Migrations (0001 -> 0004)                  │
│  - 6 Standalone Worker Processes                            │
│  - Deterministic Seed Feeds & IMD/CWC/NDMA Local Adapters   │
└─────────────────────────────────────────────────────────────┘
                               ▲
                               │ Isolated Boundary
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               DEFERRED PRODUCTION CLOUD ACTIONS             │
│  - Production Managed PostgreSQL with PostGIS (RDS/Neon)    │
│  - Production Managed Redis (AWS ElastiCache / Upstash)     │
│  - Production Cloud Storage (AWS S3 with Private IAM Bucket)│
│  - Production JWT Token Secret & OAuth2 Provider (Keycloak) │
│  - OpenTelemetry / Prometheus APM Monitoring Exporters      │
│  - Process Supervision Units (systemd / Kubernetes Pods)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. External Provider Status & Verification Matrix

| Source Provider | Provider Type | Local Simulation / Test | Live Provider Status | Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Demo Seed Feed** | Local Synthetic Feed | **Fully Verified** | **Live Local** | Deterministic generator for Mumbai/Delhi/Bengaluru weather incidents (development/test utility). |
| **IMD Nowcast** | Official Weather Feed | **Fully Verified (Mock)** | Not Live Verified | Ingests IMD AWS/CAP alert format; official API requires IMD credentials. |
| **NDMA SACHET** | National Disaster Alerts | **Fully Verified (Mock)** | Not Live Verified | Ingests CAP 1.2 XML/JSON alert feeds; production requires NDMA gateway. |
| **CWC NWDP** | Central Water Commission | **Fully Verified (Mock)** | Not Live Verified | Ingests hydrological river level telemetry; portal uses CKAN datastore format. |
| **GDELT Project** | Global News Feed | **Unit & Live Verified** | **LIVE PROVIDER VERIFIED** | Ingests disaster news via GDELT DOC 2.0 API (`http://api.gdeltproject.org`); rate limit interval $\ge 5.0\text{s}$; snippets only in `ArtList` mode. |
| **Mastodon** | Social Emergency Feed | **Unit & Live Verified** | **LIVE PROVIDER VERIFIED** | Queries public disaster hashtags via `https://mastodon.social`; rate limit interval $\ge 1.0\text{s}$; text keyword matching without coordinate fabrication. |

---

## 3. Configuration Reference

All application settings are defined in [app/core/config.py](file:///Users/akshatjain/Documents/SIH/back-end/app/core/config.py) and populated from `.env`:

### 3.1 Database & Core Infrastructure

| Variable Name | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | `postgresql+asyncpg://postgres:postgres@localhost:5432/weather_platform` | Asynchronous PostgreSQL + PostGIS connection URI |
| `DATABASE_ECHO` | No | `False` | SQLAlchemy SQL statement logging flag |
| `REDIS_URL` | **Yes** | `redis://localhost:6379/0` | Redis connection URI for streams and caching |
| `REALTIME_STREAM_NAME` | No | `stream:weather:realtime` | Redis Stream key for browser SSE events |
| `REALTIME_STREAM_MAXLEN` | No | `10000` | Approximate cap on Redis Stream retention |

### 3.2 Outbox & Worker Settings

| Variable Name | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `OUTBOX_WORKER_ENABLED` | No | `True` | Enables/disables outbox worker poll loop |
| `OUTBOX_WORKER_BATCH_SIZE` | No | `50` | Number of outbox rows claimed per batch |
| `OUTBOX_WORKER_POLL_INTERVAL_SECONDS` | No | `1.0` | Active polling loop frequency / idle sleep (seconds) |
| `OUTBOX_WORKER_MAX_ATTEMPTS` | No | `5` | Maximum delivery attempts before moving to `DEAD_LETTER` |
| `OUTBOX_WORKER_PRUNE_INTERVAL_SECONDS` | No | `3600` | Interval in seconds between historical prune runs |
| `OUTBOX_WORKER_RETENTION_HOURS` | No | `72` | Retention window in hours before pruning `PUBLISHED` rows |

### 3.3 Media Storage (MinIO / S3)

| Variable Name | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `S3_ENDPOINT_URL` | No | `http://localhost:9000` | MinIO / S3 API endpoint |
| `S3_ACCESS_KEY_ID` | No | `minioadmin` | S3 / MinIO access key ID |
| `S3_SECRET_ACCESS_KEY` | No | `minioadmin` | S3 / MinIO secret access key |
| `S3_BUCKET_NAME` | No | `weather-media` | Object storage bucket for report attachments |
| `S3_REGION` | No | `us-east-1` | S3 region identifier |

### 3.4 External Feed Settings

| Variable Name | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `IMD_API_ENDPOINT` | No | `https://api.imd.gov.in/api/v1` | IMD official API base URL |
| `IMD_API_KEY` | No | `""` | IMD API key (optional for local mock) |
| `NDMA_SACHET_RSS_URL` | No | `https://sachet.ndma.gov.in/...` | NDMA SACHET CAP alert URL |
| `CWC_NWDP_API_ENDPOINT`| No | `https://nwdp.nwic.gov.in/api/3/action/datastore_search` | CWC river telemetry API endpoint |
| `GDELT_DOC_ENDPOINT` | No | `http://api.gdeltproject.org/api/v2/doc/doc` | GDELT 2.0 Document API endpoint |
| `MASTODON_INSTANCE_URL`| No | `https://mastodon.social` | Mastodon instance URL |
| `MASTODON_HASHTAGS` | No | `mumbairains,delhirains,bengalururains...` | Monitored disaster hashtags |

---

## 4. Operational Runbook: Worker Daemons

The backend uses 6 modular standalone processes. To run the full system locally:

```bash
# 1. Start the API Server
cd back-end
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Start the Transactional Outbox Worker
python -m app.workers.run_outbox_worker

# 3. Start the Orchestration Dispatcher
python -m app.workers.run_dispatcher

# 4. Start Ingestion Consumer Workers
python -m app.workers.run_ingestion_worker
python -m app.workers.run_observation_worker
python -m app.workers.run_evidence_worker

# 5. Start the Ingestion Scheduler (Optional / On-Demand)
python -m app.workers.run_scheduler
```
