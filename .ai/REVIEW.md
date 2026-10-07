# Code Review

## Task

**Title:** M2 – Job Analysis + Matching MVP, reviewed against `ARCHITECTURE.md` (which overrides `TASK.md` where they differ).

**Review Status:** CHANGES REQUIRED

**What I actually did:** read every changed file (`jobagent/jobs.py`, `db.py`, `__main__.py`, `tests/test_jobs.py`, `tests/test_db.py`, `README.md`); ran `pytest` and `ruff check .` in a fresh Python 3.13 venv (`pydantic httpx pypdf python-dotenv pytest ruff`; `fastembed` not installed, not needed by M2 code paths); and ran a small probe script that calls `evaluate_filter_rules`, `verify_evidence_and_values` and `process_job` with fake LLM callables to confirm each bug below. **I did not run the CLI against Groq, and did not read `.env`, the resume or `private/`.**

Results: `pytest` 27 passed. `ruff check .` **10 errors** (4 × E501 in `jobs.py`, 6 in `tests/test_jobs.py`: unused imports and unsorted imports).

---

## Verification Summary

| Check | Status | Notes |
|-------|--------|-------|
| Requirements | ⚠️ | Pipeline exists end to end; location and exclusion rules are wrong in common cases |
| Architecture | ✅ | One new module, one schema step, nested `job` CLI, no new dependencies, callables injected |
| Functionality | ❌ | Issue 1 (disallowed cities pass), Issues 2-5 |
| Error handling | ❌ | Transient LLM errors are stored as `failed` rows (Issue 2) |
| Security | ✅ | Posting delimited as data, LLM has no tools, parameterized SQL, no raw text in inspect |
| Performance | ✅ | Two calls per job, one insert |
| Tests | ❌ | 8 tests written; most of the list in `ARCHITECTURE.md` is missing (Issue 6) |
| Code quality | ⚠️ | `ruff` fails (Issue 7); README not updated |

---

# Critical Issues

### Issue 1

**Severity:** Critical

**File:**

```text
jobagent/jobs.py  (evaluate_filter_rules, Rule 2 else-branch, lines ~306-315)
```

**Problem:** The branch `elif extracted.location_text and "india" in normalize_snippet(extracted.location_text)` runs **before** the branch that excludes on named cities. Any disallowed city whose snippet contains the word "India" is passed with the flag "only country stated (India)". Confirmed by probe: `cities=["Chennai"], location_text="Chennai, India"` returns not excluded; same for "Noida, Uttar Pradesh, India". The existing test only passes because it uses the snippet "Chennai" with no country.

**Why it matters:** Most Indian postings write "City, State, India". The strict location rule (Pune, Mumbai, Bangalore, Hyderabad, remote only) is effectively off for them, so out-of-scope jobs get scored and shown. This breaks a project constraint ("No other cities").

**Required Fix:** Check `extracted.cities` first. The "only country stated (India)" flag applies only when the posting names **no city** and no remote mode. Order: allowed city, then remote handling, then (verified cities present and none allowed, so exclude), then no cities with "india" in the snippet (flag), then location unknown (flag). Add a test using "Chennai, India" and "Noida, Uttar Pradesh, India".

---

# Important Issues

### Issue 2

**Severity:** Important

**File:**

```text
jobagent/jobs.py  (process_job: both `except Exception` blocks around extract_job_details and score_job_fit)
```

**Problem:** `except Exception` also catches `LLMError` (network, auth, rate limit). Confirmed by probe: an `LLMError("rate limited")` at extraction stores a row with `outcome='failed'`, title "Unknown (Failed Extraction)", and the full raw text. The spec says these cases store **nothing** and exit 1 so the owner can paste again.

**Why it matters:** A rate limit or an expired key leaves junk `failed` rows with duplicated raw postings, labels an LLM outage as a bad extraction, and pasting again creates a second row.

