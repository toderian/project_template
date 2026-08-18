#!/usr/bin/env python3
"""One-off: playbooks/skills/<bucket>/<name>.md -> plugins/<plugin>/skills/<name>/SKILL.md
Usage: convert_playbook.py <plugin> <name> [<name>...]     (reads MAPPING below for pack)
"""
import json, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LIB = json.loads((ROOT / ".agents/skill-library.json").read_text())
PACK_OF = {s: pack for pack, v in LIB["packs"].items() for s in v["skills"]}
REWRITES = [   # (regex, replacement) applied to body text
    (r"`?playbooks/conventions/todo-convention\.md`?", "the `task-ledger` skill (references/todo-convention.md)"),
    (r"`?playbooks/conventions/inbox-convention\.md`?", "the `task-ledger` skill (references/inbox-convention.md)"),
    (r"`?playbooks/conventions/task-system-quickstart\.md`?", "the `task-ledger` skill"),
    (r"`?playbooks/conventions/knowledge-base-quickstart\.md`?", "the `knowledge-base` skill"),
    (r"`?playbooks/conventions/runbook-convention\.md`?", "the `knowledge-base` skill (references/runbook-convention.md)"),
    (r"`?playbooks/conventions/adr-convention\.md`?", "the `knowledge-base` skill (references/adr-convention.md)"),
    (r"`?playbooks/conventions/generated-artifacts\.md`?", "the `knowledge-base` skill (references/generated-artifacts.md)"),
    (r"`?playbooks/conventions/workbook-convention\.md`?", "the `workbook` skill"),
    (r"`?playbooks/conventions/autonomy-levels\.md`?", "the `git-discipline` skill (references/autonomy-levels.md)"),
    (r"`?playbooks/conventions/plan-critique\.md`?", "the `planning-workflow` skill (references/plan-critique.md)"),
    (r"`?playbooks/conventions/vertical-slicing\.md`?", "the `prd-to-plan` skill (references/vertical-slicing.md)"),
    (r"`?playbooks/conventions/test-taxonomy\.md`?", "the `tdd` skill (references/test-taxonomy.md)"),
    (r"`?playbooks/conventions/connectors-and-mcp\.md`?", "the `connectors-and-mcp` skill"),
    (r"`?playbooks/conventions/agent-loop-recipes\.md`?", "the `subagent-protocol` skill (references/agent-loop-recipes.md)"),
    (r"`?playbooks/conventions/prompt-orchestration\.md`?", "the `subagent-protocol` skill (references/prompt-orchestration.md)"),
    (r"`?playbooks/personalities/(\w+)\.md`?", r"the `\1` personality (subagent-protocol skill, references/personalities/\1.md)"),
    (r"`?_base/scripts/sync-todo-ledgers\.sh`?", "`at ledger`"),
    (r"`?_base/scripts/reserve-work-item\.sh`?", "`at reserve`"),
    (r"`?_base/scripts/check-repos-config\.sh`?", "`at repos-check`"),
    (r"`?_base/scripts/check-template-update\.sh`?", "`at doctor`"),
    (r"`?playbooks/skills/\w+/([\w-]+)\.md`?", r"the `\1` skill"),
    (r"`?playbooks/skills/\w+/([\w-]+)/([\w./-]+)`?", r"`\1` skill references/\2"),
    (r"`?playbooks/templates/([\w.-]+)`?", r"assets/\1"),
    (r"wants Codex to ", "wants to "), (r"Codex should ", "the agent should "),
]
def convert(plugin: str, name: str) -> None:
    src = next(ROOT.glob(f"playbooks/skills/*/{name}.md"))
    dst_dir = ROOT / "plugins" / plugin / "skills" / name
    dst_dir.mkdir(parents=True, exist_ok=True)
    text = src.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    fm, body = m.group(1), m.group(2)
    for pat, rep in REWRITES:
        body = re.sub(pat, rep, body)
    fm = re.sub(r"wants Codex to ", "wants to ", fm)
    fm += f"\nmetadata:\n  source: {src.relative_to(ROOT)}\n  pack: {PACK_OF.get(name, 'core')}"
    (dst_dir / "SKILL.md").write_text(f"---\n{fm}\n---\n{body}")
    side = src.with_suffix("")
    if side.is_dir():
        ref = dst_dir / "references"; ref.mkdir(exist_ok=True)
        for f in side.iterdir(): shutil.copy2(f, ref / f.name)
    print(f"{src.relative_to(ROOT)} -> {dst_dir.relative_to(ROOT)}")
if __name__ == "__main__":
    plugin, *names = sys.argv[1:]
    for n in names: convert(plugin, n)
