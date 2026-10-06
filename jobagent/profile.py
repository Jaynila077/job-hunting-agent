import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

# Contact detail patterns to redact
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_REGEX = re.compile(r"https?://\S+|www\.\S+")
HANDLE_REGEX = re.compile(
    r"\b(?:linkedin\.com/in/[A-Za-z0-9_-]+|github\.com/[A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)
# Matches phone numbers while avoiding 4-digit year ranges (e.g. 2021-2025, 2023-2025)
PHONE_CANDIDATE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}"
)
YEAR_RANGE_REGEX = re.compile(r"^\s*(?:19|20)\d{2}\s*[-–—/]\s*(?:19|20)\d{2}\s*$")
SINGLE_YEAR_REGEX = re.compile(r"^\s*(?:19|20)\d{2}\s*$")


class EducationItem(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    period: str | None = None
    evidence: list[str] = Field(min_length=1)


class ExperienceItem(BaseModel):
    organization: str
    role: str
    period: str | None = None
    summary: str
    skills_used: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1)


class ProjectItem(BaseModel):
    name: str
    summary: str
    technologies: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1)


class SkillItem(BaseModel):
    name: str
    category: str | None = None
    evidence: list[str] = Field(min_length=1)


class CertificationItem(BaseModel):
    name: str
    issuer: str | None = None
    evidence: list[str] = Field(min_length=1)


class Profile(BaseModel):
    experience_level: str
    summary: str
    education: list[EducationItem] = Field(min_length=1)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    skills: list[SkillItem] = Field(min_length=1)
    certifications: list[CertificationItem] = Field(default_factory=list)


class EmbeddingItem(BaseModel):
    label: str
    vector: list[float]


class ProfileEnvelope(BaseModel):
    schema_version: int = 1
    profile_version: int
    created_at: str
    resume_sha256: str
    llm_model: str
    embed_model: str
    profile: Profile
    embeddings: list[EmbeddingItem] = Field(default_factory=list)


def redact_contact_details(text: str) -> str:
    """Replaces emails, phone numbers, URLs, and profile links with [REDACTED]."""
    text = EMAIL_REGEX.sub("[REDACTED]", text)
    text = HANDLE_REGEX.sub("[REDACTED]", text)
    text = URL_REGEX.sub("[REDACTED]", text)

    def replace_phone(m: re.Match[str]) -> str:
        matched = m.group(0).strip()
        # Protect year ranges and individual years from being redacted
        if YEAR_RANGE_REGEX.match(matched) or SINGLE_YEAR_REGEX.match(matched):
            return m.group(0)

        digits = re.sub(r"\D", "", matched)
        # Check if digits are simply two 4-digit years concatenated
        is_two_years = digits[:4].startswith(("19", "20")) and digits[4:].startswith(("19", "20"))
        if len(digits) == 8 and is_two_years:
            return m.group(0)

        # Phone numbers typically contain at least 10 digits or start with +
        if len(digits) >= 10 or (matched.startswith("+") and len(digits) >= 7):
            return "[REDACTED]"
        return m.group(0)

    return PHONE_CANDIDATE_REGEX.sub(replace_phone, text)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts raw text from a PDF file using pypdf."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Resume PDF not found: {pdf_path}")

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        text = "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError(f"Could not read PDF file {pdf_path}: {exc}") from exc

    cleaned = text.strip()
    if len(cleaned) < 50:
        raise ValueError(
            "PDF contains no readable text or is a scanned image (no OCR available)."
        )
    if len(cleaned) > 30000:
        raise ValueError("PDF content exceeds maximum supported length (30,000 characters).")

    return cleaned


def normalize_snippet(text: str) -> str:
    """Normalizes whitespace, removes bullet markers, and case-folds text."""
    text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\*\-\+]", " ", text)
    return " ".join(text.split()).lower()


def validate_profile(
    profile: Profile,
    redacted_text: str,
) -> tuple[list[str], list[str], Profile]:
    """Validates profile structure and evidence against redacted resume text."""
    errors: list[str] = []
    warnings: list[str] = []

    if not profile.experience and not profile.projects:
        errors.append("Profile must contain at least one experience or project entry.")

    norm_resume = normalize_snippet(redacted_text)
    raw_dump = profile.model_dump_json()

    if EMAIL_REGEX.search(raw_dump):
        errors.append("Contact detail detected in profile: email pattern matched.")
    if HANDLE_REGEX.search(raw_dump):
        errors.append("Contact detail detected in profile: handle pattern matched.")

    def check_items(items: list, section_name: str) -> list:
        valid_items = []
        for i, item in enumerate(items):
            valid_evidence = []
            for snip in getattr(item, "evidence", []):
                norm_snip = normalize_snippet(snip)
                if not norm_snip:
                    continue
                if norm_snip in norm_resume:
                    valid_evidence.append(snip[:300])
                else:
                    warnings.append(
                        f"Unmatched evidence in {section_name}[{i}]: '{snip[:60]}...'"
                    )
            if not valid_evidence:
                errors.append(
                    f"Item {section_name}[{i}] has no valid evidence in resume text."
                )
            else:
                valid_items.append(item.model_copy(update={"evidence": valid_evidence}))
        return valid_items

    new_edu = check_items(profile.education, "education")
    new_exp = check_items(profile.experience, "experience")
    new_proj = check_items(profile.projects, "projects")
    new_skills = check_items(profile.skills, "skills")
    new_certs = check_items(profile.certifications, "certifications")

    for sk in new_skills:
        if normalize_snippet(sk.name) not in norm_resume:
            warnings.append(f"Skill '{sk.name}' not found verbatim in resume text.")

    sanitized = profile.model_copy(
        update={
            "education": new_edu,
            "experience": new_exp,
            "projects": new_proj,
            "skills": new_skills,
            "certifications": new_certs,
        }
    )
    return errors, warnings, sanitized


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def get_latest_profile_envelope(profile_dir: Path) -> ProfileEnvelope | None:
    if not profile_dir.is_dir():
        return None
    files = sorted(profile_dir.glob("profile-v*.json"))
    if not files:
        return None
    latest_file = files[-1]
    try:
        data = json.loads(latest_file.read_text(encoding="utf-8"))
        return ProfileEnvelope.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Corrupt profile file {latest_file.name}: {exc}") from exc


