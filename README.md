# Job Hunting Agent

A personal AI agent that finds relevant new AI/ML/Data jobs, scores how well each one fits my profile, remembers what it has shown me, and tracks my decisions (saved, rejected, applied, interviewing).

It is **advisory only**: it never applies to jobs or decides for me.

> Status: M0 (setup) and M1 (profile model) done. Job scoring, the dashboard and job fetching come in later milestones. Project context and decisions live in `.ai/PROJECT.md`.

## What works today

- **Profile model:** reads my PDF resume, removes contact details, asks an LLM (Groq) to extract a structured profile, checks that every claim has evidence copied from the resume, creates local embeddings, and saves a versioned profile in `private/profile/`.
- **Inspect:** prints what the agent understood about me, with evidence, and tells me when the resume has changed since the last build.
- **Database:** an empty SQLite database with a schema-version mechanism, ready for later milestones.

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
```

How `profile build` behaves:

- It sends the resume text (contact details removed first) to Groq once, and once more only if the first answer fails validation.
- If the resume, the LLM model and the embedding model are all unchanged since the last build, it does nothing.
- On any failure it writes nothing.
- The first run downloads the embedding model (a one-time download to `private/models/`). Later runs work offline for that step.
- Each build creates a new file, `private/profile/profile-v0001.json`, then `-v0002.json`, and so on. Old versions are never overwritten.

Note: on a fresh clone, `info` may say `Private ignored: no` until `private/` exists. Creating it (for example by running `init-db`) makes the message go away.

## Settings (`.env`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `JOBAGENT_PRIVATE_DIR` | `private` | Folder for all personal data |
| `JOBAGENT_DB_FILE` | `jobagent.db` | SQLite file inside the private folder |
| `JOBAGENT_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `JOBAGENT_RESUME_FILE` | `resume.pdf` | Resume PDF inside the private folder |
| `JOBAGENT_LLM_MODEL` | `openai/gpt-oss-20b` | Groq model used to extract the profile |
| `JOBAGENT_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Local embedding model |
| `GROQ_API_KEY` | none | Groq API key (required for `profile build`) |

Real environment variables win over `.env`; empty values are treated as not set.

## Test and lint

```powershell
pytest
ruff check .
```

Tests never use the network, a real API key, or a real resume.

## Private data and privacy

Everything personal (resume, profile versions, embedding model cache, database, logs) lives in the `private/` folder, which is ignored by Git. The repository is public, so never put personal data or API keys anywhere else.

What leaves your machine: only the resume text with emails, phone numbers and links removed, sent to Groq during `profile build`. Names, employers and institutions are still in that text. Embeddings are computed locally.

## Folder map

| Path | Purpose |
|------|---------|
| `jobagent/config.py` | Settings from `.env` and environment variables |
| `jobagent/db.py` | SQLite connection and schema versioning |
| `jobagent/log.py` | Logging setup |
| `jobagent/llm.py` | One function that calls Groq |
| `jobagent/embed.py` | Local embeddings (`fastembed`) |
| `jobagent/profile.py` | Profile model, redaction, validation, versioned storage, inspect output |
| `jobagent/__main__.py` | Command line (`info`, `init-db`, `profile build`, `profile inspect`) |
| `tests/` | Tests |
| `private/` | My resume, profile versions, database and logs (not in Git) |
| `.ai/` | Project context, task, architecture and review files for the AI workflow |
| `tools/` | Helper scripts |
| `environment.yml`, `requirements.txt` | Environment and dependencies |
| `.env.example` | Template for the local `.env` settings |
