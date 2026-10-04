import argparse
import subprocess
import sys

from jobagent.config import load_settings
from jobagent.db import connect, init_db
from jobagent.log import setup_logging


def check_git_ignored(path_to_check, repo_root) -> str:
    """Checks whether path_to_check is ignored by git."""
    try:
        res = subprocess.run(
            ["git", "check-ignore", "-q", str(path_to_check)],
            cwd=str(repo_root),
            capture_output=True,
            check=False,
        )
        return "yes" if res.returncode == 0 else "no"
    except (FileNotFoundError, PermissionError):
        return "unknown"


def cmd_info(_args) -> int:
    try:
        settings = load_settings()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    git_ignored = check_git_ignored(settings.private_dir, settings.repo_root)

    print(f"Repo root:         {settings.repo_root}")
    print(f"Private directory: {settings.private_dir}")
    print(f"Database path:     {settings.db_path}")
    print(f"Log level:         {settings.log_level}")
    print(f"Private ignored:   {git_ignored}")

    if git_ignored == "no":
        print(
            "WARNING: The private directory is NOT ignored by Git. Check your .gitignore!",
            file=sys.stderr,
        )
    return 0


def cmd_init_db(_args) -> int:
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jobagent",
        description="Personal AI Job Hunt Agent",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("info", help="Display environment and path configuration")
    subparsers.add_parser("init-db", help="Initialize SQLite database and run pending schema steps")

    args = parser.parse_args()

    if args.command == "info":
        sys.exit(cmd_info(args))
    elif args.command == "init-db":
        sys.exit(cmd_init_db(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()