def get_next_profile_version(profile_dir: Path) -> int:
    if not profile_dir.is_dir():
        return 1
    files = sorted(profile_dir.glob("profile-v*.json"))
    if not files:
        return 1
    m = re.search(r"profile-v(\d+)\.json$", files[-1].name)
    return int(m.group(1)) + 1 if m else 1


def build_embedding_units(profile: Profile) -> list[tuple[str, str]]:
    units: list[tuple[str, str]] = [("summary", profile.summary)]
    for i, exp in enumerate(profile.experience):
        skills_str = f" Skills: {', '.join(exp.skills_used)}" if exp.skills_used else ""
        units.append(
            (f"experience_{i}", f"{exp.role} at {exp.organization}. {exp.summary}{skills_str}")
        )
    for i, proj in enumerate(profile.projects):
        tech_str = f" Tech: {', '.join(proj.technologies)}" if proj.technologies else ""
        units.append((f"project_{i}", f"{proj.name}: {proj.summary}{tech_str}"))

    units.append(("skills", ", ".join(s.name for s in profile.skills)))

    edu_certs = [f"{e.degree} at {e.institution}" for e in profile.education]
    edu_certs.extend([f"Certified: {c.name}" for c in profile.certifications])
    units.append(("education_and_certifications", "; ".join(edu_certs)))
    return units


def _build_system_prompt() -> str:
    return (
        "You are an expert resume parser. Extract structured details from the redacted resume.\n"
        "Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "experience_level": "short string, e.g. Fresher / Entry-Level",\n'
        '  "summary": "2-4 sentence professional summary",\n'
        '  "education": [{"institution": "...", "degree": "...", "field": "...", '
        '"period": "...", "evidence": ["verbatim snippet"]}],\n'
        '  "experience": [{"organization": "...", "role": "...", "period": "...", '
        '"summary": "...", "skills_used": ["..."], "evidence": ["verbatim snippet"]}],\n'
        '  "projects": [{"name": "...", "summary": "...", "technologies": ["..."], '
        '"evidence": ["verbatim snippet"]}],\n'
        '  "skills": [{"name": "...", "category": "...", "evidence": ["verbatim snippet"]}],\n'
        '  "certifications": [{"name": "...", "issuer": "...", '
        '"evidence": ["verbatim snippet"]}]\n'
        "}\n"
        "CRITICAL RULES:\n"
        "1. Never invent or infer details not present in the text.\n"
        "2. Do NOT extract personal contact details (name, email, phone, links, addresses).\n"
        "3. Every single item MUST have at least one verbatim snippet in 'evidence'.\n"
        "4. Output pure JSON only. Do not add markdown fences."
    )


