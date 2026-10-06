import argparse
import subprocess
import sys
from pathlib import Path

from jobagent.config import load_settings
from jobagent.db import connect, init_db
from jobagent.embed import embed_texts
from jobagent.llm import LLMError, call_llm
from jobagent.log import setup_logging
from jobagent.profile import (
    build_profile,
    format_profile_inspect,
    get_latest_profile_envelope,
)


def check_git_ignored(private_dir: Path, repo_root: Path) -> str:
    probe_path = private_dir / ".probe"
    try:
        res = subprocess.run(
            ["git", "check-ignore", "-q", str(probe_path)],
            cwd=str(repo_root),
            capture_output=True,
            check=False,
        )
        if res.returncode == 0:
            return "yes"
        if res.returncode == 1:
            return "no"
        return "unknown"
    except (FileNotFoundError, PermissionError):
        return "unknown"


def cmd_info(_args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    git_ignored = check_git_ignored(settings.private_dir, settings.repo_root)
    resume_exists = "yes" if settings.resume_path.is_file() else "no"
    key_status = "set" if settings.groq_api_key else "missing"

    print(f"Repo root:         {settings.repo_root}")
    print(f"Private directory: {settings.private_dir}")
    print(f"Database path:     {settings.db_path}")
    print(f"Resume path:       {settings.resume_path} (exists: {resume_exists})")
    print(f"LLM model:         {settings.llm_model} (LLM key: {key_status})")
    print(f"Embedding model:   {settings.embed_model}")
    print(f"Log level:         {settings.log_level}")
    print(f"Private ignored:   {git_ignored}")

    if git_ignored == "no":
        print(
            "WARNING: The private directory is NOT ignored by Git. Check your .gitignore!",
            file=sys.stderr,
        )
    return 0


def cmd_init_db(_args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    setup_logging(settings.log_level)
    try:
        conn = connect(settings.db_path)
        version = init_db(conn)
        conn.close()
        print(f"Database initialized at {settings.db_path} (user_version = {version})")
        return 0
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        return 1


def cmd_profile_build(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    setup_logging(settings.log_level)

    if not settings.groq_api_key:
        print("Error: GROQ_API_KEY is not configured in environment or .env", file=sys.stderr)
        return 1

    if not settings.resume_path.is_file():
        print(f"Error: Resume file not found at {settings.resume_path}", file=sys.stderr)
        return 1

    def llm_caller(sys_p: str, usr_p: str) -> str:
        return call_llm(
            system_prompt=sys_p,
            user_prompt=usr_p,
            api_key=settings.groq_api_key or "",
            model=settings.llm_model,
        )

    print(f"Building profile from {settings.resume_path}...")
    try:
        version, out_path, warnings, is_new = build_profile(
            pdf_path=settings.resume_path,
            profile_dir=settings.profile_dir,
            model_cache_dir=settings.model_cache_dir,
            llm_caller=llm_caller,
            embedder=embed_texts,
            llm_model=settings.llm_model,
            embed_model=settings.embed_model,
            force=args.force,
        )
        if not is_new:
            print(f"profile unchanged (v{version:04d})")
            return 0

        print(f"Profile built successfully: v{version:04d} -> {out_path}")
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f" - {w}")
        return 0
    except (LLMError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_profile_inspect(_args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        envelope = get_latest_profile_envelope(settings.profile_dir)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if envelope is None:
        print(
            "No profile found. Run 'python -m jobagent profile build' first.",
            file=sys.stderr,
        )
        return 1

    print(format_profile_inspect(envelope, current_pdf=settings.resume_path))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jobagent",
        description="Personal AI Job Hunt Agent",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("info", help="Display environment and path configuration")
    subparsers.add_parser("init-db", help="Initialize SQLite database and run pending schema steps")

    profile_parser = subparsers.add_parser("profile", help="Manage resume profile model")
    profile_subs = profile_parser.add_subparsers(dest="subcommand")

    build_parser = profile_subs.add_parser(
        "build", help="Extract and build profile from resume PDF")
    build_parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if resume is unchanged",
    )
    profile_subs.add_parser("inspect", help="Display current structured profile")

    args = parser.parse_args()

    if args.command == "info":
        sys.exit(cmd_info(args))
    elif args.command == "init-db":
        sys.exit(cmd_init_db(args))
    elif args.command == "profile":
        if args.subcommand == "build":
            sys.exit(cmd_profile_build(args))
        elif args.subcommand == "inspect":
            sys.exit(cmd_profile_inspect(args))
        else:
            profile_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()