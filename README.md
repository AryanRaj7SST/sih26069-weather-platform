# National Weather Big Data Analytics Platform

**Smart India Hackathon 2026 — Problem Statement ID**: `SIH26069`  
**Domain**: Big Data Analytics / Disaster Management / Geospatial Intelligence

---

## 1. Project Overview & Mission
The **National Weather Big Data Analytics Platform** is a scalable, real-time intelligence system engineered to ingest, corroborate, and analyze multi-source meteorological feeds and crowdsourced citizen incident reports during extreme weather emergencies.

The platform bridges the gap between high-altitude meteorological models (IMD radar/AWS) and localized ground realities (urban waterlogging, flash floods, landslides, storm damage) through:
- High-throughput multi-source ingestion (Citizen reports, IMD telemetry, RSS feeds).
- Intelligent classification and spatial-temporal deduplication.
- Explainable credibility scoring with sensor corroboration.
- Real-time GIS visualization and administrative triage for disaster response forces (NDRF, SDRF, DEOCs).

---

## 2. High-Level Architecture

```
[Citizen Reports & Weather Feeds]
               │
               ▼
   [Pluggable Ingestion Adapters]
               │
               ▼
     [Redis Streams Buffer]
               │
               ▼
[Intelligence Engine (Deduplication + Sensor Corroboration + Credibility)]
               │
               ▼
 [PostgreSQL 16 + PostGIS]  ◄───►  [MinIO / S3 Media Storage]
               │
               ▼
   [FastAPI Real-time Layer]
               │
               ▼
[React 18 + Leaflet + Recharts Disaster Management Dashboard]
```

---

## 3. Repository Structure

```
/
├── AGENTS.md                    # Primary guidelines and guardrails for developers & agents
├── README.md                    # Project overview and navigation guide
├── .gitignore                   # Security rules ignoring credentials and build artifacts
│
├── docs/                        # Complete Architectural Source of Truth
│   ├── PRD.md                   # Product requirements, personas, and SIH scope
│   ├── ARCHITECTURE.md          # Technical design, data flow, and pipeline architecture
│   ├── TECH_STACK.md            # Approved libraries, frameworks, and ADRs
│   ├── DATA_MODEL.md            # Entity specifications, spatial schemas, and indexes
│   ├── API_CONTRACT.md          # REST endpoint specifications, envelopes, and schemas
│   ├── EXTERNAL_SETUP.md        # Local vs. Cloud environment and API credentials guide
│   └── IMPLEMENTATION_PLAN.md   # Phased, incremental implementation roadmap
│
├── .agents/                     # Coding agent rules and repeatable workflows
│   ├── rules/
│   │   └── project-rules.md     # Persistent behavioral and architectural guardrails
│   └── workflows/
│       ├── verify.md            # Verification checklist protocol
│       └── checkpoint.md        # Git hygiene and checkpoint commit protocol
│
├── front-end/                   # React + TypeScript + Tailwind CSS application root
└── back-end/                    # FastAPI + SQLAlchemy + GeoAlchemy2 application root
```

---

## 4. Documentation & Source of Truth

The system architecture and specifications are documented comprehensively in `/docs`:
- **Product Scope & Requirements**: [docs/PRD.md](file:///Users/akshatjain/Documents/SIH/docs/PRD.md)
- **System Architecture**: [docs/ARCHITECTURE.md](file:///Users/akshatjain/Documents/SIH/docs/ARCHITECTURE.md)
- **Technology Stack & Decisions**: [docs/TECH_STACK.md](file:///Users/akshatjain/Documents/SIH/docs/TECH_STACK.md)
- **Data Model & Spatial Schema**: [docs/DATA_MODEL.md](file:///Users/akshatjain/Documents/SIH/docs/DATA_MODEL.md)
- **API Contracts & Envelopes**: [docs/API_CONTRACT.md](file:///Users/akshatjain/Documents/SIH/docs/API_CONTRACT.md)
- **External Configuration Runbook**: [docs/EXTERNAL_SETUP.md](file:///Users/akshatjain/Documents/SIH/docs/EXTERNAL_SETUP.md)
- **Incremental Roadmap**: [docs/IMPLEMENTATION_PLAN.md](file:///Users/akshatjain/Documents/SIH/docs/IMPLEMENTATION_PLAN.md)

---

## 5. Implementation Roadmap Status
Implementation is structured across 16 small, independently verifiable phases (Phase 0 to Phase 15).

> [!IMPORTANT]
> The project is currently in **Phase 0 (Initialization & Architecture Specification)**.  
> Production code, database migrations, and cloud infrastructure setup will be introduced incrementally starting in Phase 1 according to [docs/IMPLEMENTATION_PLAN.md](file:///Users/akshatjain/Documents/SIH/docs/IMPLEMENTATION_PLAN.md).
