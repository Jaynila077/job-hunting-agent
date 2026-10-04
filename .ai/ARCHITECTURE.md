# Implementation Specification

> This document defines **how the current task should be implemented**.
> The implementation agent treats it as the primary technical specification, while still verifying all assumptions against the actual codebase.

> **Handoff note.** This file is overwritten for every task. Durable context is in `PROJECT.md`. The owner wants this project **simple**: few files, few dependencies, plain functions. Where this document and `TASK.md` differ, follow this document and report it (see "Overrides of TASK.md").

---

## Task

**Title:** M1 – Profile Model

**Objective:** Read the owner's PDF resume from `private/`, build a validated, structured profile (with evidence snippets and embeddings), store it as a versioned JSON file in `private/`, and provide two commands: `profile build` and `profile inspect`.

---

## Overrides of TASK.md

Decided with the owner after `TASK.md` was written:

1. **Embeddings use a separate local model**, not the LLM provider (`fastembed`). This reverses the earlier "no embeddings" decision in `PROJECT.md` (updated by the owner/architect). There is still **no vector database**.
2. **Resume is a PDF** (default `private/resume.pdf`).
3. **Target roles and target locations are NOT profile fields.** They are background for the architect, not extracted from the resume.
4. **Two commands**, not one: `profile build` (creates a version) and `profile inspect` (read-only display). `TASK.md` only names `inspect`.
5. Ignore the "M2–M7" wording in `TASK.md`.

---

## Current Architecture

Verified against the repository (M0 passed review).

- Flat package `jobagent/` at the repo root, run as `python -m jobagent`.
- `config.py`: frozen `Settings` dataclass (`repo_root`, `private_dir`, `db_path`, `log_level`); `load_settings()` reads `.env` through `python-dotenv`, real environment variables win, unknown `.env` keys are ignored, relative paths resolve from the repo root.
- `__main__.py`: argparse with flat commands `info` and `init-db`; `cmd_*` functions return an exit code; errors go to stderr.
- `log.py`: `setup_logging(level)`. `db.py`: SQLite helper with an empty step list (**not used by M1**).
- Dependencies today: `python-dotenv`, `pytest`, `ruff`. Tests use `tmp_path` and `monkeypatch`.
- `.gitignore` already ignores `private/`, `.env`, `.env.*` (except `.env.example`), databases. No change needed.
- `private/` currently contains only `jobagent.db`. **No resume is present yet.**
- `tools/edit_task.ps1` already uses Groq model `openai/gpt-oss-20b` (a precedent for the default model name).

---

## Proposed Architecture

### Data flow

```text
private/resume.pdf ─► pypdf text ─► redact contact details ─► Groq (JSON) ─► pydantic validation
                                         │                                        │
                                         └──── evidence check (snippets must ◄────┘
                                               exist in redacted text)
                                                              │
                                  fastembed (local) ◄─────────┘  section texts
                                                              ▼
                              private/profile/profile-v0001.json (atomic write)

profile inspect ─► load latest version ─► re-read PDF locally ─► re-validate ─► print
```

### New modules (3 files, plain functions)

| File | Responsibility |
|------|----------------|
| `jobagent/llm.py` | One function: send a system and user message to Groq's OpenAI-compatible chat completions endpoint with `httpx`, return the reply text. No SDK. |
| `jobagent/embed.py` | One function: embed a list of texts with `fastembed`, return lists of floats. Import `fastembed` **lazily** inside the function so tests and `info` never load it. |
| `jobagent/profile.py` | Models, PDF reading, redaction, build, validation, saving and loading versions, inspect formatting. |

### Profile model (pydantic v2)

All lists are lists of small models. **Every item carries `evidence: list[str]`** (at least one verbatim snippet from the redacted resume, each at most ~300 characters).

- `experience_level` (short text, e.g. fresher/entry-level) and `summary` (2–4 sentences)
- `education[]`: institution, degree, field (optional), period (optional)
- `experience[]`: organization, role, period (optional), summary, skills used
- `projects[]`: name, summary, technologies
- `skills[]`: name, category (optional)
- `certifications[]`: name, issuer (optional)

Deliberately **absent**: name, email, phone, links, address, target roles, target locations.

