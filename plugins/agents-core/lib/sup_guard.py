#!/usr/bin/env python3
"""Command guard for supervisor sessions: a PreToolUse hook (matcher "*") that fails closed.

The supervisor runs with bypassPermissions, so this hook is the only fence on its tools.
No shell is ever invoked: the command is checked for metacharacters, split with shlex and
matched against exact tables. Deny = exit 2 plus one stderr line; allow = exit 0, no output.

Trust model: a worker session runs under the same uid as the state directory, so nothing here fences a
worker. This guard, the chat token and `require_chat` stop only the guarded supervisor (a tick or the chat
session) and honest mistakes.

Tables: {"programs": [absolute paths], "<agent_type>": [rule, ...]}. The main session uses the built-in
DEFAULT_MAIN and the tools in DEFAULT_TOOLS. Its hook input has no agent_type, or, when it was started with
`--agent <profile>-supervisor` (the launcher does), agent_type equal to `<AGENTS_SUPERVISOR>-supervisor`; both mean
the main table. `<profile>-adviser` and `<profile>-operator` use their own tables; the tables file may not define
"main" or "tools". An agent type without a table is denied; main, programs and tools are reserved and never
valid agent types. The file (env AGENTS_SUP_GUARD_TABLES, JSON) must be a regular file owned by the uid and not
group/world-writable; an unreadable or invalid file denies everything. Any tool outside DEFAULT_TOOLS is denied.
DEFAULT_MAIN holds only `at sup ...` commands and `at lease list`: no git, gh or claude.

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
  chat      only with a valid chat token. Every command in CHAT_PREFIXES and any
            "at sup answer ... --owner" need it whatever the table says.
Classes: any (free text), task-id [A-Z][A-Z0-9]*-[0-9]+, q-id Q[0-9]+, name [a-z0-9][a-z0-9-]*, int [0-9]+,
profile (only the value of AGENTS_SUPERVISOR).

The command must equal shlex.join of its own parse: single quotes only, one space between
tokens, so bash sees no glob, tilde, history or other parse differential. Max 8 KB.

Chat token: file <sup dir>/_tokens/<AGENTS_SUP_CHAT_TOKEN>, mode 0600 in a 0700 directory, owned
by the uid, JSON {"session_id": ..., "expires": epoch}; check_chat_token(session_id) checks it. `at sup chat`
writes it and starts claude with `--session-id <that id>`; sup_ask.require_chat uses the same check.

The launcher must start the session with launcher_env(os.environ): GIT_CONFIG_COUNT overrides
(core.fsmonitor=false, log.showSignature=false, gpg.program=/bin/false, core.hooksPath=/dev/null),
GIT_CONFIG_NOSYSTEM=1, GIT_DIR, GIT_EXTERNAL_DIFF, GH_HOST, GH_REPO and PYTHONPATH removed, PATH rebuilt from the directories of at, claude, git, gh, python3
and jq plus /usr/bin:/bin, minus any directory under `deny_under` (the hub and its worktrees). The incoming
PATH is kept in AGENTS_SUP_ORIG_PATH so workers and the watcher can be started with the owner's PATH again.
"""
import json
import os
import re
import shlex
import shutil
import stat
import sys
import time

CLASSES = {
    "any": re.compile(r".+", re.S),
    "task-id": re.compile(r"[A-Z][A-Z0-9]*-[0-9]+"),
    "name": re.compile(r"[a-z0-9][a-z0-9-]*"),
    "q-id": re.compile(r"Q[0-9]+"),
    "int": re.compile(r"[0-9]+"),
    "profile": re.compile(r".+"),  # checked against AGENTS_SUPERVISOR in _ok
}
DEFAULT_TOOLS = ["Bash", "Agent", "AskUserQuestion", "Read", "Glob", "Grep"]
RESERVED = {"main", "programs", "tools"}
# Commands only the owner's chat (or plain shell) may run; `answer --owner` is checked in decide. `at sup` calls
# require_chat for the same list. Of these only the first group is in DEFAULT_MAIN: init and watch start|stop are the owner's shell.
CHAT_COMMANDS = ("instruct", "pack", "start-pack", "pause-pack", "close-pack", "order", "cap", "watch start",
                 "watch stop", "init")
