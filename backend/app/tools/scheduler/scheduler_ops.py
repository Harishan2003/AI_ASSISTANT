"""
Task scheduling tools for Friday AI Assistant.
Manages one-time reminders, deferred actions, and recurring jobs stored in SQLite.
"""

import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.database.agent_db import agent_db


class CreateScheduledTaskInput(BaseModel):
    task_name: str = Field(..., description="Human-readable title or label for the scheduled task")
    command_or_action: str = Field(..., description="The prompt, instruction, or tool call to execute when scheduled time arrives")
    schedule_time_iso: Optional[str] = Field(default=None, description="ISO timestamp for one-time execution (e.g. '2026-09-16T18:00:00')")
    cron_expression: Optional[str] = Field(default=None, description="Optional cron expression for recurring tasks (e.g. '0 9 * * *')")


class CreateScheduledTaskTool(BaseTool):
    name: str = "create_scheduled_task"
    description: str = "Schedules a task, reminder, or automated instruction for future or recurring execution."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = CreateScheduledTaskInput

    def run(
        self,
        task_name: str,
        command_or_action: str,
        schedule_time_iso: Optional[str] = None,
        cron_expression: Optional[str] = None
    ) -> ToolResult:
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        if not schedule_time_iso and not cron_expression:
            # Default to 5 minutes from now if neither is specified
            run_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            schedule_time_iso = run_time.isoformat()

        success = agent_db.add_scheduled_task(
            task_id=task_id,
            name=task_name,
            action=command_or_action,
            schedule_time=schedule_time_iso,
            cron=cron_expression
        )

        if success:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "task_id": task_id,
                    "name": task_name,
                    "action": command_or_action,
                    "schedule_time": schedule_time_iso,
                    "cron": cron_expression,
                    "status": "SCHEDULED"
                }
            )
        else:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Failed to persist scheduled task in database",
                error_code="DB_SAVE_FAILED"
            )


class ListScheduledTasksInput(BaseModel):
    status: Optional[str] = Field(default=None, description="Filter tasks by status ('SCHEDULED', 'COMPLETED', 'CANCELLED')")


class ListScheduledTasksTool(BaseTool):
    name: str = "list_scheduled_tasks"
    description: str = "Retrieves all scheduled tasks and reminders."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = ListScheduledTasksInput

    def run(self, status: Optional[str] = None) -> ToolResult:
        tasks = agent_db.list_scheduled_tasks(status=status)
        return ToolResult(
            tool_name=self.name,
            success=True,
            data={"total_tasks": len(tasks), "tasks": tasks}
        )


class CancelScheduledTaskInput(BaseModel):
    task_id: str = Field(..., description="The unique ID of the scheduled task to cancel")


class CancelScheduledTaskTool(BaseTool):
    name: str = "cancel_scheduled_task"
    description: str = "Cancels an upcoming scheduled task or reminder."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = CancelScheduledTaskInput

    def run(self, task_id: str) -> ToolResult:
        success = agent_db.update_scheduled_task_status(task_id, "CANCELLED")
        if success:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"task_id": task_id, "status": "CANCELLED"}
            )
        else:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Task with ID '{task_id}' not found or could not be cancelled",
                error_code="TASK_NOT_FOUND"
            )
