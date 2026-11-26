#!/usr/bin/env python3
"""Command guard for supervisor sessions: a PreToolUse hook (matcher "*") that fails closed.

The supervisor runs with bypassPermissions, so this hook is the only fence on its tools.
No shell is ever invoked: the command is checked for metacharacters, split with shlex and
matched against exact tables. Deny = exit 2 plus one stderr line; allow = exit 0, no output.

Tables: {"programs": [absolute paths], "tools": [names], "main": [rule, ...], "<agent_type>": [...]}.
The main session (no agent_type in the hook input) uses "main"; an agent type without a table
is denied; main, programs and tools are reserved and never valid agent types. The built-in
DEFAULT_MAIN and DEFAULT_TOOLS are used unless the tables file (env AGENTS_SUP_GUARD_TABLES,
JSON) defines them. The file must be owned by the uid and not group/world-writable; an
unreadable or invalid file denies everything. Any tool outside "tools" is denied.

Rule: {"argv": [...], "flags": {...}, "args": [...], "required": [...], "chat": bool}
  argv      tokens that must equal the start of the command. argv[0] containing "/" must be
            listed in "programs"; any other first token containing "/" or "=" is denied.
            Bare interpreters (sh, bash, env, python*, ...) are refused as a program.
  flags     allowed flags after the prefix: name -> null (switch) or a class its value must
            match, given as "--f v" or "--f=v". Unlisted flags (and "--") are denied.
  args      positional classes in order. Suffix "?" = optional, "*" = zero or more,
            "+" = one or more (a "*"/"+" class takes all remaining positionals).
            Default: no positionals. Positionals and flag values may not start with "-".
  required  flags that must be present.
  chat      only with a valid chat token. at sup instruct|start-pack|pause-pack|order|cap and
            any "at sup answer ... --owner" need it whatever the table says.
Classes: any (free text), task-id [A-Z][A-Z0-9]*-[0-9]+, name [a-z0-9][a-z0-9-]*, int [0-9]+,
pr-ref (digits, or a ref with no ":" and no leading "~", "/" or "."), format (any without %G).

The command must equal shlex.join of its own parse: single quotes only, one space between
tokens, so bash sees no glob, tilde, history or other parse differential. Max 8 KB.

Chat token: file <sup dir>/_tokens/<AGENTS_SUP_CHAT_TOKEN>, mode 0600 in a 0700 directory, owned
by the uid, JSON {"session_id": ..., "expires": epoch}; check_chat_token(session_id) checks it.

The launcher must start the session with launcher_env(os.environ): GIT_CONFIG_COUNT overrides
(core.fsmonitor=false, log.showSignature=false, gpg.program=/bin/false, core.hooksPath=/dev/null),
GIT_CONFIG_NOSYSTEM=1, GIT_DIR, GIT_EXTERNAL_DIFF, GH_HOST, GH_REPO and PYTHONPATH removed, PATH pinned.
"""
import json
import os
import re
import shlex
import stat
import sys
import time

CLASSES = {
    "any": re.compile(r".+", re.S),
    "task-id": re.compile(r"[A-Z][A-Z0-9]*-[0-9]+"),
    "name": re.compile(r"[a-z0-9][a-z0-9-]*"),
    "int": re.compile(r"[0-9]+"),
    "pr-ref": re.compile(r"[0-9]+|[A-Za-z0-9_@%+,=^][A-Za-z0-9_@%+,=^~./-]*"),
    "format": re.compile(r"(?!.*%G).+", re.S),
}
DEFAULT_TOOLS = ["Bash", "Agent", "AskUserQuestion", "Read", "Glob", "Grep"]
RESERVED = {"main", "programs", "tools"}
CHAT_PREFIXES = [f"at sup {c}".split() for c in ("instruct", "start-pack", "pause-pack", "order", "cap")]
INTERPRETERS = re.compile(
    r"(sh|bash|dash|zsh|ksh|fish|csh|tcsh|env|xargs|sudo|doas|nice|nohup|timeout|time|exec|command|"
    r"busybox|awk|gawk|sed|perl|ruby|node|php|lua|expect|find|su|setsid|stdbuf|strace|watch|script|"
    r"ssh|pwsh|python[0-9.]*)")
META = set("&;|<>`$(){}\\")
TOKEN_RE = re.compile(r"[a-f0-9]{16,64}")
CTRL = re.compile(r"[\x00-\x1f\x7f]")
MAX_LEN = 8192


def _r(argv, flags=None, args=(), required=(), chat=False):
    return {"argv": argv.split(), "flags": flags or {}, "args": list(args),
            "required": list(required), "chat": chat}


