# Job Hunting Agent

A personal AI agent that finds relevant new AI/ML/Data jobs, scores how well each one fits my profile, remembers what it has shown me, and tracks my decisions (saved, rejected, applied, interviewing).

It is **advisory only**: it never applies to jobs or decides for me.

> Status: M0 (setup), M1 (profile model) and M2 (job analysis and matching) implemented. Saving decisions, the dashboard and job fetching come in later milestones. Project context and decisions live in `.ai/PROJECT.md`.

## What works today

- **Profile model:** reads my PDF resume, removes contact details, asks an LLM (Groq) to extract a structured profile, checks that every claim has evidence copied from the resume, creates local embeddings, and saves a versioned profile in `private/profile/`.
- **Inspect:** prints what the agent understood about me, with evidence, and tells me when the resume has changed since the last build.
- **Job analysis:** paste one job posting and the agent extracts its details, applies simple rules (unpaid, location, experience), scores it 1 to 10 against my profile, and lists what matches, what is missing and why.
- **Inspect jobs:** shows any stored job with its score, matches, gaps, explanation, flags and, for excluded jobs, the reason and the text that caused it.
- **Database:** a SQLite database with a schema-version mechanism and a `jobs` table (added in M2).

## Setup (Windows PowerShell)

Requires [Miniconda](https://docs.conda.io/en/latest/miniconda.html).

1. Create and activate the environment (Python 3.11):

   ```powershell
   conda env create -f environment.yml
   conda activate jobagent
   ```

   If the environment already exists and new dependencies were added, update it with `pip install -r requirements.txt`.

2. Create your local settings file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Open `.env` and set `GROQ_API_KEY`. It is ignored by Git. Never commit it.

3. Put your resume PDF in `private/` and name it `resume.pdf` (or set `JOBAGENT_RESUME_FILE` in `.env` to the file name).

4. Create the database:

   ```powershell
   python -m jobagent init-db
   ```

## Run

```powershell
python -m jobagent info                # paths, models, whether the resume exists, whether the API key is set, and whether private/ is ignored by Git
python -m jobagent init-db             # create/update the SQLite database (safe to run again)
python -m jobagent profile build       # build a new profile version from the resume PDF
python -m jobagent profile build --force   # build a new version even if the resume has not changed
python -m jobagent profile inspect     # show the latest profile and its evidence
python -m jobagent job paste           # analyze a pasted job posting (see below)
python -m jobagent job inspect         # show the most recent job analysis
python -m jobagent job inspect 3       # show job number 3
```

How `profile build` behaves:

- It sends the resume text (contact details removed first) to Groq once, and once more only if the first answer fails validation.
- If the resume, the LLM model and the embedding model are all unchanged since the last build, it does nothing.
- On any failure it writes nothing.
- The first run downloads the embedding model (a one-time download to `private/models/`). Later runs work offline for that step.
- Each build creates a new file, `private/profile/profile-v0001.json`, then `-v0002.json`, and so on. Old versions are never overwritten.

### Analyzing a job (`job paste` and `job inspect`)

`job paste` needs `GROQ_API_KEY` in `.env` and a built profile (`profile build`). It creates the `jobs` table itself, so `init-db` is optional.

Paste the posting text from the keyboard (PowerShell):

```powershell
python -m jobagent job paste
# paste the posting, press Ctrl+Z, then Enter
```

Or read it from a text file, and optionally record where it came from:

```powershell
python -m jobagent job paste --file posting.txt --url https://example.com/job --source "careers page"
```

`--url` and `--source` are only stored as notes. The URL is never opened. The posting must be between 100 and 20,000 characters.

What happens to each posting:

1. **Extract:** one Groq call turns the text into title, company, location, work mode, experience, pay, skills and posting date. Quoted snippets (location, experience, pay) must appear word for word in the pasted text.
2. **Filter:** plain Python rules decide whether to exclude the job. A job is excluded only on verified text:
   - the role is stated as unpaid, or
   - the location is not Pune, Mumbai, Bangalore, Hyderabad or remote (India or worldwide), or
   - the minimum experience is more than 3 years.

   Missing information never excludes a job. It adds a flag such as `pay not stated`, `location not stated` or `experience not stated`.
3. **Score:** jobs that pass get a second Groq call comparing the posting with my profile. The result is a score from 1 to 10, matches (each tied to an item in my profile), gaps and a short explanation. The verdict is set by the score: 7 or more is strong, 5 or 6 is a stretch, below 5 is weak.
4. **Store:** the job and its result are saved as one row in `private/jobagent.db`.

Each job ends with one of three outcomes:

| Outcome | Meaning |
|---------|---------|
| `scored` | Passed the filters and was scored |
| `excluded` | Failed a filter. Kept with the reason, not scored |
| `failed` | The model's answer was invalid after one retry. Kept with the reason |

If the key or profile is missing, the input is empty or too long, or Groq cannot be reached, nothing is stored and the command exits with an error so you can paste again.

`job inspect` reads the database only (no network) and never prints the original posting text. Without a number it shows the latest job. Excluded jobs stay viewable so a good job is never lost silently.

Rules and thresholds (allowed cities, `MAX_YEARS`, `STRONG_MIN`, `STRETCH_MIN`) are constants at the top of `jobagent/jobs.py`. Pasting the same posting twice creates two rows; duplicate handling comes in M3.

Note: on a fresh clone, `info` may say `Private ignored: no` until `private/` exists. Creating it (for example by running `init-db`) makes the message go away.

## Settings (`.env`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `JOBAGENT_PRIVATE_DIR` | `private` | Folder for all personal data |
| `JOBAGENT_DB_FILE` | `jobagent.db` | SQLite file inside the private folder |
| `JOBAGENT_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `JOBAGENT_RESUME_FILE` | `resume.pdf` | Resume PDF inside the private folder |
| `JOBAGENT_LLM_MODEL` | `openai/gpt-oss-20b` | Groq model used to extract the profile and to analyze jobs |
| `JOBAGENT_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Local embedding model |
| `GROQ_API_KEY` | none | Groq API key (required for `profile build` and `job paste`) |

Real environment variables win over `.env`; empty values are treated as not set.

## Test and lint

```powershell
pytest
ruff check .
```

Tests never use the network, a real API key, or a real resume.

## Private data and privacy

Everything personal (resume, profile versions, embedding model cache, database, logs) lives in the `private/` folder, which is ignored by Git. The repository is public, so never put personal data or API keys anywhere else.

What leaves your machine:

- During `profile build`: only the resume text with emails, phone numbers and links removed, sent to Groq. Names, employers and institutions are still in that text.
- During `job paste`: the pasted job posting, plus a compact version of the profile (no contact details, no evidence snippets, no embeddings).

Embeddings are computed locally. Pasted postings are stored in full in `private/jobagent.db`, which is ignored by Git.

## Folder map

| Path | Purpose |
|------|---------|
| `jobagent/config.py` | Settings from `.env` and environment variables |
| `jobagent/db.py` | SQLite connection and schema versioning |
| `jobagent/log.py` | Logging setup |
| `jobagent/llm.py` | One function that calls Groq |
| `jobagent/embed.py` | Local embeddings (`fastembed`) |
| `jobagent/profile.py` | Profile model, redaction, validation, versioned storage, inspect output |
| `jobagent/jobs.py` | Job extraction, filter rules, scoring, storage and inspect output |
| `jobagent/__main__.py` | Command line (`info`, `init-db`, `profile build`, `profile inspect`, `job paste`, `job inspect`) |
| `tests/` | Tests |
| `private/` | My resume, profile versions, database and logs (not in Git) |
| `.ai/` | Project context, task, architecture and review files for the AI workflow |
| `tools/` | Helper scripts |
| `environment.yml`, `requirements.txt` | Environment and dependencies |
| `.env.example` | Template for the local `.env` settings |
