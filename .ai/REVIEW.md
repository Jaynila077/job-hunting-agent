# Code Review

## Task

**Title:** M1 – Profile Model, reviewed against `ARCHITECTURE.md` (which overrides `TASK.md` where they differ).

**Review Status:** CHANGES REQUIRED

**What I actually did:** read every changed file in the live repo (`jobagent/*.py`, `tests/*`, `requirements.txt`, `.env.example`, `README.md`), and ran the phone-redaction regex on sample text in a sandbox. **I could not run `pytest`, `ruff`, or `profile build`** (no packages, no network, and I did not read the resume or `.env`). Nothing below claims those pass.

---

## Verification Summary

| Check | Status | Notes |
|-------|--------|-------|
| Requirements | ⚠️ | Code covers the spec; README and several tests missing |
| Architecture | ✅ | 3 flat modules, lazy `fastembed`, JSON versions in `private/profile/`, no extra dependencies |
| Functionality | ❌ | Phone redaction removes year ranges (Issue 1) |
| Error handling | ⚠️ | Good LLM error mapping; a few spec gaps (Minor) |
| Security | ✅ | Key hidden from `repr`, no bodies in errors, nothing logged, output stays in `private/` |
| Tests | ⚠️ | Config and LLM tests good; profile tests too thin (Issue 4) |
| Lint | ❌ | `ruff check .` very likely fails on line length (Issue 3) |
| End-to-end | ❌ | Never run: `private/` has no `profile/` folder (Issue 3) |

---

# Critical Issues

None.

---

# Important Issues

### Issue 1

**Severity:** Important

**File:** `jobagent/profile.py` (`PHONE_REGEX`, `redact_contact_details`)

**Problem:** The phone pattern treats any run of 8+ digits as a phone number. I ran it: `2021-2025` becomes `[REDACTED]`, and so does `Batch 2025 2026`. Real phones were redacted correctly (`+91 98765 43210`, `9876543210`). `Dec 2023 - Feb 2024` and `CGPA 8.52/10` survive.

**Why it matters:** Your education line ("SPPU, 2021-2025") loses its dates before the LLM sees it, so `period` will be wrong or empty. The evidence check still passes because it compares against the already-redacted text, so nothing flags the loss.

**Required Fix:** Redact only phone-like numbers: for example, require a leading `+`, or at least 10 digits, or digit groups that are not two 4-digit years. Never redact a plain `YYYY-YYYY` or `YYYY YYYY` range. Add tests for year ranges, "2023-24", and the existing phone formats.

---

### Issue 2

**Severity:** Important

**File:** `README.md`

**Problem:** Not updated. It still says "M0 (setup) done", lists only `info` and `init-db`, and the folder map omits `llm.py`, `embed.py` and `profile.py`. It says nothing about the resume location, `GROQ_API_KEY`, `profile build` / `profile inspect`, or the first-run model download.

**Why it matters:** The spec lists README updates as a required change. Without them, setup of M1 can't be followed from the repo.

**Required Fix:** Update the status line; add the two profile commands; say the resume goes in `private/` (name set by `JOBAGENT_RESUME_FILE`); mention that the first build downloads the embedding model to `private/models/`; update the folder map.

---

### Issue 3

**Severity:** Important

**File:** `jobagent/profile.py`, `tests/test_profile.py` (and an unverified end-to-end run)

**Problem:**
- **Lint:** `ruff` is set to `E` with line length 100. `profile.py` has many lines over 100 (the schema lines inside `system_prompt`, the early `return`, the `embeddings = [...]` line, the `NamedTemporaryFile` line, several in `format_profile_inspect`). `test_profile.py` has long lines too (`resume_text`, the JSON in `fake_json_reply`). `ruff check .` should fail.
- **End-to-end:** `private/` contains `jobagent.db` and the resume PDF but **no `profile/` folder**, so `profile build` was never run successfully. The PDF is not named `resume.pdf` (the default), so `build` fails with "Resume file not found" until you set `JOBAGENT_RESUME_FILE` in `.env` (or rename the file).

**Why it matters:** Acceptance requires `ruff check .` to pass and the real resume to produce a real profile. Neither is shown.

**Required Fix:** Wrap or split long lines (or build the prompt from a short list of joined strings), run `ruff check .` and `ruff format .`, then run `profile build` and `profile inspect` on the real resume and report the output (counts, warnings, version file). The PDF name issue is on the owner's side.

---

### Issue 4

**Severity:** Important

**File:** `tests/test_profile.py`

