"""Create a local virtual environment for the TwinMind scraper."""

from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from pathlib import Path
from typing import Optional, Sequence


DEFAULT_VENV_DIR = Path(".venv")
REQUIREMENTS_FILE = Path("requirements.txt")


def is_windows_platform(platform: Optional[str] = None) -> bool:
    return (platform or sys.platform).startswith("win")


def venv_python_path(venv_dir: Path, platform: Optional[str] = None) -> Path:
    if is_windows_platform(platform):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def activation_command(venv_dir: Path, platform: Optional[str] = None) -> str:
    if is_windows_platform(platform):
        script = venv_dir / "Scripts" / "Activate.ps1"
        return str(script) if venv_dir.is_absolute() else rf".\{script}"
    return f"source {venv_dir}/bin/activate"


def display_python_command(venv_dir: Path, platform: Optional[str] = None) -> str:
    if is_windows_platform(platform):
        return rf".\{venv_dir}\Scripts\python.exe"
    return f"{venv_dir}/bin/python"


def same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


def running_inside_venv(venv_dir: Path) -> bool:
    return sys.prefix != sys.base_prefix and same_path(Path(sys.prefix), venv_dir)


def should_create_virtualenv(venv_dir: Path, python_path: Path, recreate: bool) -> bool:
    if recreate:
        return True
    return not python_path.exists()


def run_command(command: Sequence[str], cwd: Path) -> None:
    print(f"Running: {' '.join(command)}", flush=True)
    subprocess.check_call(list(command), cwd=str(cwd))


def create_virtualenv(venv_dir: Path) -> None:
    print(f"Creating virtual environment at {venv_dir}", flush=True)
    builder = venv.EnvBuilder(with_pip=True, upgrade_deps=False)
    builder.create(str(venv_dir))


def setup_environment(project_dir: Path, venv_dir: Path, recreate: bool = False) -> Path:
    requirements_path = project_dir / REQUIREMENTS_FILE
    if not requirements_path.exists():
        raise SystemExit(f"Missing {requirements_path}")

    python_path = venv_python_path(venv_dir)
    if recreate and running_inside_venv(venv_dir):
        raise SystemExit(
            "Cannot recreate the virtual environment while it is activated. "
            "Deactivate it first, then run `python setup_venv.py --recreate`."
        )
    if should_create_virtualenv(venv_dir, python_path, recreate):
        create_virtualenv(venv_dir)
    else:
        print(f"Using existing virtual environment at {venv_dir}", flush=True)
    run_command(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--force-reinstall",
            "-r",
            str(requirements_path),
        ],
        cwd=project_dir,
    )
    run_command(
        [str(python_path), "-m", "playwright", "install", "chromium"],
        cwd=project_dir,
    )
    return python_path


def print_next_steps(venv_dir: Path) -> None:
    python_cmd = display_python_command(venv_dir)
    print("", flush=True)
    print("Virtual environment setup complete.", flush=True)
    print("", flush=True)
    print("Activate it:", flush=True)
    print(f"  {activation_command(venv_dir)}", flush=True)
    print("", flush=True)
    print("Then save your TwinMind login session:", flush=True)
    print("  python scrape_twinmind_memories.py --login", flush=True)
    print("", flush=True)
    print("Or run directly without activation:", flush=True)
    print(f"  {python_cmd} scrape_twinmind_memories.py --login", flush=True)
    print(f"  {python_cmd} scrape_twinmind_memories.py --limit 1 --debug", flush=True)
    print(f"  {python_cmd} scrape_twinmind_memories.py --output memories", flush=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a virtual environment for the TwinMind scraper."
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=DEFAULT_VENV_DIR,
        help=f"Virtual environment directory. Default: {DEFAULT_VENV_DIR}",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the virtual environment before installing dependencies.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    project_dir = Path(__file__).resolve().parent
    venv_dir = args.venv
    if not venv_dir.is_absolute():
        venv_dir = project_dir / venv_dir
    setup_environment(project_dir=project_dir, venv_dir=venv_dir, recreate=args.recreate)

    if args.venv.is_absolute() or Path.cwd() != project_dir:
        display_venv_dir = venv_dir
    else:
        display_venv_dir = args.venv
    print_next_steps(display_venv_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