**Required Fix:** Let `LLMError` propagate out of `process_job` (catch only `json.JSONDecodeError` / `pydantic.ValidationError` / `ValueError` for the retry-then-`failed` path), including when it is raised by the retry call. `cmd_job_paste` already maps `LLMError` to exit 1. Add tests for an `LLMError` at extraction and at scoring that assert zero rows.

### Issue 3

**Severity:** Important

**File:**

```text
jobagent/jobs.py  (verify_evidence_and_values and evaluate_filter_rules, remote_scope = "other_region" path)
```

**Problem:** The `other_region` exclusion has no evidence check. `verify_evidence_and_values` clears an unverified `location_text` but leaves `work_mode` and `remote_scope` as the LLM returned them. Confirmed by probe: a posting open to everyone worldwide, with the LLM hallucinating `location_text="US residents only"` and `remote_scope="other_region"`, is stored as **excluded** with `Remote role is restricted to another region`, and the exclusion has no snippet (probe 3 shows `None`).

**Why it matters:** This violates the evidence rule and the project decision "Strong matches are never silently lost": one wrong LLM field hides a good remote job.

**Required Fix:** When `location_text` fails verification, reset `remote_scope` to `unspecified` (and `work_mode` to `unknown` if it was `remote` with no other support) and flag it. Only exclude for `other_region` when a verified `location_text` exists. Ideally also require the snippet to contain a region-restriction phrase, mirroring the unpaid phrase check. Add a test: hallucinated snippet plus `other_region` must not exclude.

### Issue 4

**Severity:** Important

**File:**

```text
jobagent/jobs.py  (format_job_inspect, excluded branch, lines ~711-718)
```

**Problem:** The supporting snippet is chosen by searching the reason string for "Location", "experience" or "unpaid". The remote exclusion reason contains none of these, so for `Remote role is restricted to another region` no snippet is printed (confirmed by probe). `evaluate_filter_rules` already returns the snippet, but `process_job` throws it away.

**Why it matters:** The spec requires every exclusion to show its supporting snippet so the owner can check for wrongly excluded jobs. The string matching also breaks silently if a reason is reworded.

**Required Fix:** Store the snippet explicitly (a `outcome_snippet` column in schema step 1, or append it to `outcome_reason` in a fixed format) and print it for every excluded job. Do not infer it from reason text. Add an inspect test for each exclusion type.

### Issue 5

**Severity:** Important

**File:**

```text
jobagent/jobs.py  (verify_evidence_and_values, location block, lines ~256-266)
```

**Problem:** The extraction prompt asks the LLM to normalize cities, and the spec asks for it too (Hinjewadi becomes Pune). The verifier then checks that the city name appears in the snippet. Confirmed by probe: snippet "Hinjewadi, India" with `cities=["Pune"]` yields `cities=[]` with no flag. The loop `any(alias in norm_loc_snip for alias in aliases if alias == norm_c)` only matches an alias that equals the city name and is in the snippet, so it never accepts a canonical city for an alias in the snippet.

**Why it matters:** Valid Pune/Mumbai area postings lose their city silently and get flagged "location not stated" or "only country stated". Together with Issue 1's reordering, the rule's data is unreliable.

**Required Fix:** Accept a city when the city name **or any alias of the same canonical city** appears in the snippet (for example, canonical `pune` is supported by "hinjewadi" in the snippet). Keep dropping cities supported by nothing in the snippet. Add tests for Hinjewadi→Pune and Bengaluru.

### Issue 6

**Severity:** Important

**File:**

```text
tests/test_jobs.py, tests/test_db.py
```

**Problem:** The spec said to write every listed test, not a token few. Present: input length, one evidence test, unpaid, locations, experience, verdict, one scored e2e, one excluded e2e, schema step. Missing:

