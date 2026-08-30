# External Services, Credentials & Configuration Guide

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)
**Status**: **FROZEN FOR SIH/MVP SCOPE**

---

## 1. Automated Local Setup vs. Production Cloud Actions

```
┌─────────────────────────────────────────────────────────────┐
│                 AUTOMATED LOCAL MVP SERVICES                │
│  - Local PostgreSQL 16 + PostGIS (Port 5432)                │
│  - Local Redis 7 Container (Port 6379)                      │
│  - Local MinIO S3 Object Storage (Ports 9000/9001)          │
│  - Local Alembic Migrations (0001 -> 0004)                  │
│  - Seed Disaster Data & Weather Observations Telemetry      │
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

## 2. Authoritative Configuration Reference

All application configuration is managed via Pydantic Settings in [app/core/config.py](file:///Users/akshatjain/Documents/SIH/back-end/app/core/config.py) and populated from `.env` or system environment variables.

### 2.1 Database & Storage Settings

| Variable Name | Required | Default Value | Security Sensitivity | Description |
| :--- | :---: | :--- | :---: | :--- |
| `DATABASE_URL` | **Yes** | `postgresql+asyncpg://postgres:postgres@localhost:5432/weather_platform` | **Sensitive** | Asynchronous PostgreSQL + PostGIS connection string |
| `DATABASE_ECHO` | No | `False` | Low | SQLAlchemy SQL query echo debugging flag |
| `S3_ENDPOINT_URL` | No | `http://localhost:9000` | Low | S3 / MinIO API endpoint URL |
| `S3_ACCESS_KEY_ID` | No | `minioadmin` | **Sensitive** | S3 / MinIO access key ID |
| `S3_SECRET_ACCESS_KEY` | No | `minioadmin` | **Sensitive** | S3 / MinIO secret access key |
| `S3_BUCKET_NAME` | No | `weather-media` | Low | S3 bucket for citizen incident media |
| `S3_REGION` | No | `us-east-1` | Low | S3 region identifier |
| `S3_USE_SSL` | No | `False` | Low | Enable HTTPS for S3 communication |

### 2.2 Redis & Real-Time Event Stream Settings

| Variable Name | Required | Default Value | Security Sensitivity | Description |
| :--- | :---: | :--- | :---: | :--- |
| `REDIS_URL` | **Yes** | `redis://localhost:6379/0` | **Sensitive** | Redis connection URI for streams and cache |
| `REALTIME_STREAM_NAME` | No | `stream:weather:realtime` | Low | Redis Stream topic name for realtime events |
| `REALTIME_STREAM_MAXLEN` | No | `10000` | Low | Maximum approximate entries in Redis Stream |

### 2.3 Outbox Worker Settings

| Variable Name | Required | Default Value | Security Sensitivity | Description |
| :--- | :---: | :--- | :---: | :--- |
| `OUTBOX_WORKER_ENABLED` | No | `True` | Low | Enables/disables outbox worker poll loop |
| `OUTBOX_WORKER_BATCH_SIZE` | No | `50` | Low | Number of outbox rows claimed per batch |
| `OUTBOX_WORKER_POLL_INTERVAL_SECONDS` | No | `1.0` | Low | Active polling loop frequency / idle sleep (seconds) |
| `OUTBOX_WORKER_MAX_ATTEMPTS` | No | `5` | Low | Max delivery attempts before moving to `DEAD_LETTER` |
| `OUTBOX_WORKER_PRUNE_INTERVAL_SECONDS` | No | `3600` | Low | Interval in seconds between historical prune runs |
| `OUTBOX_WORKER_RETENTION_HOURS` | No | `72` | Low | Retention window in hours before pruning `PUBLISHED` rows |

### 2.4 API, Security & CORS Settings

| Variable Name | Required | Default Value | Security Sensitivity | Description |
| :--- | :---: | :--- | :---: | :--- |
| `ENVIRONMENT` | No | `development` | Low | Environment name (`development`, `production`, `testing`) |
| `DEBUG` | No | `True` | Low | Debugging and verbose logging mode |
| `API_V1_STR` | No | `/api/v1` | Low | Base route prefix for API endpoints |
| `PROJECT_NAME` | No | `"National Weather Big Data Analytics Platform"` | Low | Application name |
| `SECRET_KEY` | No | `"development-secret-key-change-in-production"` | **Sensitive** | Secret key for cryptographic signing |
| `ALLOWED_ORIGINS` | No | `["http://localhost:5173","http://localhost:3000"]` | Low | Allowed CORS origins for browser clients |
| `VITE_API_URL` | No | `http://localhost:8000` | Low | Frontend environment variable pointing to API |

---

## 3. Operations Runbook & Troubleshooting

### 3.1 Inspecting the Realtime Outbox in PostgreSQL
```sql
-- Check counts by status
SELECT status, COUNT(*) FROM realtime_outbox GROUP BY status;

-- Inspect failed records
SELECT id, event_id, event_type, attempts, max_attempts, last_error, created_at
FROM realtime_outbox
WHERE status = 'DEAD_LETTER'
ORDER BY created_at DESC;
```

### 3.2 Inspecting Redis Streams
```bash
# Check stream length
redis-cli XLEN stream:weather:realtime

# Read latest 5 messages
redis-cli XREVRANGE stream:weather:realtime + - COUNT 5
```

### 3.3 Database Health & Migration Check
```bash
cd back-end
source .venv/bin/activate
alembic current
alembic check
```

## 4. Git Security & Secret Prevention Guidelines

1. **Pre-commit scanning**: The repository includes `.gitignore` matching all `.env*` files except `.env.example`.
2. **Sanitized Defaults**: Default values in `.env.example` must point strictly to local Docker endpoints with dummy passwords (`postgres:postgres`, `minioadmin:minioadmin`).
3. **Emergency Secret Revocation**: If any real production API key is accidentally committed to Git history, immediately revoke and regenerate the key from the provider dashboard; merely deleting the commit from working tree is insufficient.