CHAT_PREFIXES = [f"at sup {c}".split() for c in CHAT_COMMANDS]
INTERPRETERS = re.compile(
    r"(sh|bash|dash|zsh|ksh|fish|csh|tcsh|env|xargs|sudo|doas|nice|nohup|timeout|time|exec|command|"
    r"busybox|awk|gawk|sed|perl|ruby|node|php|lua|expect|find|su|setsid|stdbuf|strace|watch|script|"
    r"ssh|pwsh|python[0-9.]*)")
META = set("&;|<>`$(){}\\")
QUOTED_DENY = set("&|<>`$\\{}")  # still refused inside one single-quoted word; `( ) ; "` and the rest are inert there
TOKEN_RE = re.compile(r"[a-f0-9]{16,64}")
CTRL = re.compile(r"[\x00-\x1f\x7f]")
MAX_LEN = 8192
SAFE_RUN = re.compile(r"[A-Za-z0-9@%+=:,./-]+")  # what shlex.quote leaves unquoted
SQUOTE = re.compile(r"'[^']*'")


def _r(argv, flags=None, args=(), required=(), chat=False):
    return {"argv": argv.split(), "flags": flags or {}, "args": list(args),
            "required": list(required), "chat": chat}


PROFILE = {"--profile": "profile"}  # only the supervisor's own profile; the hub is never a flag (profile config)

DEFAULT_MAIN = [
    _r("at sup status", {**PROFILE, "--json": None}), _r("at sup board", PROFILE),
    _r("at sup queue", {**PROFILE, "--json": None, "--all": None}),
    _r("at sup instructions", PROFILE), _r("at sup packs", PROFILE),
    _r("at sup ready", PROFILE, ["task-id"]),
    _r("at sup task", PROFILE, ["task-id"]),
    _r("at sup answer", PROFILE, ["q-id", "any+"]),
    _r("at sup grant", PROFILE, ["task-id", "name"]),
    _r("at sup deny", PROFILE, ["task-id", "name", "any"]),
    _r("at sup escalate", {**PROFILE, "--task": "task-id", "--q": "q-id", "--blocking": None}, ["any+"]),
    _r("at sup start-worker", PROFILE, ["task-id"]),
    _r("at sup stop-worker", PROFILE, ["task-id"]),
    _r("at sup land", {**PROFILE, "--dry-run": None}, ["task-id"]),
    _r("at sup done", PROFILE, ["name"]),
    _r("at sup measure", {**PROFILE, "--json": None, "--since": "any"}),
    _r("at sup watch status", PROFILE),
    _r("at lease list", {"--json": None}),
    # chat only: a tick has no token. `init`, `tick`, `chat`, `watch start|stop|once` and the worker-side
    # ask|need|release|inbox are in no table: the supervisor never runs them.
    _r("at sup instruct", PROFILE, ["any+"], chat=True),
    _r("at sup answer", {**PROFILE, "--owner": None}, ["q-id", "any+"], chat=True),
    _r("at sup pack", {**PROFILE, "--parallel": None}, ["name", "task-id+"], chat=True),
    _r("at sup start-pack", PROFILE, ["name"], chat=True),
    _r("at sup pause-pack", PROFILE, ["name"], chat=True),
    _r("at sup close-pack", PROFILE, ["name"], chat=True),
    _r("at sup order", PROFILE, ["name", "task-id+"], chat=True),
    _r("at sup cap", PROFILE, ["int"], chat=True),
]


