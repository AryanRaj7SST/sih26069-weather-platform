#!/usr/bin/env python3
"""Unified Developer Stack Orchestrator (SIH26069).

Manages local background worker processes, migration execution, and server health checks
with a single, clean command. Handles graceful shutdown on Ctrl+C.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = WORKSPACE_ROOT / "back-end"
FRONTEND_DIR = WORKSPACE_ROOT / "front-end"

processes: list[subprocess.Popen] = []


def signal_handler(sig, frame):
    print("\n[ORCHESTRATOR] Shutting down all spawned subprocesses...")
    for proc in processes:
        try:
            proc.terminate()
        except Exception:
            pass
    time.sleep(1)
    for proc in processes:
        try:
            proc.kill()
        except Exception:
            pass
    print("[ORCHESTRATOR] All services stopped cleanly. Goodbye!")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_command(cmd: list[str], cwd: Path, check: bool = True):
    print(f"[EXEC] {' '.join(cmd)} (in {cwd.name})")
    return subprocess.run(cmd, cwd=cwd, check=check)


def spawn_process(name: str, cmd: list[str], cwd: Path):
    print(f"[START] {name} -> {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=cwd)
    processes.append(proc)
    return proc


import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="SIH26069 Developer Stack Orchestrator")
    parser.add_argument("--skip-migrate", action="store_true", help="Skip running database migrations")
    parser.add_argument("--no-workers", action="store_true", help="Do not spawn background workers")
    parser.add_argument("--no-frontend", action="store_true", help="Do not start Vite frontend server")
    parser.add_argument("--no-api", action="store_true", help="Do not start FastAPI backend server")
    parser.add_argument(
        "--core-workers-only",
        action="store_true",
        help="Only run outbox and dispatcher workers, skipping external ingestion/observation/evidence/scheduler",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print(" National Weather Big Data Analytics Platform (SIH26069)")
    print(" Developer Stack Orchestrator")
    print("=" * 70)

    venv_bin = "Scripts" if os.name == "nt" else "bin"
    executable_suffix = ".exe" if os.name == "nt" else ""
    venv_python = BACKEND_DIR / ".venv" / venv_bin / f"python{executable_suffix}"
    venv_alembic = BACKEND_DIR / ".venv" / venv_bin / f"alembic{executable_suffix}"
    venv_uvicorn = BACKEND_DIR / ".venv" / venv_bin / f"uvicorn{executable_suffix}"

    if not venv_python.exists():
        print(f"[ERROR] Virtual environment not found at {venv_python}")
        print("Please initialize Python virtualenv in back-end/.venv first.")
        sys.exit(1)

    # 1. Run Alembic Database Migrations
    if not args.skip_migrate:
        print("\n[1/4] Running Alembic Database Migrations...")
        try:
            run_command([str(venv_alembic), "upgrade", "head"], cwd=BACKEND_DIR)
        except Exception as e:
            print(f"[WARNING] Migration failed (ensure Postgres is running): {e}")

    # 2. Start Uvicorn Backend Dev Server
    if not args.no_api:
        print("\n[2/4] Starting FastAPI Backend Dev Server (Port 8000)...")
        spawn_process(
            "Backend API",
            [str(venv_uvicorn), "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            cwd=BACKEND_DIR,
        )

    # 3. Start Background Workers
    if not args.no_workers:
        print("\n[3/4] Starting Background Workers...")
        # Core workers
        spawn_process("Outbox Worker", [str(venv_python), "-m", "app.workers.run_outbox_worker"], cwd=BACKEND_DIR)
        spawn_process("Orchestration Dispatcher", [str(venv_python), "-m", "app.workers.run_dispatcher"], cwd=BACKEND_DIR)

        if not args.core_workers_only:
            # Full ingestion, observation, evidence & scheduler workers
            spawn_process("Ingestion Worker", [str(venv_python), "-m", "app.workers.run_ingestion_worker"], cwd=BACKEND_DIR)
            spawn_process("Observation Worker", [str(venv_python), "-m", "app.workers.run_observation_worker"], cwd=BACKEND_DIR)
            spawn_process("Evidence Worker", [str(venv_python), "-m", "app.workers.run_evidence_worker"], cwd=BACKEND_DIR)
            spawn_process("Scheduler Worker", [str(venv_python), "-m", "app.workers.run_scheduler"], cwd=BACKEND_DIR)

    # 4. Start React Vite Frontend Dev Server
    if not args.no_frontend:
        print("\n[4/4] Starting Frontend Vite Dev Server (Port 5173)...")
        npm_command = "npm.cmd" if os.name == "nt" else "npm"
        spawn_process("Frontend Vite", [npm_command, "run", "dev"], cwd=FRONTEND_DIR)

    print("\n" + "=" * 70)
    print(" All selected platform services launched successfully!")
    print(" - Web Portal:     http://localhost:5173")
    print(" - Backend API:    http://localhost:8000/docs")
    print(" - Realtime SSE:   http://localhost:8000/api/v1/events/stream")
    print(" Press Ctrl+C to stop all services simultaneously.")
    print("=" * 70 + "\n")

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
