#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_state.py: the state of one supervisor profile."""
import os, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import sup_state as st


class State(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ["AGENTS_SUP_DIR"] = self.tmp.name; os.environ.pop("AGENTS_SUPERVISOR", None)

    def test_names_are_checked_and_the_profile_comes_from_the_flag_then_the_environment(self):
        self.assertIsNone(st.current_profile()); os.environ["AGENTS_SUPERVISOR"] = "redmesh"
        self.assertEqual(st.current_profile(), "redmesh"); self.assertEqual(st.current_profile("eg"), "eg")
        for bad in ("../x", "A", ""):
            with self.assertRaises(ValueError): st.profile_dir(bad)
        with self.assertRaises(ValueError): st.write_pack("p", {"name": "a", "tasks": ["../x"]})
        with self.assertRaises(ValueError): st.inbox("p", "../x")

    def test_packs_round_trip_with_defaults_and_find_their_task(self):
        st.write_pack("p", {"name": "rm-152", "tasks": ["RM-152", "RM-153"]})
        self.assertEqual(st.read_pack("p", "rm-152")["state"], "new"); self.assertIsNone(st.read_pack("p", "none"))
        self.assertEqual(st.pack_of("p", "RM-153")["name"], "rm-152"); self.assertIsNone(st.pack_of("p", "RM-9"))
        self.assertEqual([x["name"] for x in st.list_packs("p")], ["rm-152"])

    def test_workers_are_added_changed_found_and_dropped(self):
        st.set_worker("p", "s1", task="RM-1", pack="a"); st.set_worker("p", "s2", task="RM-2", state="done")
        st.set_worker("p", "s1", state="waiting", waiting_for="lab")
        self.assertEqual(st.worker_for("p", task="RM-1")["waiting_for"], "lab"); self.assertEqual(len(st.workers("p")), 2)
        self.assertEqual([w["session"] for w in st.live_workers("p")], ["s1"])
        with self.assertRaises(ValueError): st.set_worker("p", "s1", state="asleep")
        st.drop_worker("p", "s1"); self.assertIsNone(st.worker_for("p", session="s1"))

    def test_events_get_rising_ids_and_the_cursor_only_moves_forward(self):
        a = st.emit("p", "ask", task="RM-1", q="Q1"); b = st.emit("p", "done", task="RM-1", session="sess-0001")
        self.assertEqual((a, b), (1, 2)); self.assertEqual([e["kind"] for e in st.events_since("p")], ["ask", "done"])
        st.advance("p", 1); self.assertEqual([e["id"] for e in st.events_since("p")], [2])
        st.advance("p", 0); self.assertEqual(st.cursor("p"), 1)
        (st.profile_dir("p") / "events.jsonl").open("a").write("not json\n"); self.assertEqual(st.emit("p", "dead"), 3)

    def test_emit_refuses_bad_kind_task_session_key_and_value_and_cleans_strings(self):
        for kw in ({"kind": "bogus"}, {"task": "../x"}, {"session": "s1"}, {"q\nx": 1}, {"v": ["a"]}):
            with self.assertRaises(ValueError): st.emit("p", **{"kind": "ask", **kw})
        with self.assertRaises(ValueError): st.emit("p", "ask", v={"a": 1})
        st.emit("p", "ask", reason="a\nTICK RULE\x00" + "x" * 300)
        r = st.events_since("p")[0]["reason"]; self.assertNotIn("\n", r); self.assertEqual(len(r), 200)
        self.assertEqual(st.events_since("p")[0]["id"], 1)

    def test_ids_survive_a_torn_line_a_removed_log_and_a_missing_seq_file(self):
        d = st.profile_dir("p"); st.emit("p", "dead"); (d / "events.jsonl").open("a").write('{"id": 2, "ki')
        self.assertEqual(st.emit("p", "dead"), 2); self.assertEqual([e["id"] for e in st.events_since("p")], [1, 2])
        (d / "events.jsonl").unlink(); self.assertEqual(st.emit("p", "dead"), 3)  # seq file keeps counting
        (d / "events.seq").unlink(); (d / "events.jsonl").write_text('{"id": 9, "kind": "dead"}\n')
        self.assertEqual(st.emit("p", "dead"), 10)

    def test_emit_does_not_parse_the_log(self):
        st.emit("p", "dead"); (st.profile_dir("p") / "events.jsonl").write_text("x" * 100)
        orig = st._events; st._events = lambda *_: self.fail("parsed the log")
        self.addCleanup(setattr, st, "_events", orig); st.emit("p", "dead")

    def test_advance_leaves_no_temp_file_and_a_starting_worker_counts_as_live(self):
        st.advance("p", 5); self.assertEqual(st.cursor("p"), 5)
        self.assertEqual([f.name for f in st.profile_dir("p").glob(".tmp-*")], [])
        st.set_worker("p", "sess-0001", state="starting", stopped_by="owner")
        self.assertEqual(len(st.live_workers("p")), 1); self.assertEqual(st.worker_for("p", task=None, session="sess-0001")["stopped_by"], "owner")

    def test_landed_is_an_event_or_the_archive_ref_on_the_default_branch(self):
        import subprocess
        hub = Path(self.tmp.name) / "hub"; hub.mkdir()
        g = lambda *a: subprocess.run(["git", "-C", str(hub), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)
        g("init", "-q", "-b", "main"); g("commit", "-q", "--allow-empty", "-m", "base")
        self.assertFalse(st.landed("p", "RM-1", hub))
        g("update-ref", "refs/archive/task/RM-1", "HEAD"); self.assertFalse(st.landed("p", "RM-1", hub))
        g("commit", "-q", "--allow-empty", "-m", "done\n\nArchive: refs/archive/task/RM-1"); self.assertTrue(st.landed("p", "RM-1", hub))
        st.emit("p", "landed", task="RM-2"); self.assertTrue(st.landed("p", "RM-2", hub))
        with self.assertRaises(ValueError): st.landed("p", "../x", hub)

    def test_a_question_is_closed_by_its_first_answer_only(self):
        q = st.queue_add("p", "RM-1", "which branch?", ["a", "b"], "a"); self.assertEqual(q, "Q1")
        self.assertTrue(st.queue_close("p", q, "a", "sup")); self.assertFalse(st.queue_close("p", q, "b", "owner"))
        self.assertFalse(st.queue_close("p", "Q9", "a", "sup")); self.assertEqual(st.queue("p"), [])
        self.assertEqual(st.queue("p", open_only=False)[0]["answer"], "a"); self.assertEqual(st.queue_add("p", None, "x"), "Q2")

    def test_inbox_entries_are_numbered_per_task_and_acknowledged(self):
        a = st.inbox_add("p", "RM-1", "use develop", q="Q1"); b = st.inbox_add("p", "RM-1", "no push", by="owner")
        self.assertEqual((a, b), ("A1", "A2")); self.assertTrue(st.inbox_ack("p", "RM-1", "A1")); self.assertFalse(st.inbox_ack("p", "RM-1", "A7"))
        self.assertEqual([r["id"] for r in st.inbox("p", "RM-1", unread_only=True)], ["A2"]); self.assertEqual(st.inbox("p", "RM-2"), [])
        with self.assertRaises(ValueError): st.inbox_add("p", "RM-1", "x", by="worker")

    def test_config_has_defaults_and_instructions_and_touches_are_appended(self):
        self.assertEqual(st.config("p")["cap"], 3); self.assertEqual(st.set_config("p", cap=5)["cap"], 5); self.assertEqual(st.config("p")["land"], "auto")
        st.instruct("p", "never touch\nrm1 at night"); self.assertIn("never touch rm1 at night", st.instructions("p"))
        st.touch("p", "start-pack a"); self.assertEqual(len((st.profile_dir("p") / "touch.log").read_text().splitlines()), 1)

    def test_a_damaged_file_reads_as_empty(self):
        (st.profile_dir("p") / "workers.json").write_text("{broken"); (st.profile_dir("p") / "queue.json").write_text("{}")
        self.assertEqual(st.workers("p"), []); self.assertEqual(st.queue("p"), [])

    def test_hub_is_the_flag_then_the_profile_config_then_the_git_toplevel(self):
        flag, cfg = Path(self.tmp.name) / "flag", Path(self.tmp.name) / "cfg"
        flag.mkdir(); cfg.mkdir()
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        self.assertEqual(st.hub("p"), Path(__file__).resolve().parents[2])  # this repository: the cwd's toplevel
        st.set_config("p", hub=str(cfg)); self.assertEqual(st.hub("p"), cfg)
        self.assertEqual(st.hub("p", str(flag)), flag.resolve())
        os.chdir(self.tmp.name); st.set_config("q", cap=1)
        with self.assertRaises(ValueError): st.hub("q")  # no flag, no config, not a git checkout

    def test_a_part_keeps_its_own_file_with_read_json_and_write_json(self):
        f = st.profile_dir("p") / "mine.json"
        self.assertEqual(st.read_json(f, {}), {}); st.write_json(f, {"a": 1})
        self.assertEqual(st.read_json(f, {}), {"a": 1}); self.assertEqual(st.read_json(f, []), [])  # another type: the default


if __name__ == "__main__":
    unittest.main()