### Stored file (one JSON per version)

Path: `private/profile/profile-v0001.json`, `-v0002.json`, ... Never overwrite an existing version; the latest is the highest number.

Envelope fields: `schema_version` (int, starts at 1), `profile_version` (int), `created_at` (UTC ISO 8601), `resume_sha256` (hash of the PDF bytes), `llm_model`, `embed_model`, `profile` (the model above), `embeddings` (list of `{label, vector}`).

Embedding units, built by one deterministic function from the profile: `summary`; one per experience entry; one per project; `skills` (all skill names joined); `education_and_certifications` (joined). Round floats to 6 decimals. Embeddings are stored but **not used for anything yet** (matching is a later milestone).

### Build behavior (`profile build [--force]`)

1. Load settings; require `GROQ_API_KEY` and the resume file; fail early with a one-line message otherwise.
2. Extract PDF text with `pypdf`. If the text is empty or under a small minimum (scanned PDF), fail with a clear message (no OCR). If over ~30,000 characters, fail.
3. Redact contact details in Python **before** any network call: emails, phone numbers, URLs and bare `linkedin.com/…` / `github.com/…` handles become a placeholder such as `[REDACTED]`.
4. If the latest version exists with the same `resume_sha256`, `schema_version`, `llm_model` and `embed_model`, print "profile unchanged (vN)" and exit 0, unless `--force`.
5. Call the LLM once. System prompt: extract only what is written, never infer or invent, omit name and contact details, copy evidence verbatim, return a single JSON object with the specified keys and nothing else. Strip accidental code fences. Parse and validate with pydantic.
6. Run validation (below). If evidence snippets fail the check, **re-ask once**, listing the failing snippets. After that, drop any still-unmatched snippet and record it as a warning; if an item is left with zero evidence, the build fails.
7. Embed the section texts. The first run downloads the embedding model (needs network once); set the model cache to `private/models/` so it stays git-ignored.
8. Write the new version atomically (temp file in the same folder, then `os.replace`). Print version, path, counts and any warnings.

On any failure, **write nothing**.

### Inspect behavior (`profile inspect`)

Read-only, no network. Loads the latest version and prints: version, timestamp, models, whether the resume has changed since the build (hash mismatch → "profile is out of date, run `profile build`"); a short summary of what was understood (counts per section, experience level, summary); each section's items with up to two evidence snippets each (truncated for readability); embeddings count and dimension (never the vectors); and the result of re-running validation against the current PDF (errors and warnings). If no profile exists, say so and suggest `profile build`. If the PDF is missing, still show the stored profile and skip re-validation with a note.

### CLI shape

Add a nested `profile` command to the existing argparse setup with subcommands `build` and `inspect`. Keep `info` and `init-db` unchanged. Follow the existing pattern: `cmd_*` returns an exit code, errors to stderr, `setup_logging` called as `cmd_init_db` does.

---

## Validation Rules (deterministic, no LLM)

**Errors (build fails; inspect reports them):**
- `education` empty, `skills` empty, or both `experience` and `projects` empty. (`certifications` may be empty.)
- Any item without at least one evidence snippet.
- An evidence snippet not found in the redacted resume text. Compare after normalizing both sides: collapse whitespace, strip bullet characters, case-fold.
- Any text in the profile or evidence that matches the contact-detail patterns (defense in depth).

**Warnings (shown, not fatal):** a skill or technology name not found in the resume text (possible invention); snippets dropped after the retry.

---

## Implementation Plan

1. **Config** – extend `Settings` with `resume_path`, `llm_model`, `embed_model`, `groq_api_key` (field with `repr=False`, `None` if missing), and `profile_dir`/`model_cache_dir` derived from the private dir. New variables: `JOBAGENT_RESUME_FILE` (default `resume.pdf`, relative to the private dir, same pattern as the DB file), `JOBAGENT_LLM_MODEL` (default `openai/gpt-oss-20b`), `JOBAGENT_EMBED_MODEL` (default `BAAI/bge-small-en-v1.5`). Real environment variables win over `.env`, as today. Existing tests must pass unchanged.
2. **Dependencies** – add `pydantic`, `httpx`, `pypdf`, `fastembed` to `requirements.txt` (lower bounds only). Verify they install on Python 3.11 under Miniconda on Windows; report the install result.
3. **`llm.py`** – one call, timeout, HTTPS only, `temperature` 0. Map failures to short errors (missing key, 401, 429, 5xx, network) that **never include the key, the request, or the response body**.
4. **`embed.py`** – lazy `fastembed` wrapper with the cache directory set.
5. **`profile.py`** – models, PDF read, redaction, prompt, build, validation, save/load, inspect text.
6. **`__main__.py`** – nested `profile` command. `info` additionally prints the resume path and whether it exists, and "LLM key: set/missing" (never the value).
7. **Docs and tests** – `.env.example`, README, tests (below).

