import sqlite3
from pathlib import Path

from jobagent.db import connect, get_user_version, init_db, step_1_create_jobs_table


def test_connect_pragmas_and_directory_creation(tmp_path: Path):
    db_path = tmp_path / "nested" / "test.db"
    assert not db_path.parent.exists()

    conn = connect(db_path)
    try:
        assert db_path.exists()

        # Check foreign keys
        cursor = conn.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1

        # Check journal mode (WAL)
        cursor = conn.execute("PRAGMA journal_mode;")
        assert cursor.fetchone()[0].lower() == "wal"

        # Check busy timeout
        cursor = conn.execute("PRAGMA busy_timeout;")
        assert cursor.fetchone()[0] == 30000
    finally:
        conn.close()


def test_init_db_empty_steps(tmp_path: Path):
    db_path = tmp_path / "test_empty.db"
    conn = connect(db_path)
    try:
        version = init_db(conn, steps=[])
        assert version == 0
        assert get_user_version(conn) == 0
    finally:
        conn.close()


def test_init_db_applies_steps_idempotently(tmp_path: Path):
    db_path = tmp_path / "test_steps.db"
    conn = connect(db_path)

    step1_called = 0
    step2_called = 0

    def step1(c: sqlite3.Connection):
        nonlocal step1_called
        step1_called += 1
        c.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY);")

    def step2(c: sqlite3.Connection):
        nonlocal step2_called
        step2_called += 1
        c.execute("ALTER TABLE test_table ADD COLUMN name TEXT;")

    test_steps = [step1, step2]

    try:
        version = init_db(conn, steps=test_steps)
        assert version == 2
        assert get_user_version(conn) == 2
        assert step1_called == 1
        assert step2_called == 1

        conn.execute("INSERT INTO test_table (name) VALUES ('test');")

        version_second = init_db(conn, steps=test_steps)
        assert version_second == 2
        assert step1_called == 1
        assert step2_called == 1
    finally:
        conn.close()


def test_schema_step_1_and_step_2_migrations(tmp_path: Path):
    db_path = tmp_path / "test_live_schema.db"
    conn = connect(db_path)
    try:
        # 1. Run only step 1
        version1 = init_db(conn, steps=[step_1_create_jobs_table])
        assert version1 == 1
        assert get_user_version(conn) == 1

        # Insert a job under step 1 schema
        conn.execute(
            """
            INSERT INTO jobs (created_at, source, raw_text, outcome)
            VALUES ('2026-10-06T12:00:00', 'pasted', 'raw text sample', 'scored');
            """
        )
        conn.commit()

        # 2. Run full schema steps (applies step 2)
        version2 = init_db(conn)
        assert version2 == 2
        assert get_user_version(conn) == 2

        # Verify backfill of status='new' and dedup_key=NULL
        cursor = conn.execute("SELECT status, dedup_key FROM jobs WHERE id = 1;")
        row = cursor.fetchone()
        assert row[0] == "new"
        assert row[1] is None

        # Verify idempotence
        assert init_db(conn) == 2
    finally:
        conn.close()