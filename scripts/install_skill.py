#!/usr/bin/env python3
"""Install an independently validated runtime copy without replacing a skill."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Importing the validator must not add a cache to a packaged installation.
sys.dont_write_bytecode = True
from validate_skill import (  # noqa: E402
    NAME, RUNTIME_DIRS, RUNTIME_TOP_FILES, is_cache, is_link,
    validate_package, validate_skill,
)


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return Path(codex_home).expanduser() / "skills" if codex_home else Path.home() / ".codex" / "skills"


def _overlap(first: Path, second: Path) -> bool:
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def _copy_runtime(source: Path, stage: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        return {name for name in names if is_cache(Path(directory) / name)}

    for name in RUNTIME_TOP_FILES:
        shutil.copyfile(source / name, stage / name)
    for name in RUNTIME_DIRS:
        shutil.copytree(source / name, stage / name, ignore=ignore, symlinks=True)


def _cleanup_stage(stage: Path, skills_dir: Path, identity: tuple[int, int]) -> None:
    """Remove only the unchanged temporary directory created by this call."""
    if not os.path.lexists(stage):
        return
    if stage.parent.resolve() != skills_dir or not stage.name.startswith(f".{NAME}-stage-"):
        raise RuntimeError(f"refusing to clean an unexpected staging path: {stage}")
    if is_link(stage) or stage.resolve().parent != skills_dir:
        raise RuntimeError(f"refusing to follow a replaced staging path: {stage}")
    current = stage.stat()
    if (current.st_dev, current.st_ino) != identity:
        raise RuntimeError(f"refusing to clean a replaced staging directory: {stage}")
    shutil.rmtree(stage)


def _promote_stage(stage: Path, target: Path) -> None:
    if os.name == "nt":
        # Windows rename refuses an existing destination, including a directory.
        stage.rename(target)
        return
    # POSIX rename may replace an existing empty directory. Claim the name
    # exclusively first, so only our own empty reservation can be replaced.
    target.mkdir()
    reserved = target.stat()
    try:
        stage.rename(target)
    except BaseException:
        if target.exists() and not is_link(target):
            current = target.stat()
            if (current.st_dev, current.st_ino) == (reserved.st_dev, reserved.st_ino):
                try:
                    target.rmdir()  # Never recursively remove a destination.
                except OSError:
                    pass
        raise


def install_skill(source: str | Path, skills_dir: str | Path) -> Path:
    source_input = Path(source).expanduser()
    skills_path = Path(skills_dir).expanduser().resolve()
    source_path = source_input.resolve()
    target = skills_path / NAME
    # Check both the literal install path and any existing resolved target.
    if _overlap(source_path, target) or _overlap(source_path, target.resolve()):
        raise ValueError("source and installation target overlap")
    if os.path.lexists(target):
        raise FileExistsError(f"installation target already exists; preserved: {target}")
    errors = validate_skill(source_input)
    if errors:
        raise ValueError("invalid source skill:\n" + "\n".join(errors))

    skills_path.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{NAME}-stage-", dir=skills_path))
    initial = stage.stat()
    identity = (initial.st_dev, initial.st_ino)
    try:
        _copy_runtime(source_path, stage)
        errors = validate_package(stage)
        if errors:
            raise ValueError("invalid staged runtime package:\n" + "\n".join(errors))
        if os.path.lexists(target):
            raise FileExistsError(f"installation target appeared during staging; preserved: {target}")
        _promote_stage(stage, target)
        errors = validate_package(target)
        if errors:
            raise RuntimeError(f"installed copy needs inspection at {target}:\n" + "\n".join(errors))
        return target
    finally:
        _cleanup_stage(stage, skills_path, identity)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skills-dir", type=Path, default=default_skills_dir())
    args = parser.parse_args()
    try:
        target = install_skill(args.source, args.skills_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Installed ${NAME}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