Confirm with the implementer's own check that the default Groq model exists and returns JSON reliably; if not, pick another Groq model, set it as the default, and report it.

---

## Files To Modify

| File | Change |
|------|--------|
| `jobagent/config.py` | New settings fields and variables (above) |
| `jobagent/__main__.py` | Nested `profile` command; extra lines in `info` |
| `requirements.txt` | Four new dependencies |
| `.env.example` | Document the three new variables; `GROQ_API_KEY` is now used (placeholder only) |
| `README.md` | Status line, `profile build` / `profile inspect` usage, where to put the resume, folder map entries |
| `tests/test_config.py` | **Add** cases for the new variables; do not change existing tests |

## Files To Create

`jobagent/llm.py`, `jobagent/embed.py`, `jobagent/profile.py`, `tests/test_profile.py`, `tests/test_llm.py`.

## Files That Must Not Be Modified

- `.ai/PROJECT.md`, `.ai/TASK.md`, `.ai/prompts/*` (owner/architect only)
- `tools/edit_task.ps1`
- `jobagent/db.py`, `jobagent/log.py`, `tests/test_db.py`; no new database tables or schema steps
- `.gitignore` (already correct; only change it if verification shows `private/profile/` or `private/models/` are not ignored)
- The owner's `.env` and anything in `private/`

---

## Database Changes

None. The profile is JSON in `private/profile/`.

## Backend Changes

CLI only; no API endpoints.

## Frontend Changes

None.

## AI / ML Changes

- One LLM call per build (plus at most one retry). The LLM has no tools and writes nothing.
- Embeddings come from a local ONNX model through `fastembed`; no data leaves the machine for that step.
- The prompt and the redacted resume text are the only things sent to Groq.

## External Services

Groq chat completions (existing choice in `PROJECT.md`). Hugging Face model download by `fastembed` on first run only.

---

## Security Considerations

- Redaction happens before the network call and is unit-tested with fake contact details.
- The resume text, the LLM reply, evidence snippets and the API key are never logged. Logs may contain counts, version numbers and model names only.
- All outputs live under `private/` (ignored). Test fixtures use invented fake resume text, never the owner's real resume.
- Name, employer and institution names remain in the text sent to Groq; this is accepted under the existing "hosted provider" decision, which only excludes contact details.
- Prompt-injection text inside the PDF cannot cause actions, because the LLM has no tools and its output is only parsed and validated.

## Performance Considerations

One short LLM call and a handful of embeddings. The first embedding run pays a one-time model download; later runs load from the cache. `inspect` and the unchanged-resume path do no network or model work.

---

## Edge Cases

- No resume file, no API key, empty or scanned PDF, encrypted PDF, very long text.
- PDF layout problems (multi-column interleaving, ligatures, hyphenation) causing evidence mismatches: the normalization and the single retry handle most of it; persistent failure must produce a clear message listing how many snippets failed, not a stack trace.
- LLM returns fences, extra text, or invalid JSON: strip fences; one retry; then fail.
- Rate limit or network failure: short message, nothing written.
- Rebuild with the same resume: no new version unless `--force`.
- Corrupt or hand-edited latest JSON: `inspect` reports it plainly.
- Windows paths with spaces; UTF-8 for all JSON; version numbers zero-padded so sorting works.

## Backwards Compatibility

`info` and `init-db` keep working. New `Settings` fields have defaults, so existing callers and tests are unaffected. No schema change.

---

## Testing Strategy

