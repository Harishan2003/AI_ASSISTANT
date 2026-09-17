# Module: backend.app.api.v1.memory
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.memory.conversation_memory import memory_job_store
from app.memory.long_term_memory import long_term_memory
from app.memory.memory_manager import friday_memory_manager

router = APIRouter(
    prefix="/memory",
    tags=["Memory"],
)


# --- REQUEST & RESPONSE SCHEMAS ---
class IngestRequest(BaseModel):
    user_query: str
    agent_response: Optional[str] = ""
    user_id: Optional[str] = "default"
    session_id: Optional[str] = "default"
    effort_level: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BatchIngestRequest(BaseModel):
    items: List[IngestRequest]
    user_id: Optional[str] = "default"


class RetrieveRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default"
    top_k: Optional[int] = 5
    min_score: Optional[float] = 0.35


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    filters: Optional[Dict[str, Any]] = None


class RememberFactRequest(BaseModel):
    fact: str
    category: Optional[str] = "general"
    user_id: Optional[str] = "default"
    metadata: Optional[Dict[str, Any]] = None


# --- ENDPOINTS ---
@router.post("/ingest", status_code=202, summary="Start an asynchronous durable memory ingest job")
async def ingest_memory_endpoint(req: IngestRequest):
    t0 = time.perf_counter()
    job, created = await friday_memory_manager.ingest_turn_async(
        user_query=req.user_query,
        agent_response=req.agent_response or "",
        user_id=req.user_id or "default",
        session_id=req.session_id or "default",
        metadata=req.metadata,
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "status": "accepted",
        "job_id": job.job_id,
        "job_status": job.status.value,
        "created": created,
        "status_url": f"/api/v1/memory/jobs/{job.job_id}/status",
        "elapsed_ms": elapsed_ms,
    }


@router.post("/batch-ingest", status_code=202, summary="Start a batch async memory ingest job")
async def batch_ingest_endpoint(req: BatchIngestRequest):
    t0 = time.perf_counter()
    if not req.items or len(req.items) > 200:
        raise HTTPException(status_code=422, detail="items list must contain between 1 and 200 entries")

    serialized_items = [item.model_dump() for item in req.items]
    job, created = await friday_memory_manager.batch_ingest_async(
        items=serialized_items,
        user_id=req.user_id or "default",
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "status": "accepted",
        "job_id": job.job_id,
        "job_status": job.status.value,
        "created": created,
        "count": len(req.items),
        "status_url": f"/api/v1/memory/jobs/{job.job_id}/status",
        "elapsed_ms": elapsed_ms,
    }


@router.get("/jobs/{job_id}/status", summary="Poll the status of an asynchronous memory job")
@router.get("/ingest/{job_id}/status", summary="Poll the status of an ingest job")
async def job_status_endpoint(job_id: str):
    job = memory_job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Memory job '{job_id}' not found.")
    return {"status": "success", "job": job.to_public_dict()}


@router.post("/retrieve", summary="Retrieve relevant memory context for a query")
async def retrieve_memory_endpoint(req: RetrieveRequest):
    t0 = time.perf_counter()
    context = await friday_memory_manager.fetch_memory_context(
        query=req.query,
        user_id=req.user_id or "default",
        top_k=req.top_k or 5,
        min_score=req.min_score or 0.35,
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "status": "success",
        "data": context,
        "elapsed_ms": elapsed_ms,
    }


@router.post("/search", summary="Vector and metadata search across memory records")
async def search_memory_endpoint(req: SearchRequest):
    t0 = time.perf_counter()
    results = friday_memory_manager.search_memory(
        query=req.query,
        top_k=req.top_k or 5,
        filters=req.filters,
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "status": "success",
        "count": len(results),
        "results": [r.to_dict() for r in results],
        "elapsed_ms": elapsed_ms,
    }


@router.post("/facts", summary="Store an explicit long-term fact")
async def remember_fact_endpoint(req: RememberFactRequest):
    fact_id = long_term_memory.remember_fact(
        fact=req.fact,
        category=req.category or "general",
        user_id=req.user_id or "default",
        metadata=req.metadata,
    )
    return {"status": "success", "fact_id": fact_id, "message": "Fact stored in long-term memory."}


@router.get("/facts", summary="List stored long-term facts")
async def list_facts_endpoint(user_id: str = "default", category: Optional[str] = None):
    facts = long_term_memory.list_facts(user_id=user_id, category=category)
    return {"status": "success", "count": len(facts), "facts": facts}


@router.delete("/facts/{fact_id}", summary="Delete a specific long-term fact")
async def delete_fact_endpoint(fact_id: str):
    success = long_term_memory.forget_fact(fact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Fact not found.")
    return {"status": "success", "message": "Fact forgotten successfully."}


@router.delete("/clear", summary="Clear memory records")
async def clear_memory_endpoint(user_id: Optional[str] = None):
    res = friday_memory_manager.clear_all_memory(user_id=user_id)
    return {"status": "success", "details": res}
