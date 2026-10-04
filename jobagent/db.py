import sqlite3
from collections.abc import Callable
from pathlib import Path

# Schema migration steps. M0 has 0 steps. Subsequent milestones append migration functions.
SCHEMA_STEPS: list[Callable[[sqlite3.Connection], None]] = []


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
    """Applies pending schema steps in order and updates PRAGMA user_version.

    Returns the resulting user_version.
    """
    if steps is None:
        steps = SCHEMA_STEPS

    current_version = get_user_version(conn)
    total_steps = len(steps)

    if current_version < total_steps:
        for idx in range(current_version, total_steps):
            step_fn = steps[idx]
            with conn:
                step_fn(conn)
                set_user_version(conn, idx + 1)
        current_version = get_user_version(conn)

    return current_version