No test may use the network, a real API key, a real resume, or download a model. Build functions take the LLM call and the embedder as parameters (plain callables) so tests pass fakes.

- **Redaction:** emails, phones, URLs, handles replaced; ordinary text untouched.
- **Validation:** missing section, item without evidence, evidence not in text, invented skill (warning), contact pattern in output.
- **Build:** happy path with a fake LLM and fake embedder; fence stripping; one retry on bad evidence; failure writes nothing; unchanged resume → no new version; `--force` → v2; atomic write leaves no temp file.
- **Storage:** latest-version selection, zero-padded names, corrupt file handling.
- **Inspect:** output contains counts, evidence, version, staleness note; never prints vectors or the API key.
- **Config:** new variables default and override correctly; `groq_api_key` absent from `repr(settings)`.
- **LLM client:** with `httpx.MockTransport`, error mapping for 401/429/5xx; messages exclude the key.
- **PDF reading:** generate a tiny PDF in the test (or skip with a clear reason if that needs an extra dependency); do not add a dependency just for this.

### Manual verification (owner, Windows PowerShell)

```text
pip install -r requirements.txt
python -m jobagent info
python -m jobagent profile build
python -m jobagent profile inspect
python -m jobagent profile build        (expect: unchanged)
python -m jobagent profile build --force  (expect: v2)
pytest
ruff check .
git status                              (expect: nothing from private/)
```

Then read the inspect output against the real resume: every section correct, nothing invented, no contact details.

---

## Acceptance Criteria

Mapped to `TASK.md`:

- [ ] The resume PDF is read from `private/` and is never tracked by Git.
- [ ] The profile model has education, experience, projects, skills, certifications, experience level and summary (target roles/locations intentionally excluded).
- [ ] Every item has evidence snippets that exist in the redacted resume text.
- [ ] Embeddings are generated locally for the defined sections and stored in the version file.
- [ ] Versioned JSON files with version number and timestamp are written atomically in `private/profile/`; rebuilding an unchanged resume creates nothing new.
- [ ] `profile inspect` prints the structured profile and a concise summary, and flags a stale profile.
- [ ] Validation runs on build and on inspect and reports errors and warnings as specified.
- [ ] Contact details are redacted before the LLM call and never stored.
- [ ] No secret, resume text or LLM reply appears in logs.
- [ ] `pytest` and `ruff check .` pass; `info`, `init-db` and `.ai/` are unchanged.
- [ ] No dependencies beyond the four listed.

---

## Risks & Trade-offs

- **Dependency weight:** `fastembed` brings `onnxruntime` and `numpy`. Accepted for local embeddings without PyTorch. If install fails on Windows, report it; do not substitute another heavy library silently.
- **Embeddings unused for now:** they are stored for later milestones. Trade-off accepted by the owner; JSON storage keeps it trivial.
- **Strict evidence check** may reject valid output on messy PDFs. Mitigated by normalization, one retry, and dropping unmatched snippets rather than failing outright.
- **Hosted LLM sees resume content** (minus contact details), per existing decision.

### Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Store the profile in SQLite | JSON files are simpler and satisfy the versioning requirement; no schema step needed |
| `sentence-transformers` | Pulls PyTorch; much heavier |
| Hosted embeddings API | Second key, sends resume text to another party |
| `openai` SDK | `httpx` is already in the agreed stack and one call is enough |
| A `profile/` sub-package | Three flat modules match the existing style |

---

## Implementation Constraints

The implementation agent MUST: follow this specification and report deviations; keep to the files and dependencies listed; verify assumptions against the repository; run `pytest` and `ruff check .` and report exactly what was run; never read or print `.env` values or the real resume in output.

The implementation agent MUST NOT: add job matching, scoring, a dashboard, database tables, other dependencies, or code for later milestones; modify the protected files above.

---

## Open Questions

1. **Resume filename:** default is `private/resume.pdf`. If the owner's file is named differently, set `JOBAGENT_RESUME_FILE` or rename it.
2. **Groq model:** default `openai/gpt-oss-20b`; the implementer confirms it works and reports.
3. **First-run download size** of the embedding model: implementer to report.

---

## Final Implementation Notes

<!-- Filled in after implementation if important discoveries caused deviations from this specification. -->

-
