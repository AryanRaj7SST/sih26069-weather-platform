# Workflow: Verification Protocol (`verify.md`)

Use this workflow to validate code quality, tests, schemas, and build integrity across backend and frontend before completing any task or phase.

---

## 1. Backend Verification Steps
Run from `/back-end`:

1. **Python Syntax and Static Type Checking**:
   ```bash
   mypy app
   ```
2. **Code Linting & Formatting**:
   ```bash
   ruff check .
   ruff format --check .
   ```
3. **Database Migration Consistency**:
   ```bash
   alembic check
   ```
4. **Automated Unit & Integration Tests**:
   ```bash
   pytest -v --cov=app --cov-report=term-missing
   ```

---

## 2. Frontend Verification Steps
Run from `/front-end`:

1. **TypeScript Type Checking**:
   ```bash
   npm run typecheck # (or tsc --noEmit)
   ```
2. **ESLint Validation**:
   ```bash
   npm run lint
   ```
3. **Production Bundle Build Test**:
   ```bash
   npm run build
   ```

---

## 3. End-to-End & Contract Verification
1. **API Schema Alignment**:
   - Verify that frontend API client types match the backend OpenAPI schemas in `/docs/API_CONTRACT.md`.
2. **Spatial Data Integrity**:
   - Ensure coordinate order is consistently `[longitude, latitude]` for GeoJSON / PostGIS representations and `[latitude, longitude]` for Leaflet UI mapping components.

---

## 4. Failure Reporting Protocol
If any check fails:
1. **Do not ignore or suppress errors.**
2. Log the exact command, exit code, and error trace.
3. Diagnose whether the failure is due to missing types, schema mismatch, or broken logic.
4. Correct the code and re-run all checks from Step 1.
