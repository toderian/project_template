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


class Ask(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ.update(AGENTS_SUP_DIR=self.tmp.name + "/sup", AGENTS_LEASE_DIR=self.tmp.name + "/lease",
                          AGENTS_SUP_TASK="RM-1", CLAUDE_CODE_SESSION_ID="s1", CLAUDE_PID=str(os.getpid()))
        for k in ("AGENTS_SUPERVISOR", "AGENTS_SUP_CHAT_TOKEN"):
            os.environ.pop(k, None)
        st.set_worker(P, "s1", task="RM-1")

    def at(self, *argv, env=None):
        os.environ.update(env or {})
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sup_ask.main([*argv, "--profile", P])
        return code, out.getvalue(), err.getvalue()

    def chat_token(self):
        d = Path(self.tmp.name) / "sup" / "_tokens"; d.mkdir(parents=True, exist_ok=True); d.chmod(0o700)
        f = d / "a1b2c3d4e5f60718"; f.write_text(json.dumps({"session_id": "s1", "expires": time.time() + 60})); f.chmod(0o600)
        return {"AGENTS_SUP_CHAT_TOKEN": "a1b2c3d4e5f60718"}

    def test_ask_queues_emits_waits_and_prints_the_last_line(self):
        code, out, _ = self.at("ask", "Which db?", "--option", "pg", "--option", "sqlite", "--recommend", "pg")
        self.assertEqual((code, out), (0, "Q1\nWAITING supervisor: Q1\n"))
        q = st.queue(P)[0]
        self.assertEqual((q["task"], q["options"], q["recommendation"]), ("RM-1", ["pg", "sqlite"], "pg"))
        ev = st.events_since(P, 0)[0]
        self.assertEqual((ev["kind"], ev["q"]), ("ask", "Q1"))
        w = st.worker_for(P, task="RM-1")
        self.assertEqual((w["state"], w["waiting_for"]), ("waiting", "Q1"))
        code, out, _ = self.at("ask", "Fyi?", "--no-block")
        self.assertEqual(out, "Q2\n"); self.assertEqual(st.worker_for(P, task="RM-1")["waiting_for"], "Q1")

    def test_need_takes_a_free_auto_lease_and_waits_otherwise(self):
        code, out, _ = self.at("need", "full-suite", "--minutes", "20")
        self.assertEqual((code, out), (0, "granted: full-suite for 20 minutes\n"))
        self.assertEqual(lease.read(lease.lease_dir(), "full-suite")[0]["task"], "RM-1")
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "granted")
        self.assertEqual(self.at("release", "full-suite")[0], 0)
        self.assertIsNone(lease.read(lease.lease_dir(), "full-suite")[0])
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "released")
        code, out, _ = self.at("need", "lab", "--minutes", "5", "--reason", "scan")
        self.assertEqual(out, "WAITING supervisor: lab\n")
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "need")
        self.assertEqual(st.worker_for(P, task="RM-1")["waiting_for"], "lab")
        st.set_worker(P, "s1", state="running", waiting_for=None)
        lease.take("full-suite", 10, task="RM-9", own_pid=True)
        self.assertEqual(self.at("need", "full-suite", "--minutes", "5")[1], "WAITING supervisor: full-suite\n")

    def test_grant_lets_the_next_need_through_once(self):
        self.at("need", "lab", "--minutes", "7")
        code, out, _ = self.at("grant", "RM-1", "lab")
        self.assertEqual(code, 0)
        self.assertEqual(st.worker_for(P, task="RM-1")["state"], "stopped")
        self.assertIn('at sup need lab --minutes 7', st.inbox(P, "RM-1")[0]["text"])
        self.assertEqual(st.config(P)["grants"], {"RM-1": ["lab"]})
        self.assertEqual(self.at("need", "lab", "--minutes", "7")[1], "granted: lab for 7 minutes\n")
        self.assertNotIn("RM-1", st.config(P)["grants"])
        lease.release("lab", own_pid=False)
        self.assertEqual(self.at("need", "lab", "--minutes", "7")[1], "WAITING supervisor: lab\n")
        self.at("deny", "RM-1", "lab", "not now")
        self.assertEqual(st.events_since(P, 0)[-1]["kind"], "denied")
        self.assertIn("not now", st.inbox(P, "RM-1")[-1]["text"])

    def test_answer_is_first_wins_lands_in_the_inbox_and_wakes_the_worker(self):
        self.at("ask", "Which db?")
        code, out, _ = self.at("answer", "Q1", "pg")
        self.assertEqual(code, 0)
        e = st.inbox(P, "RM-1")[0]
        self.assertEqual((e["by"], e["q"], e["text"]), ("sup", "Q1", "pg"))
        w = st.worker_for(P, task="RM-1"); self.assertEqual((w["state"], w["waiting_for"]), ("stopped", None))
        self.assertEqual(st.events_since(P, 0)[-1]["by"], "sup")
        self.assertEqual(self.at("answer", "Q1", "sqlite", env=self.chat_token())[0], 3)
        self.assertEqual(len(st.inbox(P, "RM-1")), 1)
        self.assertEqual(self.at("answer", "Q9", "x")[0], 3)

    def test_chat_only_commands_need_the_token(self):
        self.at("ask", "Which db?")
        code, _, err = self.at("answer", "Q1", "pg", "--owner")
        self.assertEqual((code, err), (3, sup_ask.REFUSED + "\n")); self.assertEqual(len(st.queue(P)), 1)
        code, _, err = self.at("instruct", "be brief")
        self.assertEqual(code, 3); self.assertEqual(st.instructions(P), "")
        os.environ["AGENTS_SUP_CHAT_TOKEN"] = "0123456789abcdef"
        self.assertEqual(self.at("instruct", "be brief")[0], 3)
        env = self.chat_token()
        self.assertEqual(self.at("answer", "Q1", "pg", "--owner", env=env)[0], 0)
        self.assertEqual(st.inbox(P, "RM-1")[0]["by"], "owner")
        self.assertEqual(self.at("instruct", "be brief")[0], 0)
        self.assertIn("be brief", self.at("instructions")[1])
        self.assertEqual(len(Path(st.root() / P / "touch.log").read_text().splitlines()), 2)
        (Path(self.tmp.name) / "sup" / "_tokens" / "a1b2c3d4e5f60718").chmod(0o644)
        self.assertEqual(self.at("instruct", "x")[0], 3)
        os.environ.pop("CLAUDE_CODE_SESSION_ID"); os.environ.pop("AGENTS_SUP_CHAT_TOKEN")  # a plain shell: the owner
        self.assertEqual(self.at("instruct", "from the shell")[0], 0)

    def test_inbox_lists_unread_with_the_question_and_ack_marks_read(self):
        self.at("ask", "Which db?"); self.at("answer", "Q1", "pg")
        out = self.at("inbox")[1]
        self.assertEqual(out, "A1 from sup: pg (answers Q1: Which db?)\n")
        self.assertEqual(self.at("inbox", "--ack", "A1")[0], 0)
        self.assertEqual(self.at("inbox")[1], ""); self.assertEqual(self.at("inbox", "--ack", "A7")[0], 3)

    def test_queue_lists_open_questions_and_json(self):
        self.at("ask", "Which db?", "--option", "pg", "--recommend", "pg", "--source", "plan.md")
        self.at("ask", "Other?"); self.at("answer", "Q2", "no")
        out = self.at("queue")[1]
        self.assertEqual(len(out.splitlines()), 1)
        for part in ("Q1 RM-1", "Which db?", "options: pg", "recommend: pg", "source: plan.md"):
            self.assertIn(part, out)
        self.assertEqual(len(self.at("queue", "--all")[1].splitlines()), 2)
        self.assertIn('"id": "Q1"', self.at("queue", "--json")[1])

    def test_no_profile_or_task_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sup_ask.main(["queue"]), 2)
            self.assertEqual(sup_ask.main(["inbox", "--profile", P, "--task", "bad"]), 2)
            os.environ.pop("AGENTS_SUP_TASK")
            self.assertEqual(sup_ask.main(["inbox", "--profile", P]), 2)


if __name__ == "__main__":
    unittest.main()
