from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .memory import IncidentMemoryStore, MemoryUnavailable
from .models import utc_now

PROOF_CATEGORY = "eligibility_proof"


def new_run_id() -> str:
    return f"PRF-{uuid4().hex[:20].upper()}"


def tenant_for(run_id: str) -> str:
    if not run_id.startswith("PRF-") or len(run_id) != 24 or not run_id[4:].isalnum():
        raise ValueError("invalid proof run id")
    return f"mercury-proof-{run_id[4:].lower()}"


def proof_store(path: Path, run_id: str) -> IncidentMemoryStore:
    return IncidentMemoryStore(path, tenant_for(run_id))


def create_run(path: Path) -> dict[str, Any]:
    run_id = new_run_id()
    body: dict[str, Any] = {
        "run_id": run_id,
        "proof_version": "mercury-sibyl-cross-process-v1",
        "status": "ready",
        "created_at": utc_now(),
        "storage": {"provider": "sibyl-memory-client", "tenant_isolated": True},
        "session_a": None,
        "session_b": None,
        "base": {"status": "UNANCHORED", "network": "Base Sepolia", "chain_id": 84532},
    }
    record = proof_store(path, run_id).set_entity(PROOF_CATEGORY, run_id, body, status="active")
    body["sibyl_proof_record_id"] = record["id"]
    proof_store(path, run_id).set_entity(PROOF_CATEGORY, run_id, body, status="active")
    return body


def get_run(path: Path, run_id: str) -> dict[str, Any] | None:
    record = proof_store(path, run_id).get_entity(PROOF_CATEGORY, run_id)
    return record["body"] if record else None


@contextmanager
def run_lock(path: Path, run_id: str) -> Iterator[None]:
    lock_dir = path.parent / ".proof-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{run_id}.lock"
    fd: int | None = None
    deadline = time.monotonic() + 15
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {utc_now()}".encode())
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError("proof run is already executing")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(fd)
        lock_path.unlink(missing_ok=True)


def execute_worker(path: Path, run_id: str, phase: str) -> dict[str, Any]:
    with run_lock(path, run_id):
        before = get_run(path, run_id)
        if not before:
            raise ValueError("proof run not found")
        if phase == "session-a" and before.get("session_a"):
            raise ValueError("Session A already completed")
        if phase == "session-b" and not (before.get("session_a") or {}).get("process_ended"):
            raise ValueError("Session A must end before Session B starts")
        if phase == "session-b" and before.get("session_b"):
            raise ValueError("Session B already completed")
        command = [sys.executable, "-m", "mercury.proof_worker", phase, str(path), run_id]
        env = os.environ.copy()
        package_root = str(Path(__file__).resolve().parents[1])
        env["PYTHONPATH"] = package_root + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False, env=env)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout)[-1000:].strip()
            raise MemoryUnavailable(f"fresh session worker failed ({result.returncode}): {detail}")
        try:
            output = json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            raise MemoryUnavailable("fresh session worker returned invalid proof") from exc
        if not output.get("process_ended"):
            raise MemoryUnavailable("fresh session did not confirm process termination")
        after = get_run(path, run_id)
        if not after:
            raise MemoryUnavailable("Sibyl proof record disappeared after worker exit")
        session_key = "session_a" if phase == "session-a" else "session_b"
        after[session_key]["orchestrator_confirmed_exit_code"] = result.returncode
        after[session_key]["orchestrator_confirmed_exit_at"] = utc_now()
        proof_store(path, run_id).set_entity(PROOF_CATEGORY, run_id, after, status="active")
        return after
