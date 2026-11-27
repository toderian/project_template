#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_topics.py with a fake `claude` that picks its own bg session ids."""
import argparse, io, json, os, subprocess, sys, tempfile, unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import sup_state as st
import sup_topics as tp
import sup_workers as sw

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys, uuid
d, a = os.environ["FAKE_DIR"], sys.argv[1:]
with open(d + "/claude.log", "a") as f:
    f.write(json.dumps({"argv": a, "cwd": os.getcwd(), "topic": os.environ.get("AGENTS_SUP_TOPIC"),
                        "sup": os.environ.get("AGENTS_SUPERVISOR")}) + "\\n")
def rows():
    p = d + "/sessions"
    return [l.split(" ", 1) for l in open(p).read().splitlines()] if os.path.exists(p) else []
def listed(n):
    p = d + "/" + n
    return open(p).read().split() if os.path.exists(p) else []
if "--resume" in a:
    sid = a[a.index("--resume") + 1]
    if os.path.exists(d + "/copy"):
        print("note: session " + sid[:8] + " is already running in the background, so this started a copy as e8ad3784."); sys.exit(0)
    print("note: woke session " + sid[:8] + " with its saved options")
    open(d + "/stopped", "w").write(" ".join(x for x in listed("stopped") if x != sid[:8]))
elif a[:1] == ["--bg"]:
    sid, name = str(uuid.uuid4()), a[a.index("--name") + 1]
    open(d + "/sessions", "a").write(sid + " " + name + "\\n")
    print("backgrounded \\u00b7 " + sid[:8] + " \\u00b7 " + name)
elif a[:1] == ["agents"]:
    print(json.dumps([{"sessionId": s, "name": n, "kind": "background", "startedAt": 0,
                       "pid": None if s[:8] in listed("stopped") else 77,
                       "status": "busy" if s[:8] in listed("busy") else "idle"} for s, n in rows()]))
elif a[:1] == ["stop"]:
    open(d + "/stopped", "a").write(a[1] + " ")
elif a[:1] == ["logs"]:
    print("working...\\n\\x1b[2mTOPIC\\x1b[9Gx\\x1b[17Gdone:\\x1b[0m first\\n\\nmore\\nTOPIC x done: dropped commit f7d92c8e")
