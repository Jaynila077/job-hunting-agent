from pathlib import Path

from jobagent.profile import (
    EducationItem,
    Profile,
    ProjectItem,
    SkillItem,
    build_profile,
    format_profile_inspect,
    get_latest_profile_envelope,
    redact_contact_details,
    validate_profile,
)


def test_redact_contact_details():
    sample = (
        "Name: John Doe\n"
        "Email: john.doe@example.com\n"
        "Phone: +91 98765 43210\n"
        "Github: github.com/johndoe\n"
        "Website: https://johndoe.dev\n"
        "Skills: Python, FastAPI\n"
    )
    redacted = redact_contact_details(sample)
    assert "john.doe@example.com" not in redacted
    assert "98765" not in redacted
    assert "github.com/johndoe" not in redacted
    assert "https://johndoe.dev" not in redacted
    assert "[REDACTED]" in redacted
    assert "Python, FastAPI" in redacted


def test_validate_profile_evidence_matching():
    resume_text = "Master of Science in AI at Stanford University. Built full stack ML models with Python."
    profile = Profile(
        experience_level="Entry-Level",
        summary="AI engineer",
        education=[
            EducationItem(
                institution="Stanford University",
                degree="Master of Science",
                evidence=["Master of Science in AI at Stanford University."],
            )
        ],
        projects=[
            ProjectItem(
                name="ML Project",
                summary="Full stack ML",
                technologies=["Python"],
                evidence=["Built full stack ML models with Python."],
            )
        ],
        skills=[SkillItem(name="Python", evidence=["Python"])],
    )
    errors, warnings, sanitized = validate_profile(profile, resume_text)
    assert not errors
    assert len(sanitized.education) == 1
    assert len(sanitized.projects) == 1


def test_validate_profile_missing_evidence():
    resume_text = "Studied at Pune University."
    profile = Profile(
        experience_level="Entry-Level",
        summary="AI engineer",
        education=[
            EducationItem(
                institution="Oxford",
                degree="BSc",
                evidence=["Degree at Oxford University."],  # Not in text
            )
        ],
        skills=[SkillItem(name="Python", evidence=["Python"])],
    )
    errors, warnings, sanitized = validate_profile(profile, resume_text)
    assert any("has no valid evidence" in e for e in errors)


def test_build_profile_and_envelope(tmp_path: Path):
    pdf_file = tmp_path / "resume.pdf"
    # Create fake PDF-like text
    pdf_file.write_text("Hello World. " * 20, encoding="utf-8")

    profile_dir = tmp_path / "profile"
    model_cache = tmp_path / "models"

    fake_json_reply = """
    {
      "experience_level": "Fresher",
      "summary": "A motivated fresher.",
      "education": [{"institution": "Univ", "degree": "B.E.", "evidence": ["Hello World."]}],
      "projects": [{"name": "P1", "summary": "Project 1", "technologies": ["Python"], "evidence": ["Hello World."]}],
      "skills": [{"name": "Python", "evidence": ["Hello World."]}],
      "certifications": []
    }
    """

    def fake_llm(_sys: str, _usr: str) -> str:
        return fake_json_reply

    def fake_embedder(texts: list[str], _m: str, _c: Path | None) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    # Monkeypatch extract_text_from_pdf to return simple text
    import jobagent.profile
    orig_extract = jobagent.profile.extract_text_from_pdf
    jobagent.profile.extract_text_from_pdf = lambda p: "Hello World. " * 20

    try:
        ver, out_path, warnings = build_profile(
            pdf_path=pdf_file,
            profile_dir=profile_dir,
            model_cache_dir=model_cache,
            llm_caller=fake_llm,
            embedder=fake_embedder,
            llm_model="test-llm",
            embed_model="test-embed",
        )
        assert ver == 1
        assert out_path.is_file()

        envelope = get_latest_profile_envelope(profile_dir)
        assert envelope is not None
        assert envelope.profile_version == 1
        assert len(envelope.embeddings) > 0

        inspect_output = format_profile_inspect(envelope, pdf_file)
        assert "Profile Version: v0001" in inspect_output
        assert "Fresher" in inspect_output
    finally:
        jobagent.profile.extract_text_from_pdf = orig_extract