def build_profile(
    pdf_path: Path,
    profile_dir: Path,
    model_cache_dir: Path,
    llm_caller: Callable[[str, str], str],
    embedder: Callable[[list[str], str, Path | None], list[list[float]]],
    llm_model: str,
    embed_model: str,
    force: bool = False,
) -> tuple[int, Path, list[str], bool]:
    """Builds and stores a new versioned profile envelope.

    Returns: (version_number, written_path, warnings, is_new)
    """
    raw_pdf_text = extract_text_from_pdf(pdf_path)
    resume_sha256 = compute_sha256(pdf_path)
    redacted_text = redact_contact_details(raw_pdf_text)

    latest = get_latest_profile_envelope(profile_dir)
    if (
        not force
        and latest is not None
        and latest.resume_sha256 == resume_sha256
        and latest.schema_version == 1
        and latest.llm_model == llm_model
        and latest.embed_model == embed_model
    ):
        target = profile_dir / f"profile-v{latest.profile_version:04d}.json"
        return latest.profile_version, target, [], False

    system_prompt = _build_system_prompt()
    user_prompt = f"REDACTED RESUME TEXT:\n{redacted_text}"

    def parse_llm_json(raw_text: str) -> Profile:
        text = raw_text.strip()
        # Find outermost JSON object if there is conversational preamble
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        data = json.loads(text)
        return Profile.model_validate(data)

    llm_resp = llm_caller(system_prompt, user_prompt)
    try:
        profile_obj = parse_llm_json(llm_resp)
        errors, warnings, sanitized_profile = validate_profile(profile_obj, redacted_text)
    except Exception as exc:
        errors = [f"Initial JSON parse failed: {exc}"]
        sanitized_profile = None

    if errors or sanitized_profile is None:
        retry_prompt = (
            f"The previous extraction failed validation:\n{chr(10).join(errors)}\n\n"
            "Ensure valid JSON and verbatim snippets. Return ONLY pure JSON."
        )
        retry_resp = llm_caller(system_prompt, f"{user_prompt}\n\n{retry_prompt}")
        try:
            profile_obj = parse_llm_json(retry_resp)
            errors, warnings, sanitized_profile = validate_profile(profile_obj, redacted_text)
            if errors:
                raise ValueError(f"Profile validation failed: {len(errors)} errors found.")
        except Exception as exc:
            raise ValueError(f"Profile extraction failed after retry: {exc}") from exc

    embedding_units = build_embedding_units(sanitized_profile)
    labels = [lbl for lbl, _ in embedding_units]
    texts_to_embed = [txt for _, txt in embedding_units]
    vectors = embedder(texts_to_embed, embed_model, model_cache_dir)
    embeddings = [
        EmbeddingItem(label=lbl, vector=vec)
        for lbl, vec in zip(labels, vectors, strict=True)
    ]

    next_version = get_next_profile_version(profile_dir)
    envelope = ProfileEnvelope(
        schema_version=1,
        profile_version=next_version,
        created_at=datetime.now(timezone.utc).isoformat(),
        resume_sha256=resume_sha256,
        llm_model=llm_model,
        embed_model=embed_model,
        profile=sanitized_profile,
        embeddings=embeddings,
    )

    profile_dir.mkdir(parents=True, exist_ok=True)
    out_file = profile_dir / f"profile-v{next_version:04d}.json"

    with tempfile.NamedTemporaryFile(
        "w", dir=str(profile_dir), delete=False, encoding="utf-8"
    ) as tf:
        tf.write(envelope.model_dump_json(indent=2))
        temp_name = tf.name

    os.replace(temp_name, out_file)
    return next_version, out_file, warnings, True


def format_profile_inspect(envelope: ProfileEnvelope, current_pdf: Path | None = None) -> str:
    lines: list[str] = [
        f"Profile Version: v{envelope.profile_version:04d} (Schema v{envelope.schema_version})",
        f"Created At:      {envelope.created_at}",
        f"LLM Model:       {envelope.llm_model}",
        f"Embedding Model: {envelope.embed_model}",
    ]

    if current_pdf is not None and current_pdf.is_file():
        current_sha = compute_sha256(current_pdf)
        if current_sha != envelope.resume_sha256:
            lines.append("Status:          OUT OF DATE (Resume PDF changed. Run 'profile build'.)")
        else:
            lines.append("Status:          Up to date")
    else:
        lines.append("Status:          Current resume PDF not found on disk")

    p = envelope.profile
    lines.append("-" * 60)
    lines.append(f"Experience Level: {p.experience_level}")
    lines.append(f"Summary:          {p.summary}")
    lines.append("-" * 60)

    lines.append(f"Education ({len(p.education)}):")
    for edu in p.education:
        lines.append(f"  * {edu.degree} - {edu.institution} ({edu.period or 'N/A'})")
        for snip in edu.evidence[:2]:
            lines.append(f"    Evidence: \"{snip[:80]}\"")

    lines.append(f"\nExperience ({len(p.experience)}):")
    for exp in p.experience:
        lines.append(f"  * {exp.role} @ {exp.organization} ({exp.period or 'N/A'})")
        lines.append(f"    Summary: {exp.summary}")
        for snip in exp.evidence[:2]:
            lines.append(f"    Evidence: \"{snip[:80]}\"")

    lines.append(f"\nProjects ({len(p.projects)}):")
    for proj in p.projects:
        lines.append(f"  * {proj.name}")
        lines.append(f"    Technologies: {', '.join(proj.technologies)}")
        for snip in proj.evidence[:2]:
            lines.append(f"    Evidence: \"{snip[:80]}\"")

    lines.append(f"\nSkills ({len(p.skills)}):")
    lines.append(f"  {', '.join(s.name for s in p.skills)}")

    if p.certifications:
        lines.append(f"\nCertifications ({len(p.certifications)}):")
        for cert in p.certifications:
            issuer = f" ({cert.issuer})" if cert.issuer else ""
            lines.append(f"  * {cert.name}{issuer}")

    lines.append("-" * 60)
    lines.append(f"Embeddings: {len(envelope.embeddings)} vectors stored")
    if envelope.embeddings:
        lines.append(f"Dimension:  {len(envelope.embeddings[0].vector)}")

    return "\n".join(lines)