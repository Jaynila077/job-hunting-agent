from pathlib import Path

import pytest

from jobagent.config import load_settings


def test_default_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JOBAGENT_PRIVATE_DIR", raising=False)
    monkeypatch.delenv("JOBAGENT_DB_FILE", raising=False)
    monkeypatch.delenv("JOBAGENT_LOG_LEVEL", raising=False)
    monkeypatch.delenv("JOBAGENT_RESUME_FILE", raising=False)
    monkeypatch.delenv("JOBAGENT_LLM_MODEL", raising=False)
    monkeypatch.delenv("JOBAGENT_EMBED_MODEL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    fake_env = tmp_path / ".env.nonexistent"
    settings = load_settings(env_file=fake_env)

    assert settings.log_level == "INFO"
    assert settings.private_dir == settings.repo_root / "private"
    assert settings.db_path == settings.repo_root / "private" / "jobagent.db"
    assert settings.resume_path == settings.repo_root / "private" / "resume.pdf"
    assert settings.llm_model == "openai/gpt-oss-20b"
    assert settings.embed_model == "BAAI/bge-small-en-v1.5"
    assert settings.profile_dir == settings.repo_root / "private" / "profile"
    assert settings.model_cache_dir == settings.repo_root / "private" / "models"
    assert settings.groq_api_key is None


def test_env_file_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JOBAGENT_PRIVATE_DIR", raising=False)
    monkeypatch.delenv("JOBAGENT_DB_FILE", raising=False)
    monkeypatch.delenv("JOBAGENT_LOG_LEVEL", raising=False)
    monkeypatch.delenv("JOBAGENT_RESUME_FILE", raising=False)
    monkeypatch.delenv("JOBAGENT_LLM_MODEL", raising=False)
    monkeypatch.delenv("JOBAGENT_EMBED_MODEL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "JOBAGENT_PRIVATE_DIR=custom_private\n"
        "JOBAGENT_DB_FILE=custom.db\n"
        "JOBAGENT_LOG_LEVEL=DEBUG\n"
        "JOBAGENT_RESUME_FILE=my_resume.pdf\n"
        "JOBAGENT_LLM_MODEL=custom/model\n"
        "JOBAGENT_EMBED_MODEL=custom/embed\n"
        "GROQ_API_KEY=test_api_key\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file=env_file)
    assert settings.log_level == "DEBUG"
    assert settings.private_dir == settings.repo_root / "custom_private"
    assert settings.db_path == settings.repo_root / "custom_private" / "custom.db"
    assert settings.resume_path == settings.repo_root / "custom_private" / "my_resume.pdf"
    assert settings.llm_model == "custom/model"
    assert settings.embed_model == "custom/embed"
    assert settings.groq_api_key == "test_api_key"
    assert "test_api_key" not in repr(settings)


def test_environment_variable_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "JOBAGENT_LOG_LEVEL=DEBUG\nGROQ_API_KEY=file_key\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("JOBAGENT_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("GROQ_API_KEY", "env_key")
    settings = load_settings(env_file=env_file)
    assert settings.log_level == "WARNING"
    assert settings.groq_api_key == "env_key"


def test_invalid_log_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JOBAGENT_LOG_LEVEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("JOBAGENT_LOG_LEVEL=INVALID_LEVEL\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JOBAGENT_LOG_LEVEL"):
        load_settings(env_file=env_file)