def hook_path():
    """Absolute path of hooks/sup-guard.sh; settings files run it as `/bin/bash <path>` so the mode bit does not matter."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks", "sup-guard.sh")


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


TOOL_NAMES = ("at", "claude", "git", "gh", "python3", "jq")


def _safe_path(base, deny_under):
    """PATH for a supervisor session: the absolute directories of the tools it needs, then /usr/bin:/bin.
    A directory under `deny_under` is skipped before the lookup, so a later real tool still wins."""
    denied = [os.path.realpath(d) for d in deny_under or []]
    allowed = [d for d in base.get("PATH", "").split(os.pathsep) if os.path.isabs(d)
               and not any(os.path.realpath(d) == x or os.path.realpath(d).startswith(x + os.sep) for x in denied)]
    dirs = []
    for name in TOOL_NAMES:
        found = shutil.which(name, path=os.pathsep.join(allowed))
        if found and os.path.dirname(found) not in dirs:
            dirs.append(os.path.dirname(found))
    return ":".join([*dirs, *(d for d in ("/usr/bin", "/bin") if d not in dirs)])


def launcher_env(base, deny_under=None):
    """Environment the launcher gives a supervisor session so allowed git/gh commands run no code."""
    env = {k: v for k, v in base.items() if k not in
           ("GIT_DIR", "GIT_EXTERNAL_DIFF", "GH_HOST", "GH_REPO", "PYTHONPATH")}
    conf = [("core.fsmonitor", "false"), ("log.showSignature", "false"),
            ("gpg.program", "/bin/false"), ("core.hooksPath", "/dev/null")]
    env.update(GIT_CONFIG_COUNT=str(len(conf)), GIT_CONFIG_NOSYSTEM="1", PATH=_safe_path(base, deny_under),
               AGENTS_SUP_ORIG_PATH=base.get("AGENTS_SUP_ORIG_PATH") or base.get("PATH", ""))
    for i, (k, v) in enumerate(conf):
        env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"] = k, v
    return env


def _ok(cls, value):
    if cls == "profile":
        return value == os.environ.get("AGENTS_SUPERVISOR") and not value.startswith("-")
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


def _unquoted(command: str):
    """(text outside the quoted words, the words' contents), or None when the command is not made only of unquoted safe
    runs, spaces, single-quoted words `'...'` and the escaped quote `"'"` that shlex.join writes. The shell reads these
    pieces exactly this way, and inside them nothing expands: a single-quoted word ends only at the next single quote."""
    out, inner, i = [], [], 0
    while i < len(command):
        if command[i] == "'":
            m = SQUOTE.match(command, i)
            if not m:
                return None
            inner.append(m.group()[1:-1])
        elif command.startswith("\"'\"", i):
            m = None
            i += 3
            continue
        elif command[i] == " ":
            out.append(" ")
            i += 1
            continue
        else:
            m = SAFE_RUN.match(command, i)
            if not m:
                return None
            out.append(m.group())
        i = m.end()
    return "".join(out), inner


def _control(c: str) -> bool:
    return ord(c) < 32 or 127 <= ord(c) < 160


def decide(command, agent_type, tables, session_id=None):
    """Return (allowed, reason). Pure apart from the chat-token file check."""
    if not isinstance(command, str):
        return False, "command is not a string"
    if len(command.encode("utf-8", "replace")) > MAX_LEN:
        return False, "command too long"
    if any(_control(c) for c in command):
        return False, "shell metacharacter or control character"
    parts = _unquoted(command)
    if parts is None or any(c in META for c in parts[0]) or any(c in QUOTED_DENY for w in parts[1] for c in w):
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
    sup = os.environ.get("AGENTS_SUPERVISOR")
    key = "main" if not agent_type or (sup and agent_type == f"{sup}-supervisor") else agent_type
    rules = tables.get(key)
    if not isinstance(rules, list):
        return False, f"no table for {key}"
    for rule in rules:
        if argv[:len(rule["argv"])] == rule["argv"] and match(rule, argv):
            chat = (rule.get("chat") or any(argv[:len(p)] == p for p in CHAT_PREFIXES)
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
        fd = os.open(os.path.join(sup_dir(), "_guard.log"),
                     os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a") as f:
            if stat.S_ISREG(os.fstat(f.fileno()).st_mode):  # a FIFO or device here must not hang or take the line
                f.write(line + "\n")
    except Exception:
        pass


def validate(t):
    """Raise ValueError unless the tables are well formed; fill rule defaults."""
    progs = t.get("programs", [])
    if not (isinstance(progs, list) and all(isinstance(p, str) and os.path.isabs(p) for p in progs)):
        raise ValueError("programs must be absolute paths")
    if "main" in t or "tools" in t:
        raise ValueError("the tables file may not define main or tools")
    for key, rules in t.items():
        if key == "programs":
            continue
        if not (isinstance(rules, list) and all(isinstance(r, dict) for r in rules)):
            raise ValueError("a table must be a list of rules")
        for r in rules:
            argv = r.get("argv")
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
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)) as f:
            st = os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o022:
                raise ValueError("tables file not a private regular file")
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
    session, agent, command, allowed, reason = "", "main", "", False, "internal error"  # agent: the name both kinds of call log
    try:
        data = json.load(sys.stdin)
        session = data.get("session_id", "")
        raw_agent, tool = data.get("agent_type"), data.get("tool_name")
        agent = raw_agent if isinstance(raw_agent, str) and raw_agent else "main"
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
