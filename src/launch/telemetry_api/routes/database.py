"""SQLite database layer for telemetry API run persistence.

Binding contract: specs/16_local_telemetry_api.md (Local Telemetry API)
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from datetime import datetime, timezone


class TelemetryDatabase:
    """SQLite database for telemetry run persistence."""

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    parent_run_id TEXT,
                    product TEXT,
                    product_family TEXT,
                    platform TEXT,
                    subdomain TEXT,
                    website_section TEXT,
                    item_name TEXT,
                    git_repo TEXT,
                    git_branch TEXT,
                    end_time TEXT,
                    duration_ms INTEGER,
                    items_discovered INTEGER,
                    items_succeeded INTEGER,
                    items_failed INTEGER,
                    items_skipped INTEGER,
                    output_summary TEXT,
                    error_summary TEXT,
                    metrics_json TEXT,
                    context_json TEXT,
                    commit_hash TEXT,
                    commit_source TEXT,
                    commit_author TEXT,
                    commit_timestamp TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for efficient queries
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_parent_run_id ON runs(parent_run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_job_type ON runs(job_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_start_time ON runs(start_time)"
            )

            # Create events table for event streaming
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    trace_id TEXT,
                    span_id TEXT,
                    parent_span_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)"
            )

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new run record.

        Args:
            run_data: Run data dictionary

        Returns:
            Created run record

        Raises:
            sqlite3.IntegrityError: If event_id already exists (idempotency)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if event_id already exists (idempotency)
            cursor.execute(
                "SELECT * FROM runs WHERE event_id = ?",
                (run_data["event_id"],)
            )
            existing = cursor.fetchone()
            if existing:
                return self._row_to_dict(existing)

            # Serialize JSON fields
            metrics_json = None
            if run_data.get("metrics_json"):
                metrics_json = json.dumps(run_data["metrics_json"], sort_keys=True)

            context_json = None
            if run_data.get("context_json"):
                context_json = json.dumps(run_data["context_json"], sort_keys=True)

            # Insert new run
            cursor.execute("""
                INSERT INTO runs (
                    event_id, run_id, agent_name, job_type, start_time, status,
                    parent_run_id, product, product_family, platform, subdomain,
                    website_section, item_name, git_repo, git_branch,
                    metrics_json, context_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_data["event_id"],
                run_data["run_id"],
                run_data["agent_name"],
                run_data["job_type"],
                run_data["start_time"],
                run_data.get("status", "running"),
                run_data.get("parent_run_id"),
                run_data.get("product"),
                run_data.get("product_family"),
                run_data.get("platform"),
                run_data.get("subdomain"),
                run_data.get("website_section"),
                run_data.get("item_name"),
                run_data.get("git_repo"),
                run_data.get("git_branch"),
                metrics_json,
                context_json,
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ))

            conn.commit()

            # Return created run
            cursor.execute(
                "SELECT * FROM runs WHERE event_id = ?",
                (run_data["event_id"],)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def get_run_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run by run_id.

        Args:
            run_id: Run identifier

        Returns:
            Run record or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM runs WHERE run_id = ? ORDER BY created_at DESC LIMIT 1",
                (run_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def get_run_by_event_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get run by event_id.

        Args:
            event_id: Event identifier

        Returns:
            Run record or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM runs WHERE event_id = ?",
                (event_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def update_run(self, event_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update run record.

        Args:
            event_id: Event identifier
            update_data: Fields to update

        Returns:
            Updated run record or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if run exists
            cursor.execute(
                "SELECT * FROM runs WHERE event_id = ?",
                (event_id,)
            )
            if not cursor.fetchone():
                return None

            # Build update query dynamically
            update_fields = []
            update_values = []

            for field, value in update_data.items():
                if field in ["metrics_json", "context_json"]:
                    if value is not None:
                        update_fields.append(f"{field} = ?")
                        update_values.append(json.dumps(value, sort_keys=True))
                elif value is not None:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)

            if not update_fields:
                # No fields to update, return current record
                cursor.execute(
                    "SELECT * FROM runs WHERE event_id = ?",
                    (event_id,)
                )
                row = cursor.fetchone()
                return self._row_to_dict(row)

            # Add updated_at timestamp
            update_fields.append("updated_at = ?")
            update_values.append(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

            # Add event_id to values
            update_values.append(event_id)

            # Execute update
            query = f"UPDATE runs SET {', '.join(update_fields)} WHERE event_id = ?"
            cursor.execute(query, update_values)
            conn.commit()

            # Return updated run
            cursor.execute(
                "SELECT * FROM runs WHERE event_id = ?",
                (event_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def associate_commit(
        self,
        event_id: str,
        commit_hash: str,
        commit_source: str,
        commit_author: Optional[str] = None,
        commit_timestamp: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Associate commit with run.

        Args:
            event_id: Event identifier
            commit_hash: Git commit SHA
            commit_source: Commit source (manual, llm, ci)
            commit_author: Optional commit author
            commit_timestamp: Optional commit timestamp

        Returns:
            Updated run record or None if not found
        """
        update_data = {
            "commit_hash": commit_hash,
            "commit_source": commit_source,
        }
        if commit_author:
            update_data["commit_author"] = commit_author
        if commit_timestamp:
            update_data["commit_timestamp"] = commit_timestamp

        return self.update_run(event_id, update_data)

    def list_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        product: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """List runs with filtering and pagination.

        Args:
            limit: Max results to return
            offset: Number of results to skip
            status: Filter by status
            job_type: Filter by job_type
            parent_run_id: Filter by parent_run_id
            product: Filter by product

        Returns:
            Tuple of (runs list, total count)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            where_clauses = []
            params = []

            if status:
                where_clauses.append("status = ?")
                params.append(status)
            if job_type:
                where_clauses.append("job_type = ?")
                params.append(job_type)
            if parent_run_id:
                where_clauses.append("parent_run_id = ?")
                params.append(parent_run_id)
            if product:
                where_clauses.append("product = ?")
                params.append(product)

            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)

            # Get total count
            count_query = f"SELECT COUNT(*) FROM runs {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Get paginated results
            query = f"""
                SELECT * FROM runs
                {where_clause}
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()

            runs = [self._row_to_dict(row) for row in rows]
            return (runs, total)

    def add_event(self, event_data: Dict[str, Any]) -> None:
        """Add event to event log.

        Args:
            event_data: Event data dictionary
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            payload_json = json.dumps(event_data.get("payload", {}), sort_keys=True)

            cursor.execute("""
                INSERT INTO events (
                    event_id, run_id, ts, type, payload,
                    trace_id, span_id, parent_span_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_data["event_id"],
                event_data["run_id"],
                event_data["ts"],
                event_data["type"],
                payload_json,
                event_data.get("trace_id"),
                event_data.get("span_id"),
                event_data.get("parent_span_id"),
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ))

            conn.commit()

    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all events for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of event records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY ts ASC",
                (run_id,)
            )
            rows = cursor.fetchall()

            events = []
            for row in rows:
                event = dict(row)
                # Deserialize payload
                if event.get("payload"):
                    event["payload"] = json.loads(event["payload"])
                # Remove internal id
                event.pop("id", None)
                event.pop("created_at", None)
                events.append(event)

            return events

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary.

        Args:
            row: SQLite row

        Returns:
            Dictionary representation
        """
        result = dict(row)

        # Deserialize JSON fields
        if result.get("metrics_json"):
            result["metrics_json"] = json.loads(result["metrics_json"])
        if result.get("context_json"):
            result["context_json"] = json.loads(result["context_json"])

        return result
