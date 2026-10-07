import json
import sqlite3

import pytest

from jobagent.db import init_db
from jobagent.jobs import (
    JobExtraction,
    check_job_text_length,
    derive_verdict,
    evaluate_filter_rules,
    format_job_inspect,
    get_job_by_id,
    get_latest_job,
    process_job,
    verify_evidence_and_values,
)
from jobagent.llm import LLMError
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


def test_evidence_experience_digit_boundary():
    # "10+ years" should not substantiate minimum experience of 1 year
    raw_text = "Senior architect role with 10+ years required. Great benefits and high pay."
    ext = JobExtraction(
        title="Architect",
        experience_text="10+ years",
        experience_min_years=1.0,
    )
    verified, flags = verify_evidence_and_values(ext, raw_text)
    assert any("not substantiated" in f for f in flags)
    assert verified.experience_min_years is None


def test_evidence_alias_in_snippet_normalizes_to_city():
    # Issue 5 regression: Snippet is "Hinjewadi, India", LLM returned cities=["Pune"]
    raw_text = "Looking for a Python dev in Hinjewadi, India. Full time role at top company."
    ext = JobExtraction(
        title="Developer",
        location_text="Hinjewadi, India",
        cities=["Pune"],
    )
    verified, flags = verify_evidence_and_values(ext, raw_text)
    assert not flags
    assert verified.cities == ["Pune"]


def test_filter_disallowed_cities_with_india_excluded():
    # Issue 1 regression: Disallowed cities mentioning "India" must be excluded
    chennai_job = JobExtraction(
        title="Developer",
        cities=["Chennai"],
        location_text="Chennai, Tamil Nadu, India",
    )
    excluded, reason, snip, flags = evaluate_filter_rules(chennai_job)
    assert excluded is True
    assert "Chennai" in reason
    assert snip == "Chennai, Tamil Nadu, India"

    noida_job = JobExtraction(
        title="Developer",
        cities=["Noida"],
        location_text="Noida, Uttar Pradesh, India",
    )
    ex2, r2, _, _ = evaluate_filter_rules(noida_job)
    assert ex2 is True
    assert "Noida" in r2


def test_filter_only_country_stated_india_passes_with_flag():
    # Only country stated (no city) passes with flag
    job = JobExtraction(
        title="Developer",
        cities=[],
        location_text="Work anywhere across India",
    )
    excluded, _, _, flags = evaluate_filter_rules(job)
    assert excluded is False
    assert "only country stated (India)" in flags


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


def test_filter_pay_not_stated_flag():
    job = JobExtraction(title="Dev", cities=["Pune"], pay_status="not_stated")
    ex, _, _, flags = evaluate_filter_rules(job)
    assert ex is False
    assert "pay not stated" in flags


def test_filter_locations():
    # Allowed canonical city
    j_pune = JobExtraction(title="Dev", cities=["Pune"], location_text="Pune, MH")
    ex, _, _, _ = evaluate_filter_rules(j_pune)
    assert ex is False

    # Allowed alias (Bengaluru)
    j_bengaluru = JobExtraction(title="Dev", cities=["Bengaluru"], location_text="Bengaluru")
    ex, _, _, _ = evaluate_filter_rules(j_bengaluru)
    assert ex is False

    # Multi-city with one allowed (Delhi & Bangalore)
    j_multi = JobExtraction(title="Dev", cities=["Delhi", "Bangalore"], location_text="Both")
    ex, _, _, _ = evaluate_filter_rules(j_multi)
    assert ex is False

    # Remote India / Global
    j_remote_in = JobExtraction(title="Dev", work_mode="remote", remote_scope="india")
    ex, _, _, _ = evaluate_filter_rules(j_remote_in)
    assert ex is False

    j_remote_global = JobExtraction(title="Dev", work_mode="remote", remote_scope="global")
    ex, _, _, _ = evaluate_filter_rules(j_remote_global)
    assert ex is False

    # Unspecified remote scope passes with flag
    j_remote_unspec = JobExtraction(title="Dev", work_mode="remote", remote_scope="unspecified")
    ex, _, _, flags = evaluate_filter_rules(j_remote_unspec)
    assert ex is False
    assert "remote scope not stated" in flags

    # Remote other_region with verified restriction phrase
    j_remote_us = JobExtraction(
        title="Dev",
        work_mode="remote",
        remote_scope="other_region",
        location_text="US Only",
    )
    ex, reason, snip, _ = evaluate_filter_rules(j_remote_us)
    assert ex is True
    assert "restricted to another region" in reason
    assert snip == "US Only"


def test_filter_hallucinated_other_region_does_not_exclude():
    # Issue 3 regression: Hallucinated snippet must reset other_region
    raw_text = (
        "Global company hiring worldwide remote developers. Open to everyone. "
        "Work from anywhere in the world."
    )
    ext = JobExtraction(
        title="Dev",
        work_mode="remote",
        remote_scope="other_region",
        location_text="US residents only",  # Not in text
    )
    verified, flags = verify_evidence_and_values(ext, raw_text)
    assert verified.remote_scope == "unspecified"
    ex, _, _, _ = evaluate_filter_rules(verified)
    assert ex is False  # Must NOT exclude


