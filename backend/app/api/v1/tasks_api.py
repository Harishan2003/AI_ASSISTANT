"""
Task Scheduler REST Endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.database.agent_db import agent_db
from app.tools.scheduler.scheduler_ops import CreateScheduledTaskTool, CancelScheduledTaskTool

router = APIRouter(prefix="/tasks", tags=["Task Scheduler"])

create_task_tool = CreateScheduledTaskTool()
cancel_task_tool = CancelScheduledTaskTool()


class CreateTaskRequest(BaseModel):
    name: str = Field(..., description="Task title")
    action: str = Field(..., description="Instruction or action to run")
    schedule_time: Optional[str] = Field(default=None, description="ISO datetime string")
    cron: Optional[str] = Field(default=None, description="Cron expression")


@router.get("")
def list_tasks(status: Optional[str] = Query(default=None, description="Filter: 'SCHEDULED', 'COMPLETED', 'CANCELLED'")) -> Dict[str, Any]:
    tasks = agent_db.list_scheduled_tasks(status=status)
    return {"total": len(tasks), "tasks": tasks}


@router.post("")
def create_task(req: CreateTaskRequest) -> Dict[str, Any]:
    res = create_task_tool.run(
        task_name=req.name,
        command_or_action=req.action,
        schedule_time_iso=req.schedule_time,
        cron_expression=req.cron
    )
    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)
    return res.data


@router.delete("/{task_id}")
def cancel_task(task_id: str) -> Dict[str, Any]:
    res = cancel_task_tool.run(task_id=task_id)
    if not res.success:
        raise HTTPException(status_code=404, detail=res.error)
    return res.data
