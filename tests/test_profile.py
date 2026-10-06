import json
from pathlib import Path

import pytest

import jobagent.profile as profile_module
from jobagent.profile import (
    EducationItem,
    Profile,
    ProfileEnvelope,
    ProjectItem,
    SkillItem,
    build_profile,
    format_profile_inspect,
    get_latest_profile_envelope,
    redact_contact_details,
    validate_profile,
)


def test_redact_contact_preserves_years_and_dates():
    sample = (
        "Bachelor of Engineering (2021-2025)\n"
        "Batch 2025-2026 Honors\n"
        "Dec 2023 - Feb 2024\n"
        "Phone: +91 96079 98192\n"
        "Email: test@example.com\n"
        "GitHub: github.com/testuser\n"
    )
    redacted = redact_contact_details(sample)
    assert "2021-2025" in redacted
    assert "2025-2026" in redacted
    assert "Dec 2023 - Feb 2024" in redacted
    assert "+91 96079 98192" not in redacted
    assert "test@example.com" not in redacted
    assert "github.com/testuser" not in redacted


def test_validate_profile_evidence_and_leaks():
    resume_text = "B.E. at Pune University from 2021-2025. Built ML pipelines."
    valid_profile = Profile(
        experience_level="Entry-Level",
        summary="AI engineer",
        education=[
            EducationItem(
                institution="Pune University",
                degree="B.E.",
                period="2021-2025",
                evidence=["Pune University from 2021-2025"],
            )
        ],
        projects=[
            ProjectItem(
                name="ML",
                summary="Pipelines",
                technologies=["Python"],
                evidence=["Built ML pipelines."],
            )
        ],
        skills=[SkillItem(name="Python", evidence=["ML pipelines"])],
    )
    errors, warnings, sanitized = validate_profile(valid_profile, resume_text)
    assert not errors
    assert len(sanitized.education) == 1

    # Test contact detail leakage into profile
    leaky_profile = valid_profile.model_copy(update={"summary": "Contact me at dev@domain.com"})
    errors, _, _ = validate_profile(leaky_profile, resume_text)
    assert any("email pattern matched" in e for e in errors)


def test_build_profile_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_text("Unique resume content " * 10, encoding="utf-8")

    profile_dir = tmp_path / "profile"
    model_cache = tmp_path / "models"

    monkeypatch.setattr(
        profile_module,
        "extract_text_from_pdf",
        lambda _: "B.E. at SPPU 2021-2025. Built Agent.",
    )

    valid_json = json.dumps(
        {
            "experience_level": "Fresher",
            "summary": "AI enthusiast",
            "education": [
                {
                    "institution": "SPPU",
                    "degree": "B.E.",
                    "evidence": ["B.E. at SPPU 2021-2025"],
                }
            ],
            "projects": [
                {
                    "name": "Agent",
                    "summary": "Autonomous",
                    "evidence": ["Built Agent."],
                }
            ],
            "skills": [{"name": "Python", "evidence": ["Built Agent."]}],
        }
    )

    def fake_llm(_sys: str, _usr: str) -> str:
        return valid_json

    def fake_embedder(texts: list[str], _m: str, _c: Path | None) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    # 1. Initial build: creates v1
    v1, path1, _, is_new = build_profile(
        pdf_path=pdf_file,
        profile_dir=profile_dir,
        model_cache_dir=model_cache,
        llm_caller=fake_llm,
        embedder=fake_embedder,
        llm_model="modelA",
        embed_model="modelB",
    )
    assert v1 == 1
    assert is_new is True
    assert path1.name == "profile-v0001.json"

    # 2. Idempotence: unchanged returns v1, is_new=False
    v_same, _, _, is_new_2 = build_profile(
        pdf_path=pdf_file,
        profile_dir=profile_dir,
        model_cache_dir=model_cache,
        llm_caller=fake_llm,
        embedder=fake_embedder,
        llm_model="modelA",
        embed_model="modelB",
        force=False,
    )
    assert v_same == 1
    assert is_new_2 is False

    # 3. Force rebuild: creates v2
    v2, path2, _, is_new_3 = build_profile(
        pdf_path=pdf_file,
        profile_dir=profile_dir,
        model_cache_dir=model_cache,
        llm_caller=fake_llm,
        embedder=fake_embedder,
        llm_model="modelA",
        embed_model="modelB",
        force=True,
    )
    assert v2 == 2
    assert is_new_3 is True
    assert path2.name == "profile-v0002.json"


def test_build_profile_retry_and_failure_leaves_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_text("Dummy content " * 10, encoding="utf-8")
    profile_dir = tmp_path / "profile"
    model_cache = tmp_path / "models"

    monkeypatch.setattr(profile_module, "extract_text_from_pdf", lambda _: "Sample text")

    call_count = 0

    def failing_llm(_sys: str, _usr: str) -> str:
        nonlocal call_count
        call_count += 1
        return "Not JSON"

    with pytest.raises(ValueError, match="failed after retry"):
        build_profile(
            pdf_path=pdf_file,
            profile_dir=profile_dir,
            model_cache_dir=model_cache,
            llm_caller=failing_llm,
            embedder=lambda t, m, c: [],
            llm_model="modelA",
            embed_model="modelB",
        )

    assert call_count == 2
    assert not profile_dir.exists() or len(list(profile_dir.glob("*.json"))) == 0


def test_corrupt_profile_file_handling(tmp_path: Path):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir(parents=True)
    corrupt_file = profile_dir / "profile-v0001.json"
    corrupt_file.write_text("{ corrupt json ", encoding="utf-8")

    with pytest.raises(ValueError, match="Corrupt profile file"):
        get_latest_profile_envelope(profile_dir)


def test_format_profile_inspect_vectors_not_printed(tmp_path: Path):
    envelope = ProfileEnvelope(
        schema_version=1,
        profile_version=1,
        created_at="2026-01-01T00:00:00Z",
        resume_sha256="dummy_sha",
        llm_model="test-llm",
        embed_model="test-embed",
        profile=Profile(
            experience_level="Fresher",
            summary="Summary text",
            education=[
                EducationItem(
                    institution="Univ",
                    degree="Degree",
                    evidence=["Evidence snippet"],
                )
            ],
            skills=[SkillItem(name="Python", evidence=["Evidence snippet"])],
        ),
        embeddings=[profile_module.EmbeddingItem(label="summary", vector=[0.123456, 0.654321])],
    )

    formatted = format_profile_inspect(envelope)
    assert "Profile Version: v0001" in formatted
    assert "0.123456" not in formatted
    assert "Dimension:  2" in formatted