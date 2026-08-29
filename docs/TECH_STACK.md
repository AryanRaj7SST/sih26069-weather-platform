# Technology Stack & Tooling Reference

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)

---

## 1. Core Technology Selection Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND                                    │
│  React 18+  •  TypeScript 5+  •  Vite  •  Tailwind CSS  •  shadcn/ui        │
│  React Router v6  •  TanStack Query v5  •  React Hook Form  •  Zod          │
│  Leaflet + React-Leaflet (GIS Mapping)  •  Recharts (Data Visualization)    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ HTTP REST + Server-Sent Events (SSE)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 BACKEND                                     │
│  Python 3.11+  •  FastAPI  •  Pydantic v2  •  SQLAlchemy 2.0 (Async)        │
│  GeoAlchemy2  •  Alembic (Migrations)  •  httpx (Async Ingestion HTTP)     │
│  FastEmbed / Sentence-Transformers (Local Embeddings)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ Database Driver / Redis Protocol / S3 SDK
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA & INFRASTRUCTURE                              │
│  PostgreSQL 16+ with PostGIS 3.4+ (Primary System of Record)                │
│  Redis 7+ / Redis Streams (Message Buffering, Real-Time Cache & PubSub)     │
│  MinIO / AWS S3 (Binary Media Object Storage)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component-by-Component Technology Rationale

### 2.1 Frontend Tier
| Technology | Role in Architecture | Technical Rationale |
| :--- | :--- | :--- |
| **React 18+ & Vite** | Application Framework & Bundler | Ultra-fast HMR, lightweight bundle size, modern component ecosystem. |
| **TypeScript 5+** | Language | Compile-time type safety, eliminating runtime undefined errors in complex geospatial structures. |
| **Tailwind CSS & shadcn/ui** | Styling & UI Component Library | Accessible, unstyled primitives customizable via Tailwind; delivers an authoritative, high-density disaster-management aesthetic. |
| **TanStack Query v5** | Server State Management | Robust caching, automatic background refetching, and query invalidation upon real-time SSE triggers. |
| **React Hook Form + Zod** | Form Handling & Validation | High-performance uncontrolled form inputs with strict schema validation for citizen reporting. |
| **Leaflet & React-Leaflet** | Interactive Geospatial Mapping | Lightweight, mobile-friendly GIS rendering, vector tile support, and marker clustering plugins. |
| **Recharts** | Analytics & Metric Charts | Declarative SVG charting for temporal trends, flood hydrographs, and hazard distributions. |

### 2.2 Backend Tier
| Technology | Role in Architecture | Technical Rationale |
| :--- | :--- | :--- |
| **Python 3.11+** | Runtime Environment | Extensive geospatial (Shapely/PyProj), scientific, and AI/NLP library support with asynchronous concurrency. |
| **FastAPI** | Web Framework | Native async support, high throughput, automatic OpenAPI documentation, and native Pydantic v2 integration. |
| **Pydantic v2** | Data Validation & Serialization | Rust-accelerated validation core for low-latency request/response serialization. |
| **SQLAlchemy 2.0 (Async)** | Object Relational Mapper | Modern `select()` syntax, async connection pooling (`asyncpg`), and robust relationship management. |
| **GeoAlchemy2** | Spatial ORM Extension | PostGIS geometry column binding and seamless spatial function generation (`ST_DWithin`, `ST_Centroid`). |
| **Alembic** | Database Migrations | Deterministic, version-controlled schema evolution with PostGIS type awareness. |
| **httpx** | Async HTTP Client | Non-blocking HTTP calls for concurrent polling across external weather portals and IMD endpoints. |

### 2.3 Storage & Ingestion Tier
| Technology | Role in Architecture | Technical Rationale |
| :--- | :--- | :--- |
| **PostgreSQL 16 + PostGIS 3.4** | System of Record | Enterprise spatial indexing (GiST), ACID compliance, JSONB document querying, and temporal partitioning. |
| **Redis 7+ (Streams & Pub/Sub)** | Event Queue & In-Memory Cache | Microsecond latency, consumer groups for worker load balancing, and built-in pub/sub for live SSE updates. |
| **MinIO (Local) / AWS S3** | Object Storage | Scalable storage for high-resolution citizen photos and videos; prevents relational database bloat. |

---

## 3. AI & Data Intelligence Strategy

1. **Deterministic Rule Engine**: First-pass spam filtering, boundary checking, and threshold categorization.
2. **Local Text Embeddings (`FastEmbed` / `sentence-transformers`)**:
   - Generates compact 384-dimensional vector embeddings for report text without requiring external API calls or GPUs.
   - Used for semantic duplicate candidate grouping.
3. **Transparent Credibility Engine**:
   - Mathematical formula based on verifiable metrics (source class, spatial clustering density, official IMD sensor delta, photo presence).
4. **Targeted LLM Invocation (Optional Cloud/Local Fallback)**:
   - Reserved strictly for generating human-readable crisis summaries or categorizing unstructured vernacular text reports.
   - LLMs are **never** used as an opaque or unquestioned ground truth.

---

## 4. Architectural Decision Records (ADRs)

### ADR-001: Why Redis Streams instead of Apache Kafka for the MVP
- **Context**: The platform requires an event buffer between data ingestion adapters and background intelligence workers.
- **Decision**: Use Redis Streams for the local development and MVP environment.
- **Rationale**: Kafka introduces significant operational overhead (ZooKeeper/KRaft, JVM memory footprint, multiple containers) during early development. Redis is already required for caching and session state.
- **Future Scalability**: Ingestion adapters push events through a clean `EventPublisher` abstraction. Migrating from Redis Streams to Apache Kafka or Redpanda in Phase 15 requires replacing only the publisher/consumer driver with zero changes to business logic.

### ADR-002: Rejection of Binary Storage in Relational Database
- **Context**: Citizen weather reports frequently include high-resolution photos and video clips.
- **Decision**: Store all media files in S3-compatible object storage (MinIO locally) and persist only metadata, S3 keys, content hashes, and presigned URLs in PostgreSQL.
- **Rationale**: Relational databases degrade in query performance and backup speed when storing multi-megabyte binary blobs.

---

## 5. Development & Testing Tooling

- **Backend**:
  - Linter & Formatter: `ruff`
  - Type Checker: `mypy` (strict mode)
  - Test Suite: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` (for `AsyncClient` tests)
- **Frontend**:
  - Linter: `eslint` with `@typescript-eslint`
  - Formatter: `prettier`
  - Type Checker: `tsc --noEmit`
