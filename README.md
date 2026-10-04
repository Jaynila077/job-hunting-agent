# Job Hunting Agent

A personal AI agent that finds relevant new AI/ML/Data jobs, scores how well each one fits my profile, remembers what it has shown me, and tracks my decisions (saved, rejected, applied, interviewing).

It is **advisory only**: it never applies to jobs or decides for me.

> Status: M0 (setup) done. Scoring, dashboard and job fetching come in later milestones. Project context and decisions live in `.ai/PROJECT.md`.

## Setup (Windows PowerShell)

Requires [Miniconda](https://docs.conda.io/en/latest/miniconda.html).

1. Create and activate the environment (Python 3.11):

   ```powershell
   conda env create -f environment.yml
   conda activate jobagent
   ```

2. Create your local settings file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edit `.env` if you want to change a default. It is ignored by Git. Never commit it.

3. Create the database:

   ```powershell
   python -m jobagent init-db
   ```

## Run

```powershell
python -m jobagent info      # show paths, log level, and whether private/ is ignored by Git
python -m jobagent init-db   # create/update the SQLite database (safe to run again)
```

Note: on a fresh clone, `info` may say `Private ignored: no` until `private/` exists. Running `init-db` creates it and the message goes away.

## Test and lint

```powershell
pytest
ruff check .
```

## Private data

Everything personal (resume, database, logs) lives in the `private/` folder, which is ignored by Git. The repository is public, so never put personal data or API keys anywhere else.

## Folder map

| Path | Purpose |
|------|---------|
| `jobagent/` | The application code (`config.py`, `db.py`, `log.py`, `__main__.py`) |
| `tests/` | Tests |
| `private/` | My resume, database and logs (not in Git) |
| `.ai/` | Project context, task, architecture and review files for the AI workflow |
| `tools/` | Helper scripts |
| `environment.yml`, `requirements.txt` | Environment and dependencies |
| `.env.example` | Template for the local `.env` settings |
