import sqlite3
from pathlib import Path

from jobagent.db import connect, get_user_version, init_db


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


def test_schema_step_1_creates_jobs_table(tmp_path: Path):
    db_path = tmp_path / "test_live_schema.db"
    conn = connect(db_path)
    try:
        version = init_db(conn)
        assert version == 1
        assert get_user_version(conn) == 1

        # Verify table existence and column columns
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';")
        assert cursor.fetchone() is not None

        # Check idempotency
        version_again = init_db(conn)
        assert version_again == 1
    finally:
        conn.close()