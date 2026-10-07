import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from jobagent.db import connect, init_db
from jobagent.decisions import (
    get_jobs_by_status,
    get_status_counts,
    set_job_status,
)


@pytest.fixture
def test_db(tmp_path: Path) -> sqlite3.Connection:
    db_file = tmp_path / "test_decisions.db"
    conn = connect(db_file)
    init_db(conn)
    return conn


def _insert_test_job(conn: sqlite3.Connection, title: str, score: int | None = None) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO jobs (
            created_at, source, raw_text, title, score, outcome, status
        ) VALUES (
            '2026-10-07T12:00:00Z', 'pasted', 'raw text sample 12345', ?, ?, 'scored', 'new'
        );
        """,
        (title, score),
    )
    conn.commit()
    return int(cursor.lastrowid)


def test_set_job_status_success(test_db: sqlite3.Connection):
    job_id = _insert_test_job(test_db, "Engineer")
    fixed_time = datetime(2026, 10, 7, 14, 30, tzinfo=timezone.utc)

    set_job_status(
        test_db,
        job_id,
        "saved",
        reason="Good company",
        clock=lambda: fixed_time,
    )

    jobs = get_jobs_by_status(test_db, "saved")
    assert len(jobs) == 1
    assert jobs[0]["id"] == job_id
    assert jobs[0]["status"] == "saved"
    assert jobs[0]["decision_reason"] == "Good company"
    assert jobs[0]["decided_at"] == fixed_time.isoformat()


def test_set_job_status_validation(test_db: sqlite3.Connection):
    job_id = _insert_test_job(test_db, "Engineer")

    with pytest.raises(ValueError, match="Invalid status"):
        set_job_status(test_db, job_id, "invalid_status")

    with pytest.raises(ValueError, match="Job ID 999 not found"):
        set_job_status(test_db, 999, "rejected")


def test_get_jobs_by_status_ordering(test_db: sqlite3.Connection):
    j1 = _insert_test_job(test_db, "Job Low", score=5)
    j2 = _insert_test_job(test_db, "Job High", score=9)
    j3 = _insert_test_job(test_db, "Job No Score", score=None)

    jobs = get_jobs_by_status(test_db, "new")
    assert len(jobs) == 3
    # Ordered by (score IS NULL), score DESC, id DESC
    assert jobs[0]["id"] == j2
    assert jobs[1]["id"] == j1
    assert jobs[2]["id"] == j3


def test_get_status_counts(test_db: sqlite3.Connection):
    j1 = _insert_test_job(test_db, "Job 1")
    j2 = _insert_test_job(test_db, "Job 2")
    _insert_test_job(test_db, "Job 3")

    set_job_status(test_db, j1, "saved")
    set_job_status(test_db, j2, "applied")

    counts = get_status_counts(test_db)
    assert counts["saved"] == 1
    assert counts["applied"] == 1
    assert counts["new"] == 1
    assert counts["rejected"] == 0
    assert counts["interviewing"] == 0