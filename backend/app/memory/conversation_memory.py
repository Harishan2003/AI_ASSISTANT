# Module: backend.app.memory.conversation_memory
from __future__ import annotations

import asyncio
import copy
import enum
import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger("friday.memory.job_store")


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


def stable_hash(payload: Any) -> str:
    """Generate a deterministic SHA-256 hash of a payload dictionary or structure."""
    if isinstance(payload, dict):
        serialized = json.dumps(payload, sort_keys=True, default=str)
    elif isinstance(payload, list):
        serialized = json.dumps(payload, default=str)
    else:
        serialized = str(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def idempotency_key(job_type: str, fields: Dict[str, Any]) -> str:
    return f"{job_type}:{stable_hash(fields)}"


@dataclass
class MemoryJob:
    job_id: str
    job_type: str
    user_id: str
    status: JobStatus = JobStatus.QUEUED
    payload: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""
    result: Any = None
    error: str = ""
    error_state: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_attempts: int = 3
    timeout_seconds: float = 120.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    updated_at: float = field(default_factory=time.time)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "user_id": self.user_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status_url": f"/api/v1/memory/jobs/{self.job_id}/status",
        }


class MemoryJobStore:
    """
    Durable in-memory and asynchronous job queue for background memory ingestion.
    Supports idempotency key hashing, deduplication, retry tracking, and state transitions.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._jobs: Dict[str, MemoryJob] = {}
        self._by_idemp: Dict[str, str] = {}

    def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_fields: Dict[str, Any],
        user_id: str = "default",
        timeout_seconds: float = 120.0,
        max_attempts: int = 3,
    ) -> Tuple[MemoryJob, bool]:
        with self._lock:
            idemp_k = idempotency_key(job_type, idempotency_fields)
            if idemp_k in self._by_idemp:
                existing_id = self._by_idemp[idemp_k]
                existing_job = self._jobs.get(existing_id)
                if existing_job:
                    return copy.deepcopy(existing_job), False

            job_id = f"job_{uuid.uuid4().hex[:12]}"
            now = time.time()
            job = MemoryJob(
                job_id=job_id,
                job_type=job_type,
                user_id=user_id,
                status=JobStatus.QUEUED,
                payload=copy.deepcopy(payload),
                idempotency_key=idemp_k,
                max_attempts=max_attempts,
                timeout_seconds=timeout_seconds,
                created_at=now,
                updated_at=now,
            )
            self._jobs[job_id] = job
            self._by_idemp[idemp_k] = job_id
            return copy.deepcopy(job), True

    def get(self, job_id: str) -> Optional[MemoryJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            return copy.deepcopy(job) if job else None

    def claim_for_run(self, job_id: str) -> Tuple[Optional[MemoryJob], bool]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.QUEUED:
                return None, False

            now = time.time()
            job.status = JobStatus.RUNNING
            job.started_at = now
            job.updated_at = now
            job.error = ""
            job.error_state = None
            job.retry_count += 1
            return copy.deepcopy(job), True

    def mark_succeeded(self, job_id: str, result: Any) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            now = time.time()
            job.status = JobStatus.SUCCEEDED
            job.result = result
            job.error = ""
            job.error_state = None
            job.completed_at = now
            job.updated_at = now
            return True

    def mark_failed(self, job_id: str, error_message: str) -> JobStatus:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return JobStatus.FAILED
            now = time.time()
            if job.retry_count >= job.max_attempts:
                job.status = JobStatus.DEAD_LETTER
            else:
                job.status = JobStatus.FAILED

            job.error = error_message
            job.error_state = {
                "message": error_message,
                "failed_at": now,
                "attempt": job.retry_count,
            }
            job.updated_at = now
            job.completed_at = now
            return job.status

    def schedule_job(
        self,
        job: MemoryJob,
        worker_fn: Callable[[], Coroutine[Any, Any, Any]],
    ) -> asyncio.Task:
        """Execute a background worker asynchronously with job state tracking."""
        async def _runner():
            claimed_job, claimed = self.claim_for_run(job.job_id)
            if not claimed:
                return
            try:
                result = await asyncio.wait_for(worker_fn(), timeout=job.timeout_seconds)
                self.mark_succeeded(job.job_id, result)
            except asyncio.TimeoutError:
                self.mark_failed(job.job_id, f"Job timed out after {job.timeout_seconds}s")
            except Exception as e:
                logger.error(f"[JobRunner Error] Job {job.job_id} failed: {e}", exc_info=True)
                self.mark_failed(job.job_id, str(e))

        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(_runner())
        except RuntimeError:
            return asyncio.create_task(_runner())


memory_job_store = MemoryJobStore()
