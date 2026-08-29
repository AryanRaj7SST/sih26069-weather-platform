# External Services, Credentials & Environment Setup

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)  
**Purpose**: Comprehensive guide separating automated local environments from manual human developer configurations and cloud provisioning.

> [!NOTE]
> **No manual external setup is required during this initialization phase.**
> The local MVP is engineered to run completely offline using local containers (PostgreSQL+PostGIS, Redis, MinIO) and local embeddings (FastEmbed). This document serves as the formal operational runbook for when external cloud services and live government APIs are introduced in later phases.

---

## 1. Automated Local Setup vs. Manual Human Actions

```
┌─────────────────────────────────────────────────────────────┐
│                 AUTOMATED VIA LOCAL SCRIPTS                 │
│  - Local PostgreSQL 16 + PostGIS initialization             │
│  - Local Redis 7 container configuration                    │
│  - Local MinIO S3-compatible storage setup & bucket creation│
│  - Local text embedding models download (FastEmbed)         │
│  - Database migrations execution (Alembic)                  │
│  - Seed & demo data generation                              │
└─────────────────────────────────────────────────────────────┘
                               ▲
                               │ Isolated Boundary
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                MANUAL HUMAN DEVELOPER ACTIONS               │
│  - Registration for IMD Data Portal / Open City APIs        │
│  - Provisioning of Data.gov.in API Keys                     │
│  - Procurement of Cloud Object Storage (AWS S3 / GCP GCS)   │
│  - Provisioning of Production Managed DB (Neon/RDS/Supabase)│
│  - Cloud LLM Provider API Keys (OpenAI / Gemini / Anthropic)│
│  - Production JWT Signing Secret Generation                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Catalog of Future Manual Actions

### 2.1 Government Open Data & IMD Portal Access
* **What**: Register an appropriate developer/organization account on [IMD API Portal](https://api.imd.gov.in) and [data.gov.in](https://data.gov.in) and request access to IMD weather telemetry / nowcast datasets.
* **Why**: To enable live polling of official Automatic Weather Stations (AWS) and Doppler weather radar precipitation feeds.
* **Where**: IMD API Portal / Government Data Portal web interface.
* **Credential Produced**: `IMD_API_KEY` / `DATA_GOV_API_KEY` (string tokens).
* **Where it belongs**: `back-end/.env` $\rightarrow$ `IMD_API_KEY`, `DATA_GOV_API_KEY`.
* **Security Rule**: **NEVER commit this key to Git.** Always reference via environment variables.

---

### 2.2 Cloud Object Storage Provisioning (AWS S3 / Cloudflare R2)
* **What**: Create an S3 storage bucket (e.g., `sih26069-weather-media`) with private ACL and configure IAM credentials with read/write access.
* **Why**: For production deployment where local MinIO is replaced by durable cloud storage.
* **Where**: AWS Management Console / Cloudflare Dashboard.
* **Credentials Produced**:
  - `S3_ENDPOINT_URL`
  - `S3_ACCESS_KEY_ID`
  - `S3_SECRET_ACCESS_KEY`
  - `S3_BUCKET_NAME`
  - `S3_REGION`
* **Where it belongs**: `back-end/.env`.
* **Security Rule**: Never check S3 secret keys into version control. Use least-privilege IAM policies restricted only to the media bucket.

---

### 2.3 Cloud LLM / AI API Keys (Optional Ambiguity Resolution)
* **What**: Obtain an API key from Google AI Studio (Gemini) or Anthropic/OpenAI for natural language incident summarization and multi-lingual translation.
* **Why**: To generate human-readable crisis summaries for DEOC officers and translate regional Indian languages (Hindi, Marathi, Bengali, Tamil, etc.).
* **Where**: AI Studio / Cloud Provider Console.
* **Credential Produced**: `LLM_API_KEY` (e.g., `GEMINI_API_KEY`).
* **Where it belongs**: `back-end/.env` $\rightarrow$ `LLM_API_KEY`.
* **Security Rule**: Strict zero-commit policy. Fallback to local deterministic templates if the key is missing.

---

### 2.4 Production Database & Managed Redis
* **What**: Provision a managed PostgreSQL instance with PostGIS enabled (e.g., AWS RDS, Supabase, Neon) and managed Redis (Upstash, AWS ElastiCache).
* **Why**: High-availability multi-region hosting for production demonstration.
* **Where**: Cloud provider management console.
* **Credentials Produced**: `DATABASE_URL` (with PostGIS connection string) and `REDIS_URL`.
* **Where it belongs**: Production environment secret store / `.env`.

---

## 3. Master Environment Variable Reference Template

When setting up `back-end/.env`, use the sanitized schema below (available in `back-end/.env.example` during Phase 1):

```bash
# ==============================================================================
# NATIONAL WEATHER BIG DATA ANALYTICS PLATFORM (.env.example)
# ==============================================================================

# Application Environment
ENVIRONMENT=development
DEBUG=true
API_V1_STR=/api/v1
PROJECT_NAME="National Weather Big Data Analytics Platform"

# Security & JWT Authentication
SECRET_KEY=change-this-to-a-secure-random-64-character-hex-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Primary Database (PostgreSQL + PostGIS)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/weather_platform
DATABASE_ECHO=false

# In-Memory Cache & Message Streams (Redis)
REDIS_URL=redis://localhost:6379/0

# Object Storage (MinIO local default / S3 production)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=weather-media
S3_REGION=us-east-1
S3_USE_SSL=false

# External Meteorological & Government APIs
DATA_GOV_API_KEY=
IMD_API_ENDPOINT=https://api.imd.gov.in/api/v1
IMD_API_KEY=

# AI & Semantic Intelligence
EMBEDDING_MODEL_NAME=BAAI/bge-small-en-v1.5
LLM_PROVIDER=none # options: none | gemini | openai
LLM_API_KEY=

# CORS Configuration
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

---

## 4. Git Security & Secret Prevention Guidelines

1. **Pre-commit scanning**: The repository includes `.gitignore` matching all `.env*` files except `.env.example`.
2. **Sanitized Defaults**: Default values in `.env.example` must point strictly to local Docker endpoints with dummy passwords (`postgres:postgres`, `minioadmin:minioadmin`).
3. **Emergency Secret Revocation**: If any real production API key is accidentally committed to Git history, immediately revoke and regenerate the key from the provider dashboard; merely deleting the commit from working tree is insufficient.
