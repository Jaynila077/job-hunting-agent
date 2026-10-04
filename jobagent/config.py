import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    private_dir: Path
    db_path: Path
    log_level: str


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_settings(env_file: Path | None = None) -> Settings:
    repo_root = get_repo_root()

    if env_file is None:
        target_env = repo_root / ".env"
    else:
        target_env = env_file

    file_vals = dotenv_values(target_env) if target_env.is_file() else {}

    def get_val(key: str, default: str) -> str:
        # Real environment variables win over .env file values
        if key in os.environ and os.environ[key] is not None:
            return os.environ[key]
        if key in file_vals and file_vals[key] is not None:
            return str(file_vals[key])
        return default

    raw_private_dir = get_val("JOBAGENT_PRIVATE_DIR", "private")
    private_dir_path = Path(raw_private_dir)
    if not private_dir_path.is_absolute():
        private_dir_path = (repo_root / private_dir_path).resolve()

    db_file_name = get_val("JOBAGENT_DB_FILE", "jobagent.db")
    db_file_path = Path(db_file_name)
    if not db_file_path.is_absolute():
        db_path = (private_dir_path / db_file_path).resolve()
    else:
        db_path = db_file_path.resolve()

    log_level = get_val("JOBAGENT_LOG_LEVEL", "INFO").upper()
    if log_level not in VALID_LOG_LEVELS:
        raise ValueError(
            f"Invalid JOBAGENT_LOG_LEVEL: {log_level}. Must be one of {sorted(VALID_LOG_LEVELS)}"
        )

    return Settings(
        repo_root=repo_root,
        private_dir=private_dir_path,
        db_path=db_path,
        log_level=log_level,
    )