**Problem:** Only 4 tests. Missing from the spec: year-range redaction (would have caught Issue 1), the retry path, "failure writes nothing", unchanged resume → no new version, `--force` → v2, zero-padded latest-version selection, corrupt file handling, inspect not printing vectors or the key, and the "contact detail in output" error. The build test replaces `extract_text_from_pdf` by hand-assigning to the module instead of using `monkeypatch`.

**Why it matters:** The versioning and failure behavior is the core of this milestone and is untested.

**Required Fix:** Add those tests (fake LLM and fake embedder, no network, no real resume), and use `monkeypatch.setattr` for the PDF function.

---

# Minor Issues

- **`profile.py` / `__main__.py` (unchanged resume):** the CLI prints "Profile built successfully: vNNNN" even when nothing was built. The spec says "profile unchanged (vN)". Also, the unchanged check doesn't compare `schema_version`.
- **`profile.py` (retry):** the retry only triggers when an item ends up with zero evidence. A first reply that fails pydantic parsing (for example an empty `skills` list) gets no retry. The retry reply is parsed without the wrapper used for the first reply.
- **`profile.py` (error text):** pydantic validation messages can include fragments of the reply or resume text, and `cmd_profile_build` prints them. Print a generic message plus the error count instead.
- **`profile.py` (`get_latest_profile_envelope`):** swallows all exceptions, so a corrupt latest file shows as "No profile found". Spec says report it plainly.
- **`profile.py` (inspect):** does not re-run validation against the current PDF as the spec describes; only the staleness check is done.
- **`profile.py` (`validate_profile`):** the contact-leak check covers emails and handles only; the spec also lists URLs and phone patterns (add after fixing Issue 1).
- **`profile.py` (`build_profile`):** `zip(..., strict=False)` would silently truncate if the embedder returns fewer vectors; use `strict=True`.
- **Evidence strength:** very short snippets (for example "Python") match almost anywhere. Consider a small minimum length for non-skill items.

---

# Requirement Verification

| Requirement (`ARCHITECTURE.md`) | Status | Notes |
|---|---|---|
| Resume PDF read from `private/`, nothing tracked | ✅ | `private/` ignored; default filename differs from the actual file (owner action) |
| Profile model, no name/contact/targets | ✅ | Models match the spec |
| Evidence per item, checked against redacted text | ✅ | Works; weak on very short snippets (Minor) |
| Local embeddings, lazy import, cache in `private/models` | ✅ | Matches the spec |
| Versioned atomic JSON, no-op on unchanged | ✅ | Logic correct; message misleading (Minor) |
| `profile inspect` summary, stale flag | ⚠️ | Works; no re-validation (Minor) |
| Redaction before network call | ⚠️ | Happens, but over-redacts years (Issue 1) |
| No secrets or text in logs | ✅ | Nothing logged; terminal error text can leak fragments (Minor) |
| `pytest` and `ruff check .` pass | ❌ | Not shown; ruff likely fails |
| No extra dependencies | ✅ | Exactly the four listed |
| `info`, `init-db`, `.ai/` unchanged | ✅ | `info` also fixed the earlier git probe issue and shows resume/key status |

---

# What Was Done Correctly

> Do not change these during fixes.

- `config.py`: new settings with defaults, empty values treated as unset, `groq_api_key` hidden from `repr`; tests updated and thorough.
- `llm.py`: clean error mapping with no key or body in messages; `MockTransport` tests.
- `embed.py`: lazy import, cache directory, rounded floats.
- CLI wiring in `__main__.py` and the corrected `check_git_ignored`.
- `requirements.txt` and `.env.example`.

---

# Required Changes

- [ ] Fix phone redaction so year ranges survive; add tests (Issue 1).
- [ ] Update `README.md` (Issue 2).
- [ ] Make `ruff check .` pass; run `profile build` and `profile inspect` on the real resume and report the output (Issue 3).
- [ ] Add the missing profile tests (Issue 4).
- [ ] (Minor) "unchanged" message, retry coverage, generic parse-error text, corrupt-file message, `strict=True`.
- [ ] Re-run `pytest`, `ruff check .`, `python -m jobagent info`, and report the exact output.

---

# Final Assessment

**Status:** CHANGES DONE, Move to next stages

**Summary:** The design was followed well and the supporting modules are clean. One real bug (dates removed by redaction), a lint failure, an unrun end-to-end build, a missing README update, and thin profile tests block a PASS.

**Blocking Issues:** 4 Important (Issues 1–4), 0 Critical.

**Recommendation:** Fix Issues 1–4, run the real build, send the output, and I'll re-check.
