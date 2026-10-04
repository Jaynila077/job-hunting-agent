from pathlib import Path

import pytest

from jobagent.config import load_settings


def test_default_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JOBAGENT_PRIVATE_DIR", raising=False)
    monkeypatch.delenv("JOBAGENT_DB_FILE", raising=False)
    monkeypatch.delenv("JOBAGENT_LOG_LEVEL", raising=False)

    fake_env = tmp_path / ".env.nonexistent"
    settings = load_settings(env_file=fake_env)

    assert settings.log_level == "INFO"
    assert settings.private_dir == settings.repo_root / "private"
    assert settings.db_path == settings.repo_root / "private" / "jobagent.db"


def test_env_file_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JOBAGENT_PRIVATE_DIR", raising=False)
    monkeypatch.delenv("JOBAGENT_DB_FILE", raising=False)
    monkeypatch.delenv("JOBAGENT_LOG_LEVEL", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "JOBAGENT_PRIVATE_DIR=custom_private\n"
        "JOBAGENT_DB_FILE=custom.db\n"
        "JOBAGENT_LOG_LEVEL=DEBUG\n"
        "GROQ_API_KEY=dummy_key_to_ignore\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file=env_file)
    assert settings.log_level == "DEBUG"
    assert settings.private_dir == settings.repo_root / "custom_private"
    assert settings.db_path == settings.repo_root / "custom_private" / "custom.db"


def test_environment_variable_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env"
    env_file.write_text("JOBAGENT_LOG_LEVEL=DEBUG\n", encoding="utf-8")

    monkeypatch.setenv("JOBAGENT_LOG_LEVEL", "WARNING")
    settings = load_settings(env_file=env_file)
    assert settings.log_level == "WARNING"


def test_invalid_log_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JOBAGENT_LOG_LEVEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("JOBAGENT_LOG_LEVEL=INVALID_LEVEL\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JOBAGENT_LOG_LEVEL"):
        load_settings(env_file=env_file)