"""


def git(path, *a):
    return subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True, check=True).stdout.strip()


class Topics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(self.tmp.cleanup)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        t = Path(self.tmp.name).resolve()
        (t / "claude").write_text(FAKE_CLAUDE); (t / "claude").chmod(0o755)
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_CLAUDE_BIN=str(t / "claude"), FAKE_DIR=str(t))
        for k in ("CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_CHAT_TOKEN", "AGENTS_SUP_TASK", "AGENTS_SUP_TOPIC",
                  "AGENTS_SUPERVISOR", "AGENTS_SUP_ORIG_PATH"):
            os.environ.pop(k, None)
        self.t = t
        self.hub = t / "work" / "hub"; self.hub.mkdir(parents=True)
        git(self.hub, "init", "-q", "-b", "main")
        (self.hub / ".local").mkdir()
        (self.hub / ".local" / "repos.map").write_text("# Format: <repo-slug>: <absolute-path>\nedge: /r/edge\nnav: /r/nav\n")
        st.set_config("p", hub=str(self.hub))
        sw.POLL_DELAY = 0
        self.addCleanup(lambda: setattr(sw, "POLL_DELAY", 0.5))
        top = argparse.ArgumentParser(); sub = top.add_subparsers(); tp.register(sub); self.top = top

    def cli(self, *argv):
        args = self.top.parse_args(list(argv) + ["--profile", "p"])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = args.func(args)
        return rc, out.getvalue(), err.getvalue()

    def log(self):
        p = self.t / "claude.log"
        return [json.loads(l)["argv"] for l in p.read_text().splitlines()] if p.exists() else []

    def calls(self, verb):
        return [a for a in self.log() if a[0] == verb or (verb == "--resume" and "--resume" in a)]

    def test_delegate_starts_a_named_topic_in_the_hub_and_tracks_the_id_claude_chose(self):
        rc, out, err = self.cli("delegate", "rm-152-checkout", "drop the stray commit f7d92c8e")
        self.assertEqual(rc, 0, err)
        row = tp.topics("p")[0]
        self.assertEqual(out, f"started topic rm-152-checkout {row['session']}\n")
        start = next(c for c in map(json.loads, (self.t / "claude.log").read_text().splitlines()) if c["argv"][0] == "--bg")
        self.assertEqual(start["argv"][:5], ["--bg", "--name", "p-topic-rm-152-checkout", "--permission-mode", "auto"])
        self.assertEqual((start["cwd"], start["topic"], start["sup"]), (str(self.hub), "rm-152-checkout", "p"))
        prompt = start["argv"][5]
        for text in ("drop the stray commit f7d92c8e", "TOPIC rm-152-checkout done:", "Do not push",
                     str(tp.notes_path("p", "rm-152-checkout"))):
            self.assertIn(text, prompt)
        self.assertNotIn("Read your notes file first", prompt)
        self.assertEqual(start["argv"][6:], [])  # no --add-dir: an untrusted folder would refuse the start
        self.assertEqual((row["asks"], row["state"]), (1, "running"))

    def test_a_second_ask_resumes_the_same_session_and_a_busy_topic_needs_interrupt(self):
        self.cli("delegate", "nav", "first")
        sid = tp.topics("p")[0]["session"]
        rc, out, _ = self.cli("delegate", "nav", "second")
        self.assertEqual((rc, out), (0, f"resumed topic nav {sid}\n"))
        self.assertEqual(self.calls("stop")[-1], ["stop", sid[:8]])  # an idle bg session is stopped, then resumed
        self.assertEqual(self.calls("--resume")[-1][:4], ["--bg", "--resume", sid, "second"])
        self.assertEqual(tp.topics("p")[0]["asks"], 2)
        (self.t / "busy").write_text(sid[:8])
        rc, _, err = self.cli("delegate", "nav", "third")
        self.assertEqual(rc, 3); self.assertIn("busy", err)
        self.assertEqual(self.cli("delegate", "nav", "third", "--interrupt")[0], 0)

    def test_fresh_starts_a_new_session_that_reads_the_notes(self):
        self.cli("delegate", "nav", "first")
        old = tp.topics("p")[0]["session"]
        tp.notes_path("p", "nav").write_text("found: X\n")
        rc, out, _ = self.cli("delegate", "nav", "again", "--fresh")
        new = tp.topics("p")[0]["session"]
        self.assertEqual((rc, out), (0, f"started topic nav {new}\n"))
        self.assertNotEqual(old, new)
        self.assertIn(["stop", old[:8]], self.calls("stop"))
        self.assertIn("Read your notes file first", self.calls("--bg")[-1][5])

    def test_cap_stop_topics_and_log(self):
        st.set_config("p", topic_cap=1)
        self.cli("delegate", "a", "x")
        rc, _, err = self.cli("delegate", "b", "y")
        self.assertEqual(rc, 3); self.assertIn("topic cap 1 reached (a)", err)
        self.assertIn(str(tp.result_path("p", "a")), self.calls("--bg")[0][5])
        tp.result_path("p", "a").write_text("TOPIC a done: dropped   commit f7d92c8e\n")
        rc, out, _ = self.cli("topics")
        self.assertRegex(out, r"^a  idle  asks 1  [0-9a-f]{8}  last ask 0m ago  done: dropped commit f7d92c8e\n$")
        rc, out, _ = self.cli("topic-log", "a", "--lines", "3")
        self.assertEqual(out.splitlines()[:3], ["TOPIC x done: first", "more", "TOPIC x done: dropped commit f7d92c8e"])
        rc, out, _ = self.cli("stop-topic", "a")
        self.assertEqual(rc, 0)
        self.assertIn("a  stopped  asks 1", self.cli("topics")[1])
        self.assertEqual(self.cli("delegate", "b", "y")[0], 0)  # a stopped topic does not count against the cap
        rc, out, _ = self.cli("delegate", "a", "back")  # a stopped topic resumes without a stop
        self.assertTrue(out.startswith("resumed topic a"), out)
        self.assertFalse(tp.result_path("p", "a").exists())  # each ask clears the old result

    def test_a_resume_that_starts_a_copy_stops_the_copy_and_refuses(self):
        self.cli("delegate", "nav", "first")
        (self.t / "copy").write_text("")
        rc, _, err = self.cli("delegate", "nav", "second")
        self.assertEqual(rc, 3); self.assertIn("could not resume", err); self.assertIn("started a copy e8ad3784", err)
        self.assertEqual(self.calls("stop")[-1], ["stop", "e8ad3784"])
        self.assertEqual(len([a for a in self.calls("--resume") if "second" in a]), tp.RESUME_TRIES)  # retried, then refused
        (self.t / "copy").unlink()
        self.assertEqual(self.cli("delegate", "nav", "third")[0], 0)

    def test_refusals(self):
        self.assertEqual(self.cli("delegate", "Bad_Name", "x")[0], 2)
        self.assertEqual(self.cli("topic-log", "none")[0], 3)
        os.environ["AGENTS_SUP_TOPIC"] = "a"
        rc, _, err = self.cli("topics")
        self.assertEqual(rc, 3); self.assertIn("not for a topic session", err)
        os.environ.pop("AGENTS_SUP_TOPIC"); os.environ["AGENTS_SUP_TASK"] = "RM-1"
        self.assertEqual(self.cli("delegate", "a", "x")[0], 3)
        os.environ.pop("AGENTS_SUP_TASK"); os.environ["AGENTS_SUPERVISOR"] = "p"  # a tick: no session, no token
        self.assertEqual(self.cli("delegate", "a", "x")[0], 3)
        self.assertEqual(self.log(), [])


if __name__ == "__main__":
    unittest.main()