- `--file` read as UTF-8, empty and whitespace-only input
- Extraction: fences and preamble stripped, missing title, invalid JSON retried then stored as `failed` with raw text
- Evidence rule: a verified unpaid claim excludes while an unverified one does not; the "paid leave policy" unpaid case; a city not in the snippet not used to exclude; experience "4+ years" vs "2+ years"
- Filters: Bengaluru alias, `not_stated` pay flag, global remote, unspecified remote flag, unknown location flag, "0-1" experience, unknown experience flag
- Scoring: retry on out-of-range or non-integer score, retry succeeds, unsupported `profile_item` dropped with a warning, second failure stored as `failed`
- Outcomes: transient `LLMError` stores nothing, no profile or no key fails before any LLM call, success stores exactly one row
- Inspect: missing id, empty database, flags, exclusion reason and snippet, no `raw_text`
- CLI wiring for `job paste` and `job inspect`

**Why it matters:** The gaps include the paths where Issues 1-5 hide; the suite gave 27 green results while the location rule was broken.

**Required Fix:** Add the missing tests, including regression tests for Issues 1-5. Use fake callables and `tmp_path`; no network.

### Issue 7

**Severity:** Important

**File:**

```text
jobagent/jobs.py (lines 351, 373, 393, 395), tests/test_jobs.py (lines 1-16)
```

**Problem:** `ruff check .` reports 10 errors: four E501 (lines over 100 characters) in `jobs.py`; in `tests/test_jobs.py` an unsorted import block and unused `Path`, `connect`, `JobScoreOutput`, `MatchItem`, `get_latest_job`.

**Why it matters:** "`pytest` and `ruff check .` pass" is an acceptance criterion, and the architecture handoff note named this exact lesson from M1.

**Required Fix:** Wrap the four prompt lines, remove unused imports, sort imports. Run `ruff check .` and report the real output.

---

# Minor Issues

- **File:** `jobagent/jobs.py` (verify_evidence_and_values, experience block)
  - **Problem:** The digit check is a plain substring test, so min `1` is "supported" by "10+ years" (probe 5: value kept as 1.0, so a 10-year job is not excluded).
  - **Suggested Fix:** Match whole numbers with a regex such as `(?<!\d)1(?!\d)`.

- **File:** `jobagent/jobs.py` (extract_job_details, score_job_fit, process_job)
  - **Problem:** The raw exception text, which for pydantic includes `input_value=...` from the model reply, goes into the retry prompt, into `outcome_reason`, and is printed by `job paste`. The spec says not to echo reply bodies.
  - **Suggested Fix:** Summarise errors as field names and error types only.

- **File:** `jobagent/__main__.py` (cmd_job_inspect)
  - **Problem:** The "read-only" command calls `connect` and `init_db`, so it can create and migrate the database file. The connection is also not closed on exceptions in `cmd_job_paste`.
  - **Suggested Fix:** Open the database only if it exists in `inspect`, and use `try/finally` for `conn.close()`.

- **File:** `jobagent/jobs.py` (get_job_by_id, get_latest_job)
  - **Problem:** They set `conn.row_factory` on the caller's shared connection.
  - **Suggested Fix:** Use a local cursor with `row_factory` set on it, or restore the previous value.

- **File:** `jobagent/__main__.py` (cmd_job_paste)
  - **Problem:** The input length check happens after `connect`/`init_db`, so empty input still touches the database.
  - **Suggested Fix:** Call `check_job_text_length` before opening the database.

- **File:** `README.md`
  - **Problem:** Not updated for M2 (status line, `job paste` and `job inspect`, `jobs.py` in the folder map, the "empty database" line).
  - **Suggested Fix:** Do the README step from the implementation plan.

---

# Requirement Verification

