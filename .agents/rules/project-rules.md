# Project Rules & Coding Guardrails

## 1. Architectural Guardrails
- **PostgreSQL + PostGIS** is the sole system of record. Every spatial entity uses PostGIS geometry/geography points (`SRID 4326`).
- **Zero Binary Blobs in Database**: Photos, videos, and raw documents must be uploaded to S3/MinIO. Store only metadata, object keys, content types, and checksums in PostgreSQL.
- **Async & Scalable Backend**: FastAPI backend with async SQLAlchemy 2.0 sessions and Pydantic v2 schemas.
- **Decoupled Ingestion**: External sources and citizen reporting push into ingestion queues/streams (Redis Streams) before heavy processing.
- **Explainable Credibility**: Credibility scoring algorithm must output explicit, breakdown factors (source reputation, multi-sensor proximity, temporal correlation, media verification) — never opaque or ungrounded scores.
- **Explicit Separation of AI & Authority**: `credibility_score` (float 0-1) informs triage; `verification_status` (`PENDING`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`, `DUPLICATE`) is set by authorized administrative workflows or explicit validation rules.

## 2. Code Quality & Standards
- **Strong Typing**: 
  - Backend: Strict type annotations with Python `typing` and Pydantic v2.
  - Frontend: TypeScript strict mode with explicit interfaces and Zod validation schemas.
- **Small, Focused Modules**: Single-responsibility files under 300 lines. Avoid monolithic components or god-classes.
- **Fail Fast & Explicit Errors**: Return structured JSON error envelopes (`{"error": {"code": "...", "message": "...", "details": [...]}}`).
- **No Mocking in Production Paths**: Keep demo seed generators cleanly segregated from production adapters.

## 3. Database & Migration Protocol
- All database modifications must be managed through version-controlled Alembic migrations.
- Primary keys must use UUIDv4.
- Timestamps must always include timezone information (`timestamptz`).
- Foreign keys must define explicit cascading/nullification rules and indexes.

## 4. Security & Configuration
- Never hardcode IP addresses, credentials, or API tokens.
- Load configuration via Pydantic `BaseSettings` reading from environment variables.
- Maintain a sanitized `.env.example` file whenever new configuration keys are introduced.

## 5. Verification Before Delivery
- Do not mark tasks complete without verifying against the `.agents/workflows/verify.md` workflow.
- Ensure all automated unit/integration tests pass and linting checks succeed.
