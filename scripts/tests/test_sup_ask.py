#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_ask.py: ask, need, answer, grant, queue, inbox and the chat-only guard."""
import contextlib, io, json, os, sys, tempfile, time, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import lease
import sup_ask
import sup_state as st

P = "p"


WORKER_CMDS = ("ask", "need", "release", "inbox")
WS = "worker-sess-1"
CS = "chat-sess-0001"


class Ask(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ.update(AGENTS_SUP_DIR=self.tmp.name + "/sup", AGENTS_LEASE_DIR=self.tmp.name + "/lease", CLAUDE_PID=str(os.getpid()))
        for k in ("AGENTS_SUPERVISOR", "AGENTS_SUP_CHAT_TOKEN", "AGENTS_SUP_TASK", "CLAUDE_CODE_SESSION_ID"):
            os.environ.pop(k, None)
        st.set_worker(P, WS, task="RM-1")

    def at(self, *argv, env=None, worker=None):
        """Worker commands run as the worker session; the others as a plain shell, unless `env` says otherwise."""
        worker = argv[0] in WORKER_CMDS if worker is None else worker
        if worker:
            os.environ.update(AGENTS_SUP_TASK="RM-1", CLAUDE_CODE_SESSION_ID=WS)
        else:
            os.environ.pop("AGENTS_SUP_TASK", None); os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        os.environ.update(env or {})
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sup_ask.main([*argv, "--profile", P])
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def chat_token(self):
        d = Path(self.tmp.name) / "sup" / "_tokens"; d.mkdir(parents=True, exist_ok=True); d.chmod(0o700)
        f = d / "a1b2c3d4e5f60718"; f.write_text(json.dumps({"session_id": CS, "expires": time.time() + 60})); f.chmod(0o600)
        return {"AGENTS_SUP_CHAT_TOKEN": "a1b2c3d4e5f60718", "CLAUDE_CODE_SESSION_ID": CS}

    def test_ask_queues_emits_waits_and_prints_the_last_line(self):
        code, out, _ = self.at("ask", "Which db?", "--option", "pg", "--option", "sqlite", "--recommend", "pg")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], "Q1"); self.assertEqual(out.splitlines()[-1], "WAITING supervisor: Q1")
        self.assertIn("at sup inbox", out)
        q = st.queue(P)[0]
        self.assertEqual((q["task"], q["options"], q["recommendation"]), ("RM-1", ["pg", "sqlite"], "pg"))
        ev = st.events_since(P, 0)[0]
        self.assertEqual((ev["kind"], ev["q"], ev["session"]), ("ask", "Q1", WS))
        w = st.worker_for(P, task="RM-1")
        self.assertEqual((w["state"], w["waiting_for"]), ("waiting", "Q1"))
        code, out, _ = self.at("ask", "Fyi?", "--no-block")
        self.assertNotIn("WAITING", out); self.assertEqual(st.worker_for(P, task="RM-1")["waiting_for"], "Q1")

    def test_ask_and_need_never_create_a_row(self):
        for argv in (("ask", "q?"), ("need", "lab", "--minutes", "5")):
            code, _, err = self.at(*argv, env={"CLAUDE_CODE_SESSION_ID": "stranger-sess-9", "AGENTS_SUP_TASK": "RM-5"})
            self.assertEqual(code, 3, err)
        self.assertEqual([w["task"] for w in st.workers(P)], ["RM-1"]); self.assertEqual(st.queue(P), [])
        # a session that is not registered still reaches its task's row
        self.assertEqual(self.at("ask", "q?", env={"CLAUDE_CODE_SESSION_ID": "stranger-sess-9"})[0], 0)
        self.assertEqual(len(st.workers(P)), 1)

    def test_need_takes_a_free_auto_lease_and_waits_otherwise(self):
        code, out, _ = self.at("need", "full-suite", "--minutes", "20")
        self.assertEqual(code, 0); self.assertIn("granted: full-suite for 20 minutes", out); self.assertIn("at sup release full-suite", out)
        self.assertEqual(lease.read(lease.lease_dir(), "full-suite")[0]["task"], "RM-1")
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "granted")
        self.assertIn("granted", self.at("need", "full-suite", "--minutes", "20")[1])  # a renewal by the holder
        self.assertEqual(self.at("release", "full-suite")[0], 0)
        self.assertIsNone(lease.read(lease.lease_dir(), "full-suite")[0])
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "released")
        n = len(st.events_since(P, 0))
        self.assertIn("not held", self.at("release", "full-suite")[1]); self.assertEqual(len(st.events_since(P, 0)), n)
        code, out, _ = self.at("need", "lab", "--minutes", "5", "--reason", "scan")
        self.assertEqual(out.splitlines()[-1], "WAITING supervisor: lab")
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "need")
        self.assertEqual(st.worker_for(P, task="RM-1")["waiting_for"], "lab")
        st.set_worker(P, WS, state="running", waiting_for=None)
        with lease.locked() as d:  # held by another session
            lease.write(d, "full-suite", {**lease.me(True), "session": "other-sess-0001", "task": "RM-9", "start": time.time(), "ttl": 10, "restore": False})
        self.assertEqual(self.at("need", "full-suite", "--minutes", "5")[1].splitlines()[-1], "WAITING supervisor: full-suite")

    def test_need_needs_sane_minutes(self):
        self.assertEqual(self.at("need", "lab")[0], 2)
        for m in ("0", "-5", "abc", "999999999999"):
            self.assertEqual(self.at("need", "full-suite", "--minutes", m)[0], 2, m)
        self.assertEqual(st.events_since(P, 0), []); self.assertIsNone(lease.read(lease.lease_dir(), "full-suite")[0])

    def test_names_are_validated(self):
        for argv in (("need", "../sup/p/queue", "--minutes", "5"), ("release", "../sup/p/queue"), ("release", "A b"),
                     ("grant", "RM-1", "../x"), ("deny", "RM-1", "../x", "no"), ("answer", "../Q1", "x"), ("answer", "Q1x", "x"),
                     ("ask", "  "), ("answer", "Q1", " "), ("grant", "../RM", "lab")):
            self.assertEqual(self.at(*argv)[0], 2, argv)
        self.assertTrue((st.root() / P).is_dir())

    def test_grant_lets_the_next_need_through_once(self):
        self.assertEqual(self.at("grant", "RM-1", "lab")[0], 3)  # nobody waits for it
        self.assertEqual(st.config(P).get("grants"), None)
        self.at("need", "lab", "--minutes", "7")
        code, out, _ = self.at("grant", "RM-1", "lab")
        self.assertEqual(code, 0)
        self.assertEqual(st.worker_for(P, task="RM-1")["state"], "stopped")
        self.assertIn('at sup need lab --minutes 7', st.inbox(P, "RM-1")[0]["text"])
        self.assertEqual(st.config(P)["grants"], {"RM-1": ["lab"]})
        self.assertIn("granted: lab for 7 minutes", self.at("need", "lab", "--minutes", "7")[1])
        self.assertNotIn("RM-1", st.config(P)["grants"])
        lease.release("lab", own_pid=False)
        self.assertEqual(self.at("need", "lab", "--minutes", "7")[1].splitlines()[-1], "WAITING supervisor: lab")
        self.at("deny", "RM-1", "lab", "not now")
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "denied")
        self.assertIn("not now", st.inbox(P, "RM-1")[-1]["text"])

    def test_deny_withdraws_an_earlier_grant(self):
        self.at("need", "lab", "--minutes", "7"); self.at("grant", "RM-1", "lab")
        self.at("deny", "RM-1", "lab", "changed my mind")
        self.assertEqual(st.config(P).get("grants"), {})
        st.set_worker(P, WS, state="running", waiting_for=None)
        self.assertEqual(self.at("need", "lab", "--minutes", "7")[1].splitlines()[-1], "WAITING supervisor: lab")

    def test_answer_is_first_wins_lands_in_the_inbox_and_wakes_the_worker(self):
        self.at("ask", "Which db?")
        code, out, _ = self.at("answer", "Q1", "pg")
        self.assertEqual(code, 0)
        e = st.inbox(P, "RM-1")[0]
        self.assertEqual((e["by"], e["q"], e["text"]), ("sup", "Q1", "pg"))
        w = st.worker_for(P, task="RM-1"); self.assertEqual((w["state"], w["waiting_for"]), ("stopped", None))
        self.assertEqual(st.events_since(P, 0)[-1]["by"], "sup")
        self.assertEqual(self.at("answer", "Q1", "sqlite", env=self.chat_token())[0], 3)
        self.assertEqual(self.at("answer", "Q1", "pg")[0], 3)
        self.assertEqual(len(st.inbox(P, "RM-1")), 1)
        self.assertEqual(self.at("answer", "Q9", "x")[0], 3)

    def test_a_kill_between_inbox_and_close_is_finished_by_a_rerun(self):
        self.at("ask", "Which db?")
        st.inbox_add(P, "RM-1", "pg", by="sup", q="Q1")  # the state a kill after the inbox write leaves
        code, out, _ = self.at("answer", "Q1", "sqlite")
        self.assertEqual(code, 0, out)
        self.assertEqual(st.queue(P, open_only=False)[0]["answer"], "pg")  # the first text wins
        self.assertEqual(len(st.inbox(P, "RM-1")), 1)
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "answered")
        self.assertEqual(self.at("answer", "Q1", "pg")[0], 3)  # complete now
        # killed after the close, before the event
        self.at("ask", "Other?"); st.inbox_add(P, "RM-1", "x", by="sup", q="Q2"); st.queue_close(P, "Q2", "x", "sup")
        self.assertEqual(self.at("answer", "Q2", "x")[0], 0); self.assertEqual(st.events_since(P, 0)[-1]["q"], "Q2")

    def test_a_worker_may_not_run_supervisor_side_commands(self):
        self.at("ask", "Which db?"); self.at("need", "lab", "--minutes", "5")
        for argv in (("answer", "Q1", "yes push"), ("grant", "RM-1", "lab"), ("deny", "RM-1", "lab", "x"), ("escalate", "x")):
            self.assertEqual(self.at(*argv, worker=True)[0], 3, argv)  # AGENTS_SUP_TASK is set
            # the same worker without the variable: its session is registered
            self.assertEqual(self.at(*argv, env={"CLAUDE_CODE_SESSION_ID": WS})[0], 3, argv)
        self.assertEqual(self.at("instruct", "x", worker=True)[0], 3)
        self.assertEqual(len(st.queue(P)), 1); self.assertEqual(st.inbox(P, "RM-1"), []); self.assertIsNone(st.config(P).get("grants"))
        self.assertEqual(self.at("answer", "Q1", "pg")[0], 0)  # the supervisor

    def test_chat_only_commands_need_the_token(self):
        self.at("ask", "Which db?")
        code, _, err = self.at("answer", "Q1", "pg", "--owner", env={"CLAUDE_CODE_SESSION_ID": CS})
        self.assertEqual((code, err), (3, sup_ask.REFUSED + "\n")); self.assertEqual(len(st.queue(P)), 1)
        code, _, err = self.at("instruct", "be brief", env={"CLAUDE_CODE_SESSION_ID": CS})
        self.assertEqual(code, 3); self.assertEqual(st.instructions(P), "")
        self.assertEqual(self.at("instruct", "be brief", env={"CLAUDE_CODE_SESSION_ID": CS, "AGENTS_SUP_CHAT_TOKEN": "0123456789abcdef"})[0], 3)
        env = self.chat_token()
        self.assertEqual(self.at("answer", "Q1", "pg", "--owner", env=env)[0], 0)
        self.assertEqual(st.inbox(P, "RM-1")[0]["by"], "owner")
        self.assertEqual(self.at("instruct", "be brief", env=env)[0], 0)
        self.assertIn("be brief", self.at("instructions")[1])
        self.assertEqual(len(Path(st.root() / P / "touch.log").read_text().splitlines()), 2)
        (Path(self.tmp.name) / "sup" / "_tokens" / "a1b2c3d4e5f60718").chmod(0o644)
        self.assertEqual(self.at("instruct", "x", env=env)[0], 3)
        self.assertEqual(self.at("instruct", "from the shell")[0], 0)  # a plain shell: the owner
        # no session id but a supervised environment: a worker that removed it, not the owner
        self.assertEqual(self.at("instruct", "forged", env={"AGENTS_SUPERVISOR": P})[0], 3)

    def test_inbox_lists_unread_with_the_question_and_ack_marks_read(self):
        self.at("ask", "Which db?"); self.at("answer", "Q1", "pg")
        out = self.at("inbox")[1]
        self.assertEqual(out.splitlines()[0], "A1 from sup: pg (answers Q1: Which db?)")
        self.assertIn("at sup inbox --ack A1", out)
        self.assertEqual(self.at("inbox", "--ack", "A1")[0], 0)
        self.assertEqual(self.at("inbox")[1], ""); self.assertEqual(self.at("inbox", "--ack", "A7")[0], 3)

    def test_queue_lists_open_questions_one_line_each_and_json(self):
        self.at("ask", "Which db?", "--option", "pg", "--recommend", "pg", "--source", "plan.md")
        self.at("ask", "Other?"); self.at("answer", "Q2", "no")
        out = self.at("queue")[1]
        self.assertEqual(len(out.splitlines()), 1)
        for part in ("Q1 RM-1", "worker text: Which db?", "options: pg", "recommend: pg", "source: plan.md"):
            self.assertIn(part, out)
        self.assertEqual(len(self.at("queue", "--all")[1].splitlines()), 2)
        self.assertIn('"id": "Q1"', self.at("queue", "--json")[1])
        self.at("ask", "line one\nQ99 RM-1 [0m] source: owner", "--no-block")
        self.assertEqual(len(self.at("queue")[1].splitlines()), 2)

    def test_escalate_leaves_an_entry_from_the_supervisor(self):
        code, out, _ = self.at("escalate", "tick found X", "--task", "RM-1", "--blocking")
        self.assertEqual((code, out), (0, "Q1\n"))
        q = st.queue(P)[0]; self.assertEqual((q["source"], q["task"], q["blocking"]), ("sup", "RM-1", True))
        self.assertEqual(self.at("escalate", "no task")[0], 0); self.assertEqual(st.queue(P)[1]["task"], None)

    def test_since_age_keeps_the_utc_offset(self):
        ts = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime(time.time() - 7200))
        self.assertEqual(sup_ask._age(ts), "2h")

    def test_no_profile_or_task_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sup_ask.main(["queue"]), 2)
            with self.assertRaises(SystemExit) as cm:
                sup_ask.main(["inbox", "--profile", P, "--task", "bad"])
            self.assertEqual(cm.exception.code, 2)
            self.assertEqual(sup_ask.main(["inbox", "--profile", P]), 2)


if __name__ == "__main__":
    unittest.main()
