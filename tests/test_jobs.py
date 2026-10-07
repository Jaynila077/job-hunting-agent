import json
import sqlite3
from pathlib import Path
import pytest

from jobagent.db import connect, init_db
from jobagent.jobs import (
    JobExtraction,
    JobScoreOutput,
    MatchItem,
    check_job_text_length,
    derive_verdict,
    evaluate_filter_rules,
    format_job_inspect,
    get_job_by_id,
    get_latest_job,
    process_job,
    verify_evidence_and_values,
)
from jobagent.profile import (
    EducationItem,
    Profile,
    ProfileEnvelope,
    ProjectItem,
    SkillItem,
)


@pytest.fixture
def sample_profile_envelope() -> ProfileEnvelope:
    return ProfileEnvelope(
        schema_version=1,
        profile_version=1,
        created_at="2026-10-06T12:00:00Z",
        resume_sha256="fake_sha",
        llm_model="test-llm",
        embed_model="test-embed",
        profile=Profile(
            experience_level="Fresher",
            summary="AI Engineer with NLP and Python background.",
            education=[
                EducationItem(
                    institution="Savitribai Phule Pune University",
                    degree="B.E. Electronics",
                    evidence=["Savitribai Phule Pune University"],
                )
            ],
            projects=[
                ProjectItem(
                    name="Disaster Management Dashboard",
                    summary="Full-stack forecasting dashboard.",
                    technologies=["FastAPI", "Python", "BiLSTM"],
                    evidence=["Disaster Management Dashboard"],
                )
            ],
            skills=[
                SkillItem(name="Python", evidence=["Python"]),
                SkillItem(name="FastAPI", evidence=["FastAPI"]),
            ],
        ),
        embeddings=[],
    )


@pytest.fixture
def memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def test_input_length_checks():
    with pytest.raises(ValueError, match="too short"):
        check_job_text_length("Short text")

    with pytest.raises(ValueError, match="exceeds maximum"):
        check_job_text_length("A" * 20001)

    # Valid range
    check_job_text_length("A" * 150)


def test_evidence_verification_rules():
    raw_text = (
        "We are hiring a Python Engineer in Pune. Minimum 2+ years of experience required. "
        "Salary is 10 LPA. Full-time role."
    )
    # Valid extraction matching text
    valid_ext = JobExtraction(
        title="Python Engineer",
        location_text="Pune",
        cities=["Pune"],
        experience_text="2+ years",
        experience_min_years=2.0,
        pay_text="10 LPA",
        pay_status="stated",
    )
    verified, flags = verify_evidence_and_values(valid_ext, raw_text)
    assert not flags
    assert verified.experience_min_years == 2.0
    assert verified.cities == ["Pune"]

    # Snippet mismatch / hallucinated snippet
    bad_snippet = valid_ext.model_copy(update={"location_text": "San Francisco"})
    verified_bad, flags_bad = verify_evidence_and_values(bad_snippet, raw_text)
    assert any("location snippet could not be verified" in f for f in flags_bad)
    assert verified_bad.cities == []

    # Value mismatch with snippet: snippet says 2+ years, model says 5 years
    bad_val = valid_ext.model_copy(update={"experience_min_years": 5.0})
    verified_val, flags_val = verify_evidence_and_values(bad_val, raw_text)
    assert any("experience minimum years not substantiated" in f for f in flags_val)
    assert verified_val.experience_min_years is None

    # Unpaid status without unpaid phrase
    fake_unpaid = valid_ext.model_copy(update={"pay_status": "unpaid", "pay_text": "10 LPA"})
    verified_unpaid, flags_unpaid = verify_evidence_and_values(fake_unpaid, raw_text)
    assert any("unpaid status not substantiated" in f for f in flags_unpaid)
    assert verified_unpaid.pay_status == "not_stated"


def test_filter_unpaid():
    job = JobExtraction(
        title="Intern",
        pay_text="Unpaid internship for college students",
        pay_status="unpaid",
    )
    excluded, reason, snip, flags = evaluate_filter_rules(job)
    assert excluded is True
    assert "unpaid" in reason.lower()
    assert snip == job.pay_text


