"""Exercise packaging boundaries and failure paths using temporary fixtures."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from install_skill import default_skills_dir, install_skill  # noqa: E402
from validate_skill import validate_package, validate_skill  # noqa: E402


def fixture(root: Path) -> Path:
    files = {
        "SKILL.md": "---\nname: campus-relations\ndescription: 帮大学生沟通\n---\n\n# 测试技能\n\n[资料](references/practical/teacher-relations.md)\n",
        "agents/openai.yaml": "interface:\n" + "".join(
            f"  {key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in {
                "display_name": "校园关系·测试",
                "short_description": "帮助大学生维护师生与同学关系，提供自然沟通话术和可执行的小行动",
                "default_prompt": "使用 $campus-relations 帮我整理沟通。",
            }.items()
        ),
        "references/practical/teacher-relations.md": "# 师生\n\n[依据](../knowledge/evidence.md)\n",
        "references/practical/peer-relations.md": "# 同学\n",
        "references/practical/repair-and-boundaries.md": "# 修复\n",
        "references/practical/conversation-playbook.md": "# 话术\n",
        "references/practical/chat-analysis.md": "# 聊天材料\n",
        "references/practical/social-calibration.md": "# 社交校准\n",
        "references/practical/campus-romance.md": "# 校园恋爱\n",
        "references/knowledge/evidence.md": "# 依据\n\n[外部来源](https://example.org/paper)\n",
        "NOTICE.md": "来源 https://github.com/shengjidaguai-china/goutoujunshi\n\n[许可](LICENSE)\n",
        "README.md": "# 项目\n\n[入口](SKILL.md)\n",
        "docs/provenance.md": "# 来源\n\n[入口](../SKILL.md)\n",
        "tests/scenarios.md": "# 场景\n",
        "tests/fusion-scenarios.md": "# 融合场景\n",
        "tests/test_tooling.py": "# temporary fixture only\n",
    }
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    shutil.copyfile(PROJECT / "LICENSE", root / "LICENSE")
    (root / "scripts").mkdir()
    for name in ("validate_skill.py", "install_skill.py"):
        shutil.copyfile(PROJECT / "scripts" / name, root / "scripts" / name)
    return root


class ToolingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = fixture(self.base / "source")
        self.skills = self.base / "skills"

    def add_link(self, target: str) -> None:
        path = self.source / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + f"\n[link]({target})\n", encoding="utf-8")

    def test_valid_runtime_and_project_with_unicode_metadata(self) -> None:
        self.assertEqual(validate_skill(self.source), [])
        self.assertEqual(validate_skill(self.source, project=True), [])

    def test_missing_reference_fails(self) -> None:
        (self.source / "references/practical/teacher-relations.md").unlink()
        errors = validate_skill(self.source)
        self.assertTrue(any("missing required file" in error for error in errors))
        self.assertTrue(any("link target is missing" in error for error in errors))

    def test_plain_and_encoded_paths_cannot_escape_root(self) -> None:
        (self.base / "outside.md").write_text("outside", encoding="utf-8")
        path = self.source / "SKILL.md"
        original = path.read_text(encoding="utf-8")
        for target in ("../outside.md", "..%2Foutside.md", "%252e%252e%252foutside.md", "..\\outside.md"):
            with self.subTest(target=target):
                path.write_text(original, encoding="utf-8")
                self.add_link(target)
                self.assertTrue(any("outside skill directory" in error for error in validate_skill(self.source)))

    def test_default_prompt_must_match_name(self) -> None:
        path = self.source / "agents/openai.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("$campus-relations", "$goutoujunshi"), encoding="utf-8")
        self.assertTrue(any("default_prompt" in error for error in validate_skill(self.source)))

    def test_structural_yaml_values_are_rejected(self) -> None:
        path = self.source / "SKILL.md"
        original = path.read_text(encoding="utf-8")
        for value in ("*alias", "&anchor text", "!tag text", "@reserved", "`code`", "# comment", "nested: mapping"):
            with self.subTest(value=value):
                path.write_text(original.replace("description: 帮大学生沟通", f"description: {value}"), encoding="utf-8")
                self.assertTrue(any("invalid SKILL.md metadata" in error for error in validate_skill(self.source)))

    def test_utf8_and_database_content_are_checked(self) -> None:
        reference = self.source / "references/practical/peer-relations.md"
        reference.write_bytes(b"\xff\xfe")
        self.assertTrue(any("UTF-8" in error for error in validate_skill(self.source)))
        reference.write_bytes(b"SQLite format 3\x00" + b"\x00" * 20)
        self.assertTrue(any("SQLite database" in error for error in validate_skill(self.source)))

    def test_source_cache_is_ignored_and_excluded_from_package(self) -> None:
        cache = self.source / "scripts/__pycache__"
        cache.mkdir()
        (cache / "unrelated.pyc").write_bytes(b"bytecode")
        (self.source / "scripts/old.pyc").write_bytes(b"bytecode")
        self.assertEqual(validate_skill(self.source), [])
        self.assertTrue(any("cache" in error for error in validate_package(self.source)))
        target = install_skill(self.source, self.skills)
        self.assertFalse((target / "scripts/__pycache__").exists())
        self.assertFalse((target / "scripts/old.pyc").exists())
        self.assertEqual(validate_package(target), [])

    def test_install_copies_only_runtime_and_keeps_links_valid(self) -> None:
        target = install_skill(self.source, self.skills)
        self.assertEqual(target, self.skills / "campus-relations")
        self.assertEqual(validate_package(target), [])
        self.assertEqual({path.name for path in target.iterdir()}, {"SKILL.md", "LICENSE", "NOTICE.md", "agents", "references", "scripts"})
        self.assertFalse((target / "README.md").exists())
        self.assertFalse((target / "docs").exists())
        self.assertFalse((target / "tests").exists())
        self.assertTrue((self.source / "docs/provenance.md").exists())

    def test_existing_installation_is_preserved(self) -> None:
        target = install_skill(self.source, self.skills)
        sentinel = target / "sentinel.txt"
        sentinel.write_bytes(b"keep this installation")
        with self.assertRaises(FileExistsError):
            install_skill(self.source, self.skills)
        self.assertEqual(sentinel.read_bytes(), b"keep this installation")
        self.assertFalse(list(self.skills.glob(".campus-relations-stage-*")))

    def test_source_and_target_overlap_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            install_skill(self.source, self.source / "skills")
        self.assertFalse((self.source / "skills").exists())

    def test_stage_failure_cleans_only_its_own_temporary_directory(self) -> None:
        self.add_link("docs/provenance.md")
        self.assertEqual(validate_skill(self.source), [])
        self.skills.mkdir()
        existing = self.skills / ".campus-relations-stage-someone-else"
        existing.mkdir()
        (existing / "sentinel").write_text("preserve", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "staged runtime package"):
            install_skill(self.source, self.skills)
        self.assertEqual(list(self.skills.iterdir()), [existing])
        self.assertEqual((existing / "sentinel").read_text(encoding="utf-8"), "preserve")

    def test_copy_failure_cleans_stage(self) -> None:
        with patch("install_skill._copy_runtime", side_effect=OSError("simulated copy failure")):
            with self.assertRaisesRegex(OSError, "simulated copy failure"):
                install_skill(self.source, self.skills)
        self.assertFalse(list(self.skills.iterdir()))

    def test_symlink_and_broken_existing_target_are_rejected(self) -> None:
        self.skills.mkdir()
        target = self.skills / "campus-relations"
        try:
            target.symlink_to(self.base / "does-not-exist", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable on this host: {exc}")
        with self.assertRaises(FileExistsError):
            install_skill(self.source, self.skills)
        self.assertTrue(target.is_symlink())
        target.unlink()
        link = self.source / "references/linked.md"
        link.symlink_to(self.source / "references/knowledge/evidence.md")
        self.assertTrue(any("symlink" in error for error in validate_skill(self.source)))

    def test_default_destination_uses_codex_home(self) -> None:
        with patch.dict(os.environ, {"CODEX_HOME": str(self.base / "custom-home")}):
            self.assertEqual(default_skills_dir(), self.base / "custom-home/skills")


if __name__ == "__main__":
    unittest.main()