DEFAULT_MAIN = [
    _r("at sup status", {"--json": None}), _r("at sup board"),
    _r("at sup queue", {"--json": None}),
    _r("at sup inbox", args=["task-id"]), _r("at sup ready", args=["task-id"]),
    _r("at sup answer", args=["task-id", "any+"]),
    _r("at sup start-worker", args=["task-id"]),
    _r("at sup stop-worker", {"--stuck": None}, ["task-id"]),
    _r("at sup pack", args=["name", "task-id+"]),
    _r("at sup land", {"--dry-run": None}, ["task-id"]),
    _r("at sup worktree", args=["task-id"]),
    _r("at sup op", args=["name", "any+"]), _r("at sup measure", args=["name"]),
    _r("at lease take", {"--ttl": "int", "--for": "task-id", "--reason": "any", "--restore": None},
       ["name"], required=["--ttl"]),
    _r("at lease release", args=["name"]), _r("at lease list", {"--json": None}),
    _r("at run-guard status", {"--all": None}),
    _r("claude agents", {"--json": None, "--all": None}, required=["--json"]),
    _r("git status", {"--short": None, "--porcelain": None}),
    _r("git log", {"--oneline": None, "-n": "int", "--format": "format"}, ["pr-ref?"]),
    _r("git branch --show-current"), _r("git branch --list"),
    _r("git worktree list", {"--porcelain": None}),
    _r("git rev-parse", {"--short": None, "--abbrev-ref": None}, ["pr-ref?"]),
    _r("git diff --stat", args=["pr-ref?", "pr-ref?"]),
    _r("gh pr view", {"--json": "any"}, ["pr-ref"]),
    _r("gh pr list", {"--json": "any", "--state": "name", "--limit": "int"}),
    _r("gh pr checks", args=["pr-ref"]),
    # chat only: a tick has no token
    _r("at sup instruct", args=["any+"], chat=True),
    _r("at sup answer", {"--owner": None}, ["task-id", "any+"], chat=True),
    _r("at sup start-pack", args=["name"], chat=True),
    _r("at sup pause-pack", args=["name"], chat=True),
    _r("at sup order", args=["name", "task-id+"], chat=True), _r("at sup cap", args=["int"], chat=True),
]


def sup_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.environ.get("AGENTS_SUP_DIR") or os.path.join(base, "agents-template", "sup")