def test_filter_locations():
    # Allowed canonical city
    j_pune = JobExtraction(title="Dev", cities=["Pune"], location_text="Pune, MH")
    ex, _, _, _ = evaluate_filter_rules(j_pune)
    assert ex is False

    # Allowed alias (Hinjewadi)
    j_alias = JobExtraction(title="Dev", cities=["Hinjewadi"], location_text="Hinjewadi")
    ex, _, _, _ = evaluate_filter_rules(j_alias)
    assert ex is False

    # Multi-city with one allowed (Delhi & Bangalore)
    j_multi = JobExtraction(title="Dev", cities=["Delhi", "Bangalore"], location_text="Both")
    ex, _, _, _ = evaluate_filter_rules(j_multi)
    assert ex is False

    # Disallowed city (Chennai)
    j_disallowed = JobExtraction(title="Dev", cities=["Chennai"], location_text="Chennai")
    ex, reason, _, _ = evaluate_filter_rules(j_disallowed)
    assert ex is True
    assert "Chennai" in reason

    # Remote India / Global
    j_remote_in = JobExtraction(title="Dev", work_mode="remote", remote_scope="india")
    ex, _, _, _ = evaluate_filter_rules(j_remote_in)
    assert ex is False

    # Remote US-only / other_region
    j_remote_us = JobExtraction(
        title="Dev",
        work_mode="remote",
        remote_scope="other_region",
        location_text="US Only",
    )
    ex, reason, _, _ = evaluate_filter_rules(j_remote_us)
    assert ex is True
    assert "restricted to another region" in reason


def test_filter_experience():
    # 2 years passes
    j2 = JobExtraction(title="Dev", cities=["Pune"], experience_min_years=2.0)
    ex, _, _, _ = evaluate_filter_rules(j2)
    assert ex is False

    # 3 years passes (boundary)
    j3 = JobExtraction(title="Dev", cities=["Pune"], experience_min_years=3.0)
    ex, _, _, _ = evaluate_filter_rules(j3)
    assert ex is False

    # 4 years excluded
    j4 = JobExtraction(
        title="Dev",
        cities=["Pune"],
        experience_min_years=4.0,
        experience_text="4+ years required",
    )
    ex, reason, snip, _ = evaluate_filter_rules(j4)
    assert ex is True
    assert "exceeds maximum allowed" in reason
    assert snip == "4+ years required"


def test_derive_verdict_thresholds():
    assert derive_verdict(8) == "strong"
    assert derive_verdict(7) == "strong"
    assert derive_verdict(6) == "stretch"
    assert derive_verdict(5) == "stretch"
    assert derive_verdict(4) == "weak"
    assert derive_verdict(2) == "weak"


def test_process_job_e2e_scoring(memory_db: sqlite3.Connection, sample_profile_envelope):
    raw_text = (
        "Role: AI Engineer at Kasnet. Location: Pune, India. Looking for a candidate skilled in "
        "Python and FastAPI. 0-1 years of experience. Competitive salary."
    )

    def fake_llm(sys_p: str, _usr_p: str) -> str:
        if "Extract structured details" in sys_p:
            return json.dumps(
                {
                    "title": "AI Engineer",
                    "company": "Kasnet",
                    "summary": "AI role",
                    "location_text": "Pune, India",
                    "cities": ["Pune"],
                    "work_mode": "onsite",
                    "remote_scope": "unspecified",
                    "experience_text": "0-1 years",
                    "experience_min_years": 0.0,
                    "pay_text": "Competitive salary",
                    "pay_status": "stated",
                    "skills": ["Python", "FastAPI"],
                }
            )
        else:
            return json.dumps(
                {
                    "score": 8,
                    "matches": [
                        {
                            "requirement": "Python & FastAPI",
                            "profile_item": "FastAPI",
                        }
                    ],
                    "gaps": ["No production Kubernetes experience"],
                    "explanation": "Strong fit for candidate's project background.",
                }
            )

    job_id, record = process_job(
        raw_text=raw_text,
        conn=memory_db,
        profile_envelope=sample_profile_envelope,
        llm_caller=fake_llm,
        llm_model="test-model",
    )
    assert job_id == 1
    assert record["outcome"] == "scored"
    assert record["score"] == 8
    assert record["verdict"] == "strong"

    stored = get_job_by_id(memory_db, 1)
    assert stored["title"] == "AI Engineer"
    assert stored["score"] == 8

    formatted = format_job_inspect(stored)
    assert "Score:           8/10" in formatted
    assert "Verdict:         STRONG" in formatted
    assert "FastAPI" in formatted
    assert raw_text not in formatted  # Never print raw posting in inspect


def test_process_job_excluded_triggers_no_second_call(
    memory_db: sqlite3.Connection, sample_profile_envelope
):
    raw_text = (
        "Senior Python Engineer needed in Pune with 6+ years experience. "
        "High salary with full health benefits and equity packages."
    )

    llm_calls = 0

    def fake_llm(_sys_p: str, _usr_p: str) -> str:
        nonlocal llm_calls
        llm_calls += 1
        return json.dumps(
            {
                "title": "Senior Python Engineer",
                "location_text": "Pune",
                "cities": ["Pune"],
                "experience_text": "6+ years",
                "experience_min_years": 6.0,
                "pay_status": "stated",
            }
        )

    job_id, record = process_job(
        raw_text=raw_text,
        conn=memory_db,
        profile_envelope=sample_profile_envelope,
        llm_caller=fake_llm,
        llm_model="test-model",
    )
    assert llm_calls == 1  # Only extraction called
    assert record["outcome"] == "excluded"
    assert "exceeds maximum allowed" in record["outcome_reason"]