#!/usr/bin/env python3
"""Synchronize active skill manifests and runtime wrappers.

The durable source is:
- .agents/skill-library.json: every selectable skill and pack
- .agents/skills.enabled.json: the active profile/packs/extra skills

Generated runtime surfaces are:
- .claude-plugin/plugin.json
- skills/<bucket>/<name>/SKILL.md
- .claude/skills/<bucket>/<name>/SKILL.md
- .agents/skills/<bucket>/<name>/SKILL.md
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BUCKETS = ("engineering", "productivity", "misc", "personal")
PLUGIN_NAME = "project-template-skills"


@dataclass(frozen=True)
class Skill:
    name: str
    bucket: str
    description: str
    argument_hint: str | None
    kind: str

    @property
    def runtime_path(self) -> str:
        return f"./skills/{self.bucket}/{self.name}"

    @property
    def playbook_path(self) -> str:
        return f"playbooks/skills/{self.bucket}/{self.name}.md"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"missing required file: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc


def dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=False) + "\n"


def library_paths(root: Path) -> tuple[Path, Path]:
    return root / ".agents" / "skill-library.json", root / ".agents" / "skills.enabled.json"


def load_library(root: Path) -> tuple[dict[str, Any], dict[str, Skill]]:
    library_path, _ = library_paths(root)
    library = load_json(library_path)

    raw_skills = library.get("skills")
    if not isinstance(raw_skills, dict):
        raise SystemExit(f"{library_path} must contain an object at skills")

    skills: dict[str, Skill] = {}
    for name, raw in raw_skills.items():
        if not isinstance(raw, dict):
            raise SystemExit(f"{library_path}: skills.{name} must be an object")
        bucket = raw.get("bucket")
        description = raw.get("description")
        if bucket not in BUCKETS:
            raise SystemExit(f"{library_path}: skills.{name}.bucket must be one of {', '.join(BUCKETS)}")
        if not isinstance(description, str) or not description:
            raise SystemExit(f"{library_path}: skills.{name}.description must be a non-empty string")
        argument_hint = raw.get("argument_hint")
        if argument_hint is not None and not isinstance(argument_hint, str):
            raise SystemExit(f"{library_path}: skills.{name}.argument_hint must be a string")
        kind = raw.get("kind", "skill")
        if kind not in {"skill", "agent-role"}:
            raise SystemExit(f"{library_path}: skills.{name}.kind must be skill or agent-role")
        skills[name] = Skill(
            name=name,
            bucket=bucket,
            description=description,
            argument_hint=argument_hint,
            kind=kind,
        )

    validate_library(root, library, skills)
    return library, skills


def validate_library(root: Path, library: dict[str, Any], skills: dict[str, Skill]) -> None:
    packs = library.get("packs")
    profiles = library.get("profiles")
    if not isinstance(packs, dict) or not packs:
        raise SystemExit(".agents/skill-library.json must contain a non-empty packs object")
    if not isinstance(profiles, dict) or not profiles:
        raise SystemExit(".agents/skill-library.json must contain a non-empty profiles object")

    for pack_name, pack in packs.items():
        if not isinstance(pack, dict):
            raise SystemExit(f"pack {pack_name} must be an object")
        pack_skills = pack.get("skills")
        if not isinstance(pack_skills, list):
            raise SystemExit(f"pack {pack_name} must contain a skills list")
        for skill_name in pack_skills:
            if skill_name not in skills:
                raise SystemExit(f"pack {pack_name} references unknown skill {skill_name}")
            if skills[skill_name].kind != "skill":
                raise SystemExit(f"pack {pack_name} references non-invocable skill {skill_name}")

    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            raise SystemExit(f"profile {profile_name} must be an object")
        profile_packs = profile.get("packs")
        if not isinstance(profile_packs, list):
            raise SystemExit(f"profile {profile_name} must contain a packs list")
        for pack_name in profile_packs:
            if pack_name not in packs:
                raise SystemExit(f"profile {profile_name} references unknown pack {pack_name}")

    for skill in skills.values():
        if skill.kind == "agent-role":
            continue
        playbook = root / skill.playbook_path
        if not playbook.exists():
            raise SystemExit(f"library skill {skill.name} is missing playbook {skill.playbook_path}")


def load_selection(root: Path) -> dict[str, Any]:
    _, selection_path = library_paths(root)
    selection = load_json(selection_path)
    if selection.get("version") != 1:
        raise SystemExit(f"{selection_path} must contain version 1")
    return selection


def selection_from_profile(library: dict[str, Any], profile: str) -> dict[str, Any]:
    profiles = library["profiles"]
    if profile not in profiles:
        raise SystemExit(f"unknown skills profile {profile!r}; choose one of {', '.join(sorted(profiles))}")
    return {
        "version": 1,
        "profile": profile,
        "packs": list(profiles[profile]["packs"]),
        "skills": [],
    }


def normalize_name_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def resolve_active(library: dict[str, Any], skills: dict[str, Skill], selection: dict[str, Any]) -> list[Skill]:
    profile = selection.get("profile")
    packs = selection.get("packs")
    extra_skills = selection.get("skills", [])

    if not isinstance(extra_skills, list):
        raise SystemExit(".agents/skills.enabled.json skills must be a list")

    if packs is None:
        if not isinstance(profile, str):
            raise SystemExit(".agents/skills.enabled.json must set packs or a profile")
        packs = library["profiles"][profile]["packs"]
    if not isinstance(packs, list):
        raise SystemExit(".agents/skills.enabled.json packs must be a list")

    active_names: set[str] = set()
    for pack_name in packs:
        if pack_name not in library["packs"]:
            raise SystemExit(f"unknown enabled skill pack {pack_name!r}")
        active_names.update(library["packs"][pack_name]["skills"])

    for skill_name in extra_skills:
        if skill_name not in skills:
            raise SystemExit(f"unknown explicitly enabled skill {skill_name!r}")
        active_names.add(skill_name)

    active: list[Skill] = []
    for name in sorted(active_names, key=lambda n: (skills[n].bucket, n)):
        skill = skills[name]
        if skill.kind != "skill":
            raise SystemExit(f"{name} is {skill.kind}, not an invocable skill")
        active.append(skill)
    return active


def generated_manifest(active: list[Skill]) -> dict[str, Any]:
    return {
        "name": PLUGIN_NAME,
        "description": (
            "Active skills shared across Claude Code and Codex by this project template. "
            "Generated from .agents/skills.enabled.json and .agents/skill-library.json; "
            "inactive library skills are not exposed to agents."
        ),
        "skills": [skill.runtime_path for skill in active],
    }


def yaml_string(value: str) -> str:
    return json.dumps(value.replace("\n", " "), ensure_ascii=True)


def title_for(name: str) -> str:
    special = {"tdd": "TDD", "ui": "UI", "prd": "PRD", "owasp": "OWASP"}
    words = []
    for word in name.split("-"):
        words.append(special.get(word, word.capitalize()))
    return " ".join(words)


def frontmatter(skill: Skill, *, claude: bool) -> str:
    lines = [
        "---",
        f"name: {skill.name}",
        f"description: {yaml_string(skill.description)}",
    ]
    if skill.argument_hint:
        lines.append(f"argument-hint: {yaml_string(skill.argument_hint)}")
    if claude:
        lines.append("disable-model-invocation: true")
    lines.append("---")
    return "\n".join(lines)


def wrapper_body(skill: Skill, *, title: bool, antigravity: bool) -> str:
    heading = f"\n# {title_for(skill.name)}\n" if title else ""
    suffix = (
        "This Antigravity wrapper is generated from `.agents/skills.enabled.json`.\n"
        "Keep Antigravity support experimental and isolated; update the shared playbook first.\n"
        if antigravity
        else "Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.\n"
    )
    return (
        f"{heading}\n"
        "Read and follow:\n\n"
        f"- `{skill.playbook_path}`\n\n"
        f"{suffix}"
    )


def codex_wrapper(skill: Skill) -> str:
    return f"{frontmatter(skill, claude=False)}\n{wrapper_body(skill, title=True, antigravity=False)}"


def claude_wrapper(skill: Skill) -> str:
    return f"{frontmatter(skill, claude=True)}\n{wrapper_body(skill, title=False, antigravity=False)}"


def antigravity_wrapper(skill: Skill) -> str:
    return f"{frontmatter(skill, claude=False)}\n{wrapper_body(skill, title=False, antigravity=True)}"


def expected_files(root: Path, active: list[Skill]) -> dict[Path, str]:
    expected: dict[Path, str] = {}
    for skill in active:
        rel = Path(skill.bucket) / skill.name / "SKILL.md"
        expected[root / "skills" / rel] = codex_wrapper(skill)
        expected[root / ".claude" / "skills" / rel] = claude_wrapper(skill)
        expected[root / ".agents" / "skills" / rel] = antigravity_wrapper(skill)
    expected[root / ".claude-plugin" / "plugin.json"] = dump_json(generated_manifest(active))
    return expected


def managed_runtime_dirs(root: Path, skills: dict[str, Skill]) -> list[Path]:
    dirs: list[Path] = []
    for skill in skills.values():
        for base in (root / "skills", root / ".claude" / "skills", root / ".agents" / "skills"):
            dirs.append(base / skill.bucket / skill.name)
    return dirs


def check_sync(root: Path, active: list[Skill], skills: dict[str, Skill]) -> list[str]:
    findings: list[str] = []
    expected = expected_files(root, active)

    for path, content in expected.items():
        if not path.exists():
            findings.append(f"missing {path.relative_to(root)}")
        elif path.read_text() != content:
            findings.append(f"drift {path.relative_to(root)}")

    active_dirs = {path.parent for path in expected if path.name == "SKILL.md"}
    for path in managed_runtime_dirs(root, skills):
        if path.exists() and path not in active_dirs:
            findings.append(f"inactive runtime wrapper present {path.relative_to(root)}")

    return findings


def write_sync(root: Path, active: list[Skill], skills: dict[str, Skill]) -> None:
    expected = expected_files(root, active)
    active_dirs = {path.parent for path in expected if path.name == "SKILL.md"}

    for path in managed_runtime_dirs(root, skills):
        if path.exists() and path not in active_dirs:
            shutil.rmtree(path)

    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text() != content:
            path.write_text(content)

    for base in (root / "skills", root / ".claude" / "skills", root / ".agents" / "skills"):
        if not base.exists():
            continue
        for path in sorted((p for p in base.rglob("*") if p.is_dir()), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass


def write_selection(root: Path, selection: dict[str, Any]) -> None:
    _, selection_path = library_paths(root)
    selection_path.write_text(dump_json(selection))


def print_list(library: dict[str, Any], skills: dict[str, Skill]) -> None:
    print("Profiles:")
    for name, profile in sorted(library["profiles"].items()):
        packs = ", ".join(profile["packs"])
        print(f"  {name}: {packs}")
        print(f"    {profile.get('description', '')}")

    print("\nPacks:")
    for name, pack in sorted(library["packs"].items()):
        print(f"  {name}: {len(pack['skills'])} skills")
        print(f"    {pack.get('description', '')}")
        print(f"    {', '.join(pack['skills'])}")

    agent_roles = sorted(name for name, skill in skills.items() if skill.kind == "agent-role")
    if agent_roles:
        print("\nAgent roles, not invocable skills:")
        print(f"  {', '.join(agent_roles)}")


def prompt_interactive(library: dict[str, Any]) -> dict[str, Any]:
    if not sys.stdin.isatty():
        raise SystemExit("--interactive requires a TTY")

    profiles = sorted(library["profiles"])
    print("Skill profiles:")
    for idx, name in enumerate(profiles, 1):
        profile = library["profiles"][name]
        print(f"  {idx}. {name}: {profile.get('description', '')}")
        print(f"     packs: {', '.join(profile['packs'])}")
    print(f"  {len(profiles) + 1}. custom packs")

    choice = input("Choose skill profile [recommended]: ").strip()
    if not choice:
        return selection_from_profile(library, "recommended")

    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(profiles):
            return selection_from_profile(library, profiles[index - 1])
        if index == len(profiles) + 1:
            return prompt_custom_packs(library)
        raise SystemExit(f"invalid profile choice: {choice}")

    if choice in library["profiles"]:
        return selection_from_profile(library, choice)
    if choice == "custom":
        return prompt_custom_packs(library)
    raise SystemExit(f"unknown profile: {choice}")


def prompt_custom_packs(library: dict[str, Any]) -> dict[str, Any]:
    print("\nAvailable packs:")
    for name, pack in sorted(library["packs"].items()):
        print(f"  {name}: {pack.get('description', '')}")
    raw = input("Comma-separated packs to activate: ").strip()
    packs = normalize_name_list(raw)
    for pack in packs:
        if pack not in library["packs"]:
            raise SystemExit(f"unknown pack: {pack}")
    return {
        "version": 1,
        "profile": "custom",
        "packs": packs,
        "skills": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated files without writing")
    parser.add_argument("--sync", action="store_true", help="write generated manifest and runtime wrappers")
    parser.add_argument("--list", action="store_true", help="list profiles, packs, and library skills")
    parser.add_argument("--interactive", action="store_true", help="prompt for a profile or custom packs")
    parser.add_argument("--profile", help="activate a named profile")
    parser.add_argument("--packs", help="activate comma-separated packs and mark selection custom")
    parser.add_argument("--skills", help="activate comma-separated individual skills in addition to packs")
    args = parser.parse_args()

    root = repo_root()
    library, skills = load_library(root)

    if args.list:
        print_list(library, skills)
        return 0

    selection_changed = False
    if args.interactive:
        selection = prompt_interactive(library)
        selection_changed = True
    elif args.profile:
        selection = selection_from_profile(library, args.profile)
        selection_changed = True
    elif args.packs is not None or args.skills is not None:
        packs = normalize_name_list(args.packs)
        extra_skills = normalize_name_list(args.skills)
        for pack in packs:
            if pack not in library["packs"]:
                raise SystemExit(f"unknown pack: {pack}")
        for skill in extra_skills:
            if skill not in skills:
                raise SystemExit(f"unknown skill: {skill}")
        selection = {
            "version": 1,
            "profile": "custom",
            "packs": packs,
            "skills": extra_skills,
        }
        selection_changed = True
    else:
        selection = load_selection(root)

    if selection_changed:
        write_selection(root, selection)

    active = resolve_active(library, skills, selection)

    if args.check:
        findings = check_sync(root, active, skills)
        if findings:
            print("Skill selection generated files are out of sync:")
            for finding in findings:
                print(f"- {finding}")
            return 1
        print(f"OK  skill selection current ({len(active)} active skills)")
        return 0

    if args.sync or selection_changed:
        write_sync(root, active, skills)
        print(f"Synchronized {len(active)} active skills from .agents/skills.enabled.json")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
