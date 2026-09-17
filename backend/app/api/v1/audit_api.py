"""
Audit Trail and Security Logs REST Endpoints.
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional

from app.database.agent_db import agent_db

router = APIRouter(prefix="/audit", tags=["Security & Audit"])


@router.get("")
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=500, description="Max log items to fetch"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    tool_name: Optional[str] = Query(default=None, description="Filter by tool name"),
    success: Optional[bool] = Query(default=None, description="Filter by execution success status")
) -> Dict[str, Any]:
    """Retrieves redacted audit log records for all agent tool executions."""
    logs = agent_db.get_audit_logs(
        limit=limit,
        offset=offset,
        tool_name=tool_name,
        success=success
    )
    return {
        "total_returned": len(logs),
        "limit": limit,
        "offset": offset,
        "logs": logs
    }
