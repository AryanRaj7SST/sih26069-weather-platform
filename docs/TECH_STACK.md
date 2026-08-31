# Technology Stack & Tooling Reference

**Platform**: National Weather Big Data Analytics Platform (`SIH26069`)
**Status**: **SYNCHRONIZED WITH CURRENT REPOSITORY & DEPENDENCY MANIFESTS**

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
│  Python 3.11+ / 3.14  •  FastAPI  •  Pydantic v2  •  SQLAlchemy 2.0 (Async) │
│  GeoAlchemy2  •  Alembic (Migrations)  •  httpx (Async Ingestion HTTP)     │
│  FastEmbed / Sentence-Transformers (Local Dense Embeddings)                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ Database Driver / Redis Protocol / S3 SDK
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA & INFRASTRUCTURE                              │
│  PostgreSQL 16+ with PostGIS 3.4+ (Primary System of Record)                │
│  Redis 7+ / Redis Streams (6 Dedicated Streams & Caching)                   │
│  MinIO / AWS S3 (Binary Media Object Storage)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component-by-Component Technology Rationale

### 2.1 Frontend Tier
| Technology | Role in Architecture | Technical Rationale |
| :--- | :--- | :--- |
| **React 18+ & Vite** | Application Framework & Bundler | Fast HMR, lightweight bundle size, modern component ecosystem. |
| **TypeScript 5+** | Language | Compile-time type safety, eliminating runtime undefined errors in complex geospatial structures. |
| **Tailwind CSS & shadcn/ui** | Styling & UI Component Library | Accessible, unstyled primitives customizable via Tailwind; delivers an authoritative, high-density disaster-management aesthetic. |
| **TanStack Query v5** | Server State Management | Robust caching, automatic background refetching, and query invalidation upon real-time SSE triggers. |
| **React Hook Form + Zod** | Form Handling & Validation | High-performance uncontrolled form inputs with strict schema validation for citizen reporting. |
| **Leaflet & React-Leaflet** | Interactive Geospatial Mapping | Lightweight, mobile-friendly GIS rendering, vector tile support, and marker clustering plugins. |
| **Recharts** | Analytics & Metric Charts | Declarative SVG charting for temporal trends, flood hydrographs, and hazard distributions. |

### 2.2 Backend Tier
| Technology | Role in Architecture | Technical Rationale |
| :--- | :--- | :--- |
| **Python 3.11+ / 3.14** | Runtime Environment | Extensive geospatial (Shapely/PyProj), scientific, and AI/NLP library support with asynchronous concurrency. |
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
| **Redis 7+ (Redis Streams)** | Event Queue & In-Memory Cache | Microsecond latency, consumer groups for worker load balancing, and 6 dedicated stream topics. |
| **MinIO (Local) / AWS S3** | Object Storage | Scalable storage for citizen photos and videos; prevents relational database bloat. |

---

## 3. AI & Data Intelligence Strategy

1. **Deterministic Rule Engine**: First-pass spam filtering, boundary checking, and threshold categorization.
2. **Local Text Embeddings (`FastEmbed` / `sentence-transformers`)**:
   - Generates compact vector embeddings for report text without requiring external GPU infrastructure.
   - Used for semantic duplicate candidate grouping.
3. **Transparent Credibility Engine**:
   - Deterministic multi-factor formula based on verifiable metrics (source class prior, quality score, crowd volume signal, digital evidence provenance, physical station delta).
4. **Targeted LLM Invocation (Optional Cloud/Local Fallback)**:
   - Reserved strictly for generating human-readable crisis summaries or categorizing unstructured vernacular text reports.
   - LLMs are **never** used as an opaque or unquestioned ground truth.

---

## 4. Architectural Decision Records (ADRs)

### ADR-001: Redis Streams for Local Event Buffering
- **Context**: The platform requires event buffering between multi-source ingestion adapters, background consumer workers, and the intelligence pipeline.
- **Decision**: Use Redis Streams (`stream:weather:*`) for local development and MVP evaluation.
- **Rationale**: Kafka introduces significant operational overhead (JVM memory footprint, multiple containers) during evaluation. Redis Streams provides consumer groups, message replay, and microsecond latency.
- **Future Scalability**: Ingestion adapters push events through a clean `EventPublisher` abstraction. Migrating from Redis Streams to Apache Kafka in future enterprise scaling requires replacing only the publisher/consumer driver with zero changes to business logic.

### ADR-002: Rejection of Binary Storage in Relational Database
- **Context**: Citizen weather reports frequently include photos and video clips.
- **Decision**: Store all media files in S3-compatible object storage (MinIO locally) and persist only metadata, S3 keys, content hashes, and presigned URLs in PostgreSQL (`report_media`).
- **Rationale**: Relational databases degrade in query performance and backup speed when storing multi-megabyte binary blobs.
