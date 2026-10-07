import sqlite3
from collections.abc import Callable
from pathlib import Path


def step_1_create_jobs_table(conn: sqlite3.Connection) -> None:
    """Schema step 1: creates the jobs table and associated index."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT,
            posting_date TEXT,
            raw_text TEXT NOT NULL,
            title TEXT,
            company TEXT,
            summary TEXT,
            location_text TEXT,
            cities_json TEXT,
            work_mode TEXT,
            remote_scope TEXT,
            experience_text TEXT,
            experience_min_years REAL,
            experience_max_years REAL,
            pay_text TEXT,
            pay_status TEXT,
            skills_json TEXT,
            flags_json TEXT,
            outcome TEXT NOT NULL,
            outcome_reason TEXT,
            score INTEGER,
            verdict TEXT,
            matches_json TEXT,
            gaps_json TEXT,
            explanation TEXT,
            profile_version INTEGER,
            llm_model TEXT
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at);"
    )


# Schema migration steps. Step 1 adds the jobs table.
SCHEMA_STEPS: list[Callable[[sqlite3.Connection], None]] = [
    step_1_create_jobs_table,
]


def connect(db_path: Path, timeout_seconds: float = 30.0) -> sqlite3.Connection:
    """Connects to SQLite database at db_path, creating parent folders on demand."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=timeout_seconds)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute(f"PRAGMA busy_timeout = {int(timeout_seconds * 1000)};")
    return conn


def get_user_version(conn: sqlite3.Connection) -> int:
    cursor = conn.execute("PRAGMA user_version;")
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def set_user_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {version};")


def init_db(
    conn: sqlite3.Connection,
    steps: list[Callable[[sqlite3.Connection], None]] | None = None,
) -> int:
    """Applies pending schema steps in atomic transactions and updates PRAGMA user_version.

    Returns the resulting user_version.
    """
    if steps is None:
        steps = SCHEMA_STEPS

    current_version = get_user_version(conn)
    total_steps = len(steps)

    if current_version < total_steps:
        for idx in range(current_version, total_steps):
            step_fn = steps[idx]
            conn.execute("BEGIN IMMEDIATE;")
            try:
                step_fn(conn)
                set_user_version(conn, idx + 1)
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
        current_version = get_user_version(conn)

    return current_version