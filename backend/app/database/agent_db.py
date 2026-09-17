"""
SQLite Database manager for Friday PC Agent (Audit Logs, Confirmations, Scheduler, Facts).
"""
from __future__ import annotations

import datetime
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentDatabase:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            base_dir = Path("database")
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "friday_agent.db"
        else:
            self.db_path = db_path
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Audit Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                user_request TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL,
                permission_level TEXT NOT NULL,
                status TEXT NOT NULL,
                result_summary TEXT,
                error TEXT,
                execution_time_ms REAL NOT NULL
            )
            """)

            # 2. Pending Confirmations
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_confirmations (
                token TEXT PRIMARY KEY,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING'
            )
            """)

            # 3. Scheduled Tasks
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                command TEXT NOT NULL,
                task_type TEXT NOT NULL,
                interval_seconds INTEGER,
                run_at TEXT,
                last_run TEXT,
                next_run TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL
            )
            """)

            # 4. User Facts
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                key TEXT PRIMARY KEY,
                fact TEXT,
                value TEXT,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            # Migrate user_facts schema if needed
            cursor.execute("PRAGMA table_info(user_facts)")
            cols = [col[1] for col in cursor.fetchall()]
            if "fact" not in cols:
                cursor.execute("ALTER TABLE user_facts ADD COLUMN fact TEXT")
                cursor.execute("UPDATE user_facts SET fact = value WHERE fact IS NULL")
            if "value" not in cols:
                cursor.execute("ALTER TABLE user_facts ADD COLUMN value TEXT")

            conn.commit()

    # ============================================================
    # AUDIT LOG METHODS
    # ============================================================
    def add_audit_log(
        self,
        session_id: str = "default",
        user_request: str = "",
        tool_name: str = "",
        arguments: Optional[Dict[str, Any]] = None,
        permission_level: str = "SAFE",
        status: str = "SUCCESS",
        result_summary: Optional[str] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
        timestamp: Optional[str] = None,
    ) -> int:
        ts = timestamp or datetime.datetime.now().isoformat()
        args_payload = json.dumps(arguments or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_logs (
                timestamp, session_id, user_request, tool_name, arguments,
                permission_level, status, result_summary, error, execution_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts, session_id, user_request, tool_name,
                args_payload, permission_level, status,
                result_summary, error, execution_time_ms
            ))
            conn.commit()
            return cursor.lastrowid or 0

    def insert_audit_log(self, *args, **kwargs) -> int:
        return self.add_audit_log(*args, **kwargs)

    def get_audit_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        tool_name: Optional[str] = None,
        success: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params: List[Any] = []

            if tool_name:
                query += " AND tool_name = ?"
                params.append(tool_name)
            if success is not None:
                query += " AND status = ?"
                params.append("SUCCESS" if success else "FAILED")

            query += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["arguments"] = json.loads(item["arguments"])
                except Exception:
                    pass
                results.append(item)
            return results

    # ============================================================
    # CONFIRMATION METHODS
    # ============================================================
    def save_pending_confirmation(
        self,
        token: str,
        tool_name: str,
        arguments: Dict[str, Any],
        description: str,
        created_at: str,
        expires_at: float,
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO pending_confirmations (
                token, tool_name, arguments, description, created_at, expires_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            """, (
                token, tool_name, json.dumps(arguments), description, created_at, expires_at
            ))
            conn.commit()

    def get_pending_confirmation(self, token: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pending_confirmations WHERE token = ?", (token,))
            row = cursor.fetchone()
            if row:
                item = dict(row)
                try:
                    item["arguments"] = json.loads(item["arguments"])
                except Exception:
                    pass
                return item
            return None

    def update_confirmation_status(self, token: str, status: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pending_confirmations SET status = ? WHERE token = ?",
                (status, token)
            )
            conn.commit()

    # ============================================================
    # SCHEDULED TASKS METHODS
    # ============================================================
    def add_scheduled_task(
        self,
        task_id: str,
        name: str,
        action: str,
        schedule_time: Optional[str] = None,
        cron: Optional[str] = None,
        task_type: str = "ONE_TIME"
    ) -> bool:
        try:
            now = datetime.datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO scheduled_tasks (
                    id, name, command, task_type, run_at, next_run, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'SCHEDULED', ?)
                """, (
                    task_id, name, action, "CRON" if cron else task_type, schedule_time, schedule_time, now
                ))
                conn.commit()
                return True
        except Exception:
            return False

    def list_scheduled_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT id, name, command as action, run_at as schedule_time, status, created_at FROM scheduled_tasks WHERE status = ? ORDER BY created_at DESC", (status,))
            else:
                cursor.execute("SELECT id, name, command as action, run_at as schedule_time, status, created_at FROM scheduled_tasks ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def update_scheduled_task_status(self, task_id: str, status: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE scheduled_tasks SET status = ? WHERE id = ?", (status, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_scheduled_task(self, task_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ============================================================
    # USER FACTS / MEMORY METHODS
    # ============================================================
    def save_fact(self, fact: str, category: str = "general", key: Optional[str] = None) -> bool:
        try:
            now = datetime.datetime.now().isoformat()
            k = key or f"fact_{uuid.uuid4().hex[:8]}"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO user_facts (key, fact, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (k, fact, fact, category, now, now))
                conn.commit()
                return True
        except Exception:
            return False

    def get_facts(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                sql = "SELECT key, COALESCE(fact, value) as fact, category, created_at, updated_at FROM user_facts WHERE 1=1"
                params: List[Any] = []
                if category:
                    sql += " AND category = ?"
                    params.append(category)
                if query:
                    sql += " AND (fact LIKE ? OR value LIKE ?)"
                    params.extend([f"%{query}%", f"%{query}%"])
                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(sql, params)
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []


agent_db = AgentDatabase()
