#!/usr/bin/env python3
"""Validate this project's small metadata schema, files and portable links.

This is deliberately not a general YAML or Markdown parser. Development caches
are ignored normally; --package rejects them in a distributable runtime tree.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

NAME = "campus-relations"
UPSTREAM = "https://github.com/shengjidaguai-china/goutoujunshi"
RUNTIME_DIRS = ("agents", "references", "scripts")
RUNTIME_TOP_FILES = ("SKILL.md", "LICENSE", "NOTICE.md")
REQUIRED_FILES = (
    *RUNTIME_TOP_FILES,
    "agents/openai.yaml",
    "references/practical/teacher-relations.md",
    "references/practical/peer-relations.md",
    "references/practical/repair-and-boundaries.md",
    "references/practical/conversation-playbook.md",
    "references/practical/chat-analysis.md",
    "references/practical/social-calibration.md",
    "references/practical/campus-romance.md",
    "references/knowledge/evidence.md",
    "scripts/validate_skill.py",
    "scripts/install_skill.py",
)
PROJECT_FILES = ("README.md", "docs/provenance.md", "tests/scenarios.md", "tests/fusion-scenarios.md", "tests/test_tooling.py")
CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache"}
CACHE_SUFFIXES = {".pyc", ".pyo"}
FORBIDDEN_DIRS = {".git", "node_modules"}
MAX_ENTRY_BYTES = 16_000
MAX_REFERENCE_BYTES = 40_000
MAX_RUNTIME_BYTES = 160_000


def is_link(path: Path) -> bool:
    """Include Windows junctions/reparse points without following them."""
    return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)


def is_cache(path: Path) -> bool:
    return path.name in CACHE_DIRS or path.suffix.lower() in CACHE_SUFFIXES


def _walk(directory: Path, errors: list[str], strict: bool) -> list[Path]:
    files: list[Path] = []
    pending = [directory]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name)
            for child in children:
                if is_link(child):
                    errors.append(f"symlink or reparse point is not allowed: {child}")
                elif is_cache(child):
                    if strict:
                        errors.append(f"cache is not allowed in a runtime package: {child}")
                elif child.is_dir():
                    if child.name in FORBIDDEN_DIRS:
                        errors.append(f"non-runtime directory is not allowed: {child}")
                    else:
                        pending.append(child)
                elif child.is_file():
                    files.append(child)
                else:
                    errors.append(f"unsupported filesystem entry: {child}")
        except OSError as exc:
            errors.append(f"cannot inspect {current}: {exc}")
    return files


def _read(path: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (UnicodeError, OSError) as exc:
        errors.append(f"file must be readable UTF-8: {path}: {exc}")
        return None


def _scalar(value: str) -> str:
    if value.startswith('"'):
        parsed = json.loads(value)
        if not isinstance(parsed, str):
            raise ValueError("expected a string")
        return parsed
    if not value or value[0] in "'|>{[*&!@`#%" or ": " in value or " #" in value:
        raise ValueError("expected a plain or double-quoted one-line string")
    if value.startswith(("- ", "? ", ": ")):
        raise ValueError("plain metadata must not contain YAML structure")
    return value


def _metadata(skill: str, agent: str, errors: list[str]) -> None:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", skill, re.DOTALL)
    fields: dict[str, str] = {}
    try:
        if not match:
            raise ValueError("SKILL.md must start with --- frontmatter")
        for line in match.group(1).splitlines():
            found = re.fullmatch(r"(name|description):\s*(.+)", line)
            if not found or found[1] in fields:
                raise ValueError("frontmatter accepts exactly name and description once each")
            fields[found[1]] = _scalar(found[2])
        if set(fields) != {"name", "description"}:
            raise ValueError("frontmatter requires name and description")
        if fields["name"] != NAME:
            raise ValueError(f"skill name must be {NAME}")
        if not fields["description"].strip() or len(fields["description"]) > 1024:
            raise ValueError("description must be nonempty and at most 1024 characters")
        if "<" in fields["description"] or ">" in fields["description"]:
            raise ValueError("description must not contain angle brackets")
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid SKILL.md metadata: {exc}")

    interface: dict[str, str] = {}
    try:
        lines = [line for line in agent.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        if not lines or lines[0] != "interface:":
            raise ValueError("metadata must start with interface:")
        for line in lines[1:]:
            found = re.fullmatch(r'  (display_name|short_description|default_prompt):\s*(".*")', line)
            if not found or found[1] in interface:
                raise ValueError("interface requires three unique double-quoted strings")
            value = json.loads(found[2])
            if not isinstance(value, str) or not value.strip():
                raise ValueError("interface values must be nonempty strings")
            interface[found[1]] = value
        if set(interface) != {"display_name", "short_description", "default_prompt"}:
            raise ValueError("interface requires display_name, short_description and default_prompt")
        if not 25 <= len(interface["short_description"]) <= 64:
            raise ValueError("short_description must contain 25 to 64 characters")
        calls = re.findall(r"\$([a-z0-9-]+)", interface["default_prompt"])
        if not calls or set(calls) != {NAME}:
            raise ValueError(f"default_prompt must call only ${NAME}")
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid agents/openai.yaml metadata: {exc}")


def _markdown_targets(content: str):
    fence: str | None = None
    for line in content.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        for match in re.finditer(r"!?\[[^\]\r\n]*\]\(([^)\r\n]+)\)", line):
            value = match[1].strip()
            if value.startswith("<") and ">" in value:
                yield value[1:value.index(">")]
            else:
                yield value.split(maxsplit=1)[0]
        definition = re.match(r"^ {0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", line)
        if definition:
            yield definition[1].strip("<>")


def _links(root: Path, path: Path, content: str, errors: list[str]) -> None:
    for target in _markdown_targets(content):
        try:
            parts = urlsplit(html.unescape(target))
            if parts.scheme.lower() in {"http", "https", "mailto"}:
                continue
            if parts.scheme or parts.netloc:
                raise ValueError("unsupported local-link scheme")
            decoded = parts.path
            for _ in range(8):
                next_value = unquote(decoded, errors="strict")
                if next_value == decoded:
                    break
                decoded = next_value
            else:
                raise ValueError("excessively encoded local-link path")
            if not decoded:
                continue
            decoded = decoded.replace("\\", "/")
            if re.match(r"^[A-Za-z]:", decoded) or decoded.startswith("//"):
                raise ValueError("absolute platform path is not portable")
            resolved = (path.parent / decoded).resolve()
            if not resolved.is_relative_to(root):
                raise ValueError("local link resolves outside skill directory")
            if not resolved.exists():
                raise ValueError("local link target is missing")
        except (ValueError, UnicodeError, OSError) as exc:
            errors.append(f"invalid local Markdown link in {path.relative_to(root)}: {target!r}: {exc}")


def _validate(root: str | Path, project: bool, strict: bool) -> list[str]:
    errors: list[str] = []
    supplied = Path(root).expanduser()
    try:
        if is_link(supplied):
            return [f"skill root must not be a symlink or reparse point: {supplied}"]
        root_path = supplied.resolve()
        if not root_path.is_dir():
            return [f"skill root is not a directory: {root_path}"]
    except OSError as exc:
        return [f"cannot inspect skill root: {exc}"]

    for relative in REQUIRED_FILES + (PROJECT_FILES if project else ()):
        required = root_path / relative
        if not required.is_file():
            errors.append(f"missing required file: {relative}")

    runtime: list[Path] = []
    for relative in RUNTIME_TOP_FILES + RUNTIME_DIRS:
        entry = root_path / relative
        if not entry.exists() and not entry.is_symlink():
            continue
        try:
            if is_link(entry):
                errors.append(f"symlink or reparse point is not allowed: {entry}")
            elif relative in RUNTIME_DIRS:
                if entry.is_dir():
                    runtime.extend(_walk(entry, errors, strict))
                else:
                    errors.append(f"runtime path must be a directory: {relative}")
            elif entry.is_file():
                runtime.append(entry)
        except OSError as exc:
            errors.append(f"cannot inspect {entry}: {exc}")

    texts: dict[Path, str] = {}
    total = 0
    for path in runtime:
        try:
            size = path.stat().st_size
            total += size
            if path.name == "SKILL.md" and path.parent == root_path and size > MAX_ENTRY_BYTES:
                errors.append(f"SKILL.md exceeds {MAX_ENTRY_BYTES} bytes")
            if path.is_relative_to(root_path / "references") and size > MAX_REFERENCE_BYTES:
                errors.append(f"reference exceeds {MAX_REFERENCE_BYTES} bytes: {path.relative_to(root_path)}")
            if re.search(r"\.(?:sqlite3?|db)(?:-(?:wal|shm|journal))?$", path.name, re.IGNORECASE):
                errors.append(f"database is not allowed in runtime: {path.relative_to(root_path)}")
                continue
            if size > MAX_RUNTIME_BYTES:
                errors.append(f"runtime file is too large: {path.relative_to(root_path)}")
                continue
            with path.open("rb") as handle:
                if handle.read(16) == b"SQLite format 3\x00":
                    errors.append(f"SQLite database is not allowed in runtime: {path.relative_to(root_path)}")
                    continue
            text = _read(path, errors)
            if text is not None:
                texts[path] = text
        except OSError as exc:
            errors.append(f"cannot read {path}: {exc}")
    if total > MAX_RUNTIME_BYTES:
        errors.append(f"runtime files exceed {MAX_RUNTIME_BYTES} bytes: {total}")

    if project:
        extras = [root_path / "README.md"]
        for directory in (root_path / "docs", root_path / "tests"):
            if directory.is_dir() and not is_link(directory):
                extras.extend(_walk(directory, errors, False))
            else:
                errors.append(f"project directory is missing or unsafe: {directory.name}")
        for path in extras:
            if path.is_file() and not is_link(path):
                text = _read(path, errors)
                if text is not None:
                    texts[path] = text
            elif path.is_symlink():
                errors.append(f"symlink is not allowed in project files: {path}")

    skill = texts.get(root_path / "SKILL.md")
    agent = texts.get(root_path / "agents/openai.yaml")
    if skill is not None and agent is not None:
        _metadata(skill, agent, errors)
    license_text = texts.get(root_path / "LICENSE", "")
    for marker in ("MIT License", "Copyright (c) 2026 powerycy", "Permission is hereby granted", 'THE SOFTWARE IS PROVIDED "AS IS"'):
        if marker not in license_text:
            errors.append(f"LICENSE must retain upstream MIT notice: {marker}")
    if UPSTREAM not in texts.get(root_path / "NOTICE.md", ""):
        errors.append("NOTICE.md must identify the upstream repository")
    for path, text in texts.items():
        if path.suffix.lower() == ".md":
            _links(root_path, path, text, errors)
    return errors


def validate_skill(root: str | Path, project: bool = False) -> list[str]:
    return _validate(root, project, strict=False)


def validate_package(root: str | Path) -> list[str]:
    return _validate(root, project=False, strict=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--project", action="store_true", help="also check development documents and tests")
    modes.add_argument("--package", action="store_true", help="reject caches in a runtime package")
    args = parser.parse_args()
    errors = validate_package(args.root) if args.package else validate_skill(args.root, args.project)
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"{NAME} validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
