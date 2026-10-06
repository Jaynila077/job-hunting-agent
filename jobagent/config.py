import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    private_dir: Path
    db_path: Path
    log_level: str
    resume_path: Path
    llm_model: str
    embed_model: str
    profile_dir: Path
    model_cache_dir: Path
    groq_api_key: str | None = field(default=None, repr=False)


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
        # Real non-empty environment variables win over .env file values
        if key in os.environ and os.environ[key] is not None and os.environ[key].strip() != "":
            return os.environ[key].strip()
        if (
            key in file_vals
            and file_vals[key] is not None
            and str(file_vals[key]).strip() != ""
        ):
            return str(file_vals[key]).strip()
        return default

    def get_optional_secret(key: str) -> str | None:
        if key in os.environ and os.environ[key] is not None and os.environ[key].strip() != "":
            return os.environ[key].strip()
        if (
            key in file_vals
            and file_vals[key] is not None
            and str(file_vals[key]).strip() != ""
        ):
            return str(file_vals[key]).strip()
        return None

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

    resume_file_name = get_val("JOBAGENT_RESUME_FILE", "resume.pdf")
    resume_file_path = Path(resume_file_name)
    if not resume_file_path.is_absolute():
        resume_path = (private_dir_path / resume_file_path).resolve()
    else:
        resume_path = resume_file_path.resolve()

    llm_model = get_val("JOBAGENT_LLM_MODEL", "openai/gpt-oss-20b")
    embed_model = get_val("JOBAGENT_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    groq_api_key = get_optional_secret("GROQ_API_KEY")

    profile_dir = (private_dir_path / "profile").resolve()
    model_cache_dir = (private_dir_path / "models").resolve()

    return Settings(
        repo_root=repo_root,
        private_dir=private_dir_path,
        db_path=db_path,
        log_level=log_level,
        resume_path=resume_path,
        llm_model=llm_model,
        embed_model=embed_model,
        profile_dir=profile_dir,
        model_cache_dir=model_cache_dir,
        groq_api_key=groq_api_key,
    )