def test_filter_experience():
    # 2 years passes
    j2 = JobExtraction(title="Dev", cities=["Pune"], experience_min_years=2.0)
    ex, _, _, _ = evaluate_filter_rules(j2)
    assert ex is False

    # 3 years passes (boundary)
    j3 = JobExtraction(title="Dev", cities=["Pune"], experience_min_years=3.0)
    ex, _, _, _ = evaluate_filter_rules(j3)
    assert ex is False

    # 0-1 years passes
    j01 = JobExtraction(title="Dev", cities=["Pune"], experience_min_years=0.0)
    ex, _, _, _ = evaluate_filter_rules(j01)
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

    # Unknown experience passes with flag
    j_unspec = JobExtraction(title="Dev", cities=["Pune"], experience_min_years=None)
    ex, _, _, flags = evaluate_filter_rules(j_unspec)
    assert ex is False
    assert "experience not stated" in flags


def test_derive_verdict_thresholds():
    assert derive_verdict(8) == "strong"
    assert derive_verdict(7) == "strong"
    assert derive_verdict(6) == "stretch"
    assert derive_verdict(5) == "stretch"
    assert derive_verdict(4) == "weak"
    assert derive_verdict(2) == "weak"


def test_process_job_transient_llm_error_stores_nothing(
    memory_db: sqlite3.Connection, sample_profile_envelope
):
    # Issue 2 regression: LLMError must raise and write zero rows
    raw_text = "Hiring a developer in Pune. Must know Python and FastAPI. " * 3

    def failing_llm(_sys: str, _usr: str) -> str:
        raise LLMError("Rate limit reached on Groq")

    with pytest.raises(LLMError, match="Rate limit"):
        process_job(
            raw_text=raw_text,
            conn=memory_db,
            profile_envelope=sample_profile_envelope,
            llm_caller=failing_llm,
            llm_model="test-model",
        )

    cursor = memory_db.execute("SELECT COUNT(*) FROM jobs;")
    assert cursor.fetchone()[0] == 0


def test_process_job_invalid_json_retries_and_fails(
    memory_db: sqlite3.Connection, sample_profile_envelope
):
    raw_text = "Hiring a developer in Pune. Must know Python and FastAPI. " * 3
    calls = 0

    def bad_json_llm(_sys: str, _usr: str) -> str:
        nonlocal calls
        calls += 1
        return "Non-JSON response"

    job_id, record = process_job(
        raw_text=raw_text,
        conn=memory_db,
        profile_envelope=sample_profile_envelope,
        llm_caller=bad_json_llm,
        llm_model="test-model",
    )
    assert calls == 2  # First call + retry
    assert record["outcome"] == "failed"
    assert job_id == 1


def test_process_job_scoring_drops_unsupported_match_with_warning(
    memory_db: sqlite3.Connection, sample_profile_envelope
):
    raw_text = (
        "AI Engineer in Pune. Knowledge of Python and Rust. "
        "0-1 years of experience required. Competitive pay package."
    )

    def llm_caller(sys_p: str, _usr: str) -> str:
        if "Extract structured details" in sys_p:
            return json.dumps(
                {
                    "title": "AI Engineer",
                    "cities": ["Pune"],
                    "location_text": "Pune",
                    "experience_text": "0-1 years",
                    "experience_min_years": 0.0,
                    "pay_status": "stated",
                }
            )
        return json.dumps(
            {
                "score": 7,
                "matches": [
                    {"requirement": "Python", "profile_item": "Python"},
                    {"requirement": "Rust", "profile_item": "Rust Language Expert"},
                ],
                "gaps": ["None"],
                "explanation": "Good fit.",
            }
        )

    job_id, record = process_job(
        raw_text=raw_text,
        conn=memory_db,
        profile_envelope=sample_profile_envelope,
        llm_caller=llm_caller,
        llm_model="test-model",
    )
    assert record["outcome"] == "scored"
    matches = json.loads(record["matches_json"])
    assert len(matches) == 1
    assert matches[0]["profile_item"] == "Python"
    flags = json.loads(record["flags_json"])
    assert any("Dropped unsupported match" in f for f in flags)


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
    assert raw_text not in formatted


def test_process_job_excluded_shows_snippet_in_inspect(
    memory_db: sqlite3.Connection, sample_profile_envelope
):
    # Issue 4 regression: Remote and other exclusions must output snippet in inspect
    raw_text = (
        "Senior Python Engineer needed in US Only with 6+ years experience. "
        "Work mode is remote for US residents only. High salary."
    )

    def fake_llm(_sys_p: str, _usr_p: str) -> str:
        return json.dumps(
            {
                "title": "Senior Python Engineer",
                "location_text": "US Only",
                "work_mode": "remote",
                "remote_scope": "other_region",
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
    assert record["outcome"] == "excluded"
    assert record["outcome_snippet"] == "US Only"

    stored = get_job_by_id(memory_db, job_id)
    formatted = format_job_inspect(stored)
    assert 'Snippet:         "US Only"' in formatted


def test_get_latest_job(memory_db: sqlite3.Connection):
    assert get_latest_job(memory_db) is None
    memory_db.execute(
        """
        INSERT INTO jobs (created_at, source, raw_text, outcome)
        VALUES ('2026-10-07T00:00:00', 'pasted', 'dummy raw text 1234567890', 'scored');
        """
    )
    memory_db.commit()
    latest = get_latest_job(memory_db)
    assert latest is not None
    assert latest["id"] == 1