| Requirement | Status | Notes |
|-------------|--------|-------|
| A posting can be pasted via `job paste` (stdin or `--file`) | ✅ | Code present; I did not run it against Groq |
| Parsed into the structured model with all fields | ✅ | `JobExtraction` covers every field; `source` and `url` come from flags |
| Filtering applied, unsuitable jobs excluded, only on verified evidence | ❌ | Issues 1, 3, 5 |
| Scored 1-10 with matches, gaps, explanation, matches checked against profile | ✅ | Validation, retry and verdict thresholds as specified |
| Stored in `private/jobagent.db` (git-ignored), excluded and failed kept | ⚠️ | Stored correctly; transient errors also stored (Issue 2) |
| `job inspect` shows details, score, matches, gaps, explanation, flags, reason | ⚠️ | Snippet missing for remote exclusions (Issue 4) |
| Constraints from `PROJECT.md` hold | ❌ | Location rule and "never silently lost" broken (Issues 1, 3) |
| `pytest` and `ruff check .` pass | ❌ | pytest passes; ruff has 10 errors (Issue 7) |
| No new dependencies, protected files untouched | ✅ | `requirements.txt` unchanged; I could only compare against the single available commit, not an earlier diff |

---

# Architecture Verification

### Correct

- New `jobs.py` with plain functions; LLM calls injected as callables.
- `db.py` adds `step_1_create_jobs_table` and appends it to `SCHEMA_STEPS`; DDL runs inside the existing `BEGIN IMMEDIATE`/`user_version` mechanism, so it is atomic and idempotent.
- Nested `job` command follows the `cmd_*` pattern; key and profile checked before any network call.
- One INSERT at the end of the flow; parameterized queries; excluded jobs trigger no scoring call.
- Verdict derived in Python; constants at the top of the module.

### Deviations

- None that were reported. The failures above are against the spec, not justified deviations.

### Justified Deviations

- The index is created in the same transaction as the table instead of as a separate statement. This is fine and slightly safer.

---

# Security

- No meaningful concerns beyond the Minor item on error text containing fragments of model replies.

---

# Performance

- No concerns.

---

# Error Handling

- Transient `LLMError` is converted into stored `failed` rows (Issue 2).
- Other paths (missing key, no profile, corrupt profile, file errors) are handled and exit 1 as specified.

---

# Testing

## Existing Tests

- `pytest`: 27 passed (includes M0/M1 tests and the new schema, length, evidence, filter, verdict and two end-to-end tests).

## Missing Tests

- See Issue 6 for the full list.

## Failed Tests

- None.

---

# What Was Done Correctly

> Do NOT change these during fixes.

- Schema step and `init_db` integration, including the idempotency test.
- Extraction and scoring models, prompts, JSON cleanup, single retry, and profile-item validation.
- `derive_verdict` thresholds and the constants block.
- `process_job` structure (extraction, verification, filtering, scoring, one insert) and the rule that excluded jobs skip scoring.
- Experience, pay and unpaid-phrase value-vs-snippet checks (apart from the digit-boundary Minor item).
- `format_job_inspect` never prints `raw_text`; CLI error-to-exit-code pattern.

---

# Required Changes

- [ ] Fix filter order so disallowed cities with "India" in the snippet are excluded (Issue 1)
- [ ] Stop storing transient `LLMError` as `failed`; propagate it (Issue 2)
- [ ] Evidence-check the `other_region` exclusion and reset unverified remote fields (Issue 3)
- [ ] Store and print the exclusion snippet explicitly for every excluded job (Issue 4)
- [ ] Accept LLM-normalized cities supported by an alias in the snippet (Issue 5)
- [ ] Write the missing tests, with regression tests for Issues 1-5 (Issue 6)
- [ ] Make `ruff check .` pass (Issue 7)
- [ ] Update the README; address Minor items where cheap

---

# Final Assessment

**Status:** CHANGES MADE, REVIEW WAS DONE

**Summary:** The structure matches the architecture and the happy path works, but the deterministic filter, which is the part meant to be trustworthy, lets out-of-scope cities through, can exclude good remote jobs on a hallucinated field, and the error handling stores outages as data. The tests are too thin to have caught any of it.

**Blocking Issues:** 1 Critical, 6 Important

**Recommendation:** Fix Issues 1-5 first (small, local changes in `jobs.py`), add the missing tests and regression tests, make `ruff` clean, update the README, then run `pytest`, `ruff check .` and a manual `job paste` on 10-15 real postings (include a "City, State, India" posting for a disallowed city) before final verification.
