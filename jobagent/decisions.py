import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

VALID_STATUSES: set[str] = {"new", "saved", "rejected", "applied", "interviewing"}


def set_job_status(
    conn: sqlite3.Connection,
    job_id: int,
    status: str,
    reason: str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> None:
    """Updates the decision status and reason for a specific job."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}.")

    now_dt = clock() if clock else datetime.now(timezone.utc)
    decided_at = now_dt.isoformat()

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE jobs
        SET status = ?, decision_reason = ?, decided_at = ?
        WHERE id = ?;
        """,
        (status, reason, decided_at, job_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        raise ValueError(f"Job ID {job_id} not found.")


def get_jobs_by_status(conn: sqlite3.Connection, status: str) -> list[dict[str, Any]]:
    """Fetches all jobs with the specified status, ordered by score descending."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}.")

    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    cursor.execute(
        """
        SELECT * FROM jobs
        WHERE status = ?
        ORDER BY (score IS NULL), score DESC, id DESC;
        """,
        (status,),
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Returns a count mapping of all job statuses."""
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status;")
    counts = {s: 0 for s in VALID_STATUSES}
    for row in cursor.fetchall():
        counts[row[0]] = int(row[1])
    return counts