def check_chat_token(session_id):
    """True when AGENTS_SUP_CHAT_TOKEN names a private, unexpired token file of this chat session."""
    try:
        tok = os.environ.get("AGENTS_SUP_CHAT_TOKEN", "")
        d = os.path.join(sup_dir(), "_tokens")
        ds = os.lstat(d)
        if not (TOKEN_RE.fullmatch(tok) and session_id and stat.S_ISDIR(ds.st_mode)
                and ds.st_uid == os.getuid() and stat.S_IMODE(ds.st_mode) == 0o700):
            return False
        fd = os.open(os.path.join(d, tok), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as f:
            fs = os.fstat(f.fileno())
            if not (stat.S_ISREG(fs.st_mode) and fs.st_uid == os.getuid()
                    and stat.S_IMODE(fs.st_mode) == 0o600):
                return False
            data = json.load(f)
        return data["session_id"] == session_id and float(data["expires"]) > time.time()
    except Exception:
        return False


def launcher_env(base):
    """Environment the launcher gives a supervisor session so allowed git/gh commands run no code."""
    env = {k: v for k, v in base.items() if k not in
           ("GIT_DIR", "GIT_EXTERNAL_DIFF", "GH_HOST", "GH_REPO", "PYTHONPATH")}
    conf = [("core.fsmonitor", "false"), ("log.showSignature", "false"),
            ("gpg.program", "/bin/false"), ("core.hooksPath", "/dev/null")]
    env.update(GIT_CONFIG_COUNT=str(len(conf)), GIT_CONFIG_NOSYSTEM="1", PATH="/usr/local/bin:/usr/bin:/bin")
    for i, (k, v) in enumerate(conf):
        env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"] = k, v
    return env


def _ok(cls, value):
    return not value.startswith("-") and bool(CLASSES[cls].fullmatch(value))


def match(rule, argv):
    """True when argv after the rule's prefix fits its flags and positionals."""
    rest = argv[len(rule["argv"]):]
    flags, seen, pos, i = rule["flags"], set(), [], 0
    while i < len(rest):
        tok = rest[i]
        i += 1
        if not tok.startswith("-"):
            pos.append(tok)
            continue
        name, eq, val = tok.partition("=")
        if name not in flags or name in seen:
            return False
        seen.add(name)
        cls = flags[name]
        if cls is None:
            if eq:
                return False
            continue
        if not eq:
            if i >= len(rest):
                return False
            val = rest[i]
            i += 1
        if not _ok(cls, val):
            return False
    if not set(rule["required"]) <= seen:
        return False
    for spec in rule["args"]:
        base, mod = (spec[:-1], spec[-1]) if spec[-1] in "?*+" else (spec, "")
        if mod in ("*", "+"):
            if (mod == "+" and not pos) or not all(_ok(base, p) for p in pos):
                return False
            pos = []
        elif pos and _ok(base, pos[0]):
            pos.pop(0)
        elif mod != "?" or pos:
            return False
    return not pos


def decide(command, agent_type, tables, session_id=None):
    """Return (allowed, reason). Pure apart from the chat-token file check."""
    if not isinstance(command, str):
        return False, "command is not a string"
    if len(command.encode("utf-8", "replace")) > MAX_LEN:
        return False, "command too long"
    if any(c in META or ord(c) < 32 or ord(c) == 127 for c in command):
        return False, "shell metacharacter or control character"
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return False, "unparsable quoting"
    if not argv:
        return False, "empty command"
    if shlex.join(argv) != command:
        return False, "non-canonical quoting (single quotes, one space between tokens)"
    if "=" in argv[0]:
        return False, "environment prefix"
    if "/" in argv[0] and argv[0] not in tables.get("programs", []):
        return False, "program path not listed"
    if agent_type in RESERVED:
        return False, "reserved agent_type"
    key = agent_type or "main"
    rules = tables.get(key)
    if not isinstance(rules, list):
        return False, f"no table for {key}"
    for rule in rules:
        if argv[:len(rule["argv"])] == rule["argv"] and match(rule, argv):
            chat = (rule.get("chat") or argv[:3] in CHAT_PREFIXES
                    or (argv[:3] == ["at", "sup", "answer"] and "--owner" in argv))
            if chat and not check_chat_token(session_id):
                return False, "chat only"
            return True, "matched " + " ".join(rule["argv"])
    return False, "no rule matches"


def log(session, agent, allowed, reason, command):
    try:
        fields = [time.strftime("%Y-%m-%dT%H:%M:%S%z"), str(session), agent,
                  "allow" if allowed else "deny", reason, str(command)[:300]]
        line = "\t".join(CTRL.sub(" ", f) for f in fields)
        os.makedirs(sup_dir(), exist_ok=True)
        fd = os.open(os.path.join(sup_dir(), "_guard.log"), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def validate(t):
    """Raise ValueError unless the tables are well formed; fill rule defaults."""
    progs, tools = t.get("programs", []), t.get("tools", [])
    if not (isinstance(progs, list) and all(isinstance(p, str) and os.path.isabs(p) for p in progs)):
        raise ValueError("programs must be absolute paths")
    if not (isinstance(tools, list) and all(isinstance(x, str) for x in tools)):
        raise ValueError("tools must be a list of names")
    for key, rules in t.items():
        if key in ("programs", "tools"):
            continue
        for r in rules:
            argv = r["argv"]
            if not (isinstance(argv, list) and argv and all(isinstance(x, str) and x for x in argv)):
                raise ValueError("bad argv")
            if INTERPRETERS.fullmatch(os.path.basename(argv[0])):
                raise ValueError("interpreter as program")
            r.setdefault("flags", {})
            r.setdefault("args", [])
            r.setdefault("required", [])
            if not (all(v is None or v in CLASSES for v in r["flags"].values())
                    and all(a.rstrip("?*+") in CLASSES for a in r["args"])):
                raise ValueError("unknown class")


def load_tables():
    tables = {"main": DEFAULT_MAIN, "tools": DEFAULT_TOOLS}
    path = os.environ.get("AGENTS_SUP_GUARD_TABLES")
    if path:
        with open(path) as f:
            st = os.fstat(f.fileno())
            if st.st_uid != os.getuid() or st.st_mode & 0o022:
                raise ValueError("tables file not private")
            extra = json.load(f)
        if not isinstance(extra, dict):
            raise ValueError("tables file is not an object")
        validate(extra)
        tables.update(extra)
    return tables


def deny_exit(reason):
    try:
        print(f"sup-guard: denied: {reason}", file=sys.stderr)
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(2)


def main():
    session, agent, command, allowed, reason = "", "main", "", False, "internal error"
    try:
        data = json.load(sys.stdin)
        session = data.get("session_id", "")
        raw_agent, tool = data.get("agent_type"), data.get("tool_name")
        tables = load_tables()
        if raw_agent is not None and (not isinstance(raw_agent, str) or not raw_agent):
            reason = "bad agent_type"
        elif raw_agent in RESERVED:
            reason = "reserved agent_type"
        elif tool not in tables["tools"]:
            reason = "tool not allowed"
        elif tool != "Bash":
            allowed, reason = True, "tool allowed"
        else:
            agent = raw_agent or "main"
            command = data["tool_input"]["command"]
            allowed, reason = decide(command, raw_agent, tables, session)
    except Exception as e:
        allowed, reason = False, f"fail closed: {type(e).__name__}"
    log(session, agent, allowed, reason, command)
    if not allowed:
        deny_exit(reason)
    sys.exit(0)


if __name__ == "__main__":
    main()
