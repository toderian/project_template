# Size — unattended-run-hardening whole run · BASE da43501 → working tree

| File | Before | After | Net | Kind |
|---|---|---|---|---|
| plugins/agents-core/lib/run_watch.py | 0 | 514 | +514 (new) | code |
| scripts/tests/test_run_watch.py | 0 | 439 | +439 (new) | test |
| plugins/agents-core/lib/task_lanes.py | 0 | 347 | +347 (new) | code |
| scripts/tests/test_task_run.py | 178 | 513 | +335 | test |
| plugins/agents-core/lib/task_run.py | 873 | 1176 | +303 | code |
| plugins/agents-core/lib/task_report.py | 0 | 210 | +210 (new) | code |
| scripts/tests/test_task_report.py | 0 | 188 | +188 (new) | test |
| plugins/agents-core/hooks/tests/test-hooks.sh | 882 | 1057 | +175 | test |
| plugins/agents-core/lib/at.py | 1609 | 1777 | +168 | code |
| plugins/agents-core/skills/execute-plan/references/run-state.md | 169 | 320 | +151 | docs |
| scripts/tests/live/lib.sh | 0 | 141 | +141 (new) | test |
| docs/specs/2026-11-26-unattended-run-hardening-plan.md | 274 | 412 | +138 | test |
| docs/_plans/_runs/unattended-run-hardening/state.md | 0 | 132 | +132 (new) | docs |
| docs/meta/2026-11-26-run-guard-facts.md | 0 | 121 | +121 (new) | docs |
| scripts/tests/live/e5-watchdog.sh | 0 | 120 | +120 (new) | test |
| scripts/tests/live/e8-driver-lanes.sh | 0 | 118 | +118 (new) | test |
| scripts/tests/test-at.sh | 1816 | 1916 | +100 | test |
| docs/_plans/_runs/unattended-run-hardening/phase-4/brief.md | 0 | 93 | +93 (new) | docs |
| scripts/tests/live/e7-driver-marks.sh | 0 | 90 | +90 (new) | test |
| docs/_plans/_runs/unattended-run-hardening/phase-6/brief.md | 0 | 80 | +80 (new) | docs |
| scripts/tests/live/e1-guard-holds.sh | 0 | 78 | +78 (new) | test |
| docs/_plans/_runs/unattended-run-hardening/phase-3/brief.md | 0 | 76 | +76 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/findings-1.md | 0 | 76 | +76 (new) | docs |
| scripts/tests/live/e6-heartbeat.sh | 0 | 75 | +75 (new) | test |
| docs/_plans/_runs/unattended-run-hardening/phase-2/brief.md | 0 | 72 | +72 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/findings-1.md | 0 | 71 | +71 (new) | docs |
| scripts/tests/live/e4-report.sh | 0 | 71 | +71 (new) | test |
| docs/_plans/_runs/unattended-run-hardening/phase-0/report.md | 0 | 67 | +67 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/findings-1.md | 0 | 67 | +67 (new) | docs |
| scripts/tests/test-unattended-live.sh | 0 | 67 | +67 (new) | test |
| docs/_plans/_runs/unattended-run-hardening/phase-1/brief.md | 0 | 65 | +65 (new) | docs |
| docs/meta/2026-11-26-run-guard-e2e.log | 0 | 64 | +64 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-7/brief.md | 0 | 55 | +55 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/brief.md | 0 | 48 | +48 (new) | docs |
| plugins/agents-core/hooks/run-guard.sh | 101 | 149 | +48 | code |
| docs/_plans/_runs/unattended-run-hardening/phase-0/brief.md | 0 | 47 | +47 (new) | docs |
| plugins/agents-core/hooks/lib/run-open.sh | 0 | 46 | +46 (new) | code |
| docs/_plans/_runs/unattended-run-hardening/phase-2/findings-1.md | 0 | 45 | +45 (new) | docs |
| scripts/tests/live/e2-compaction.sh | 0 | 42 | +42 (new) | test |
| docs/_plans/_runs/unattended-run-hardening/phase-1/findings-1.md | 0 | 41 | +41 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/findings-2.md | 0 | 36 | +36 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/architecture-review-peer.md | 0 | 35 | +35 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/findings-1.md | 0 | 34 | +34 (new) | docs |
| plugins/agents-core/skills/unattended-run/SKILL.md | 136 | 169 | +33 | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-0/findings-1.md | 0 | 32 | +32 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/report.md | 0 | 31 | +31 (new) | docs |
| README.md | 204 | 234 | +30 | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/findings-2.md | 0 | 30 | +30 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/findings-2.md | 0 | 29 | +29 (new) | docs |
| scripts/tests/live/e3-notify.sh | 0 | 29 | +29 (new) | test |
| CHANGELOG.md | 795 | 823 | +28 | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/findings-3.md | 0 | 28 | +28 (new) | docs |
| plugins/agents-core/hooks/run-guard-remind.sh | 0 | 19 | +19 (new) | code |
| docs/_plans/_runs/unattended-run-hardening/phase-3/findings-2.md | 0 | 18 | +18 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/review-quality.md | 0 | 18 | +18 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-1/report.md | 0 | 17 | +17 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-1/size.md | 0 | 17 | +17 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/architecture-brief.md | 0 | 16 | +16 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-1/size-fix-1.md | 0 | 16 | +16 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/report.md | 0 | 16 | +16 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-0/review-quality.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/review-quality.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/re-review-1.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/re-review-1.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/review-quality.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/size-fix-1.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/size-fix-2.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/size.md | 0 | 14 | +14 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/review-quality.md | 0 | 14 | +14 (new) | docs |
| plugins/agents-core/skills/execute-plan/SKILL.md | 357 | 371 | +14 | docs |
| scripts/tests/fixtures/fake-harness.py | 72 | 86 | +14 | test |
| docs/_plans/_runs/unattended-run-hardening/phase-1/review-quality.md | 0 | 13 | +13 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/size-fix-1.md | 0 | 13 | +13 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/size-fix-1.md | 0 | 13 | +13 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/size-fix-2.md | 0 | 13 | +13 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/size.md | 0 | 13 | +13 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/size.md | 0 | 13 | +13 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-7/review.md | 0 | 13 | +13 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/size.md | 0 | 12 | +12 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/review-spec.md | 0 | 12 | +12 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/review-quality.md | 0 | 12 | +12 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/review-security.md | 0 | 12 | +12 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/architecture-review.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-0/fix-1-report.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-1/review-spec.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/review-security.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/re-review-1.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/re-review-3.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/size-fix-3.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/re-review-1.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/review-security.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/size-fix-1.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/size-fix-2.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/size.md | 0 | 11 | +11 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-0/review-spec.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-1/re-review-1.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-1/review-security.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/re-review-1.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/report.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/report.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/review-spec.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/re-review-2.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/report.md | 0 | 10 | +10 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/review-security.md | 0 | 9 | +9 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/re-review-1-security.md | 0 | 9 | +9 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/review-spec.md | 0 | 9 | +9 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/review-spec.md | 0 | 9 | +9 (new) | docs |
| plugins/agents-core/hooks/hooks.codex.json | 75 | 84 | +9 | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-0/re-review-1.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-0/size-fix-1.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-0/size.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/review-spec.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/re-review-2-security.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/size-fix-1.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/size-fix-2.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/re-review-2.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-7/report.md | 0 | 8 | +8 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/fix-2-report.md | 0 | 7 | +7 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/re-review-3-security.md | 0 | 7 | +7 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/re-review-2.md | 0 | 6 | +6 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/re-review-1-security.md | 0 | 6 | +6 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/re-review-2.md | 0 | 6 | +6 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/re-review-1-security.md | 0 | 6 | +6 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/re-review-2-security.md | 0 | 6 | +6 (new) | docs |
| .gitignore | 19 | 24 | +5 | code |
| docs/_plans/_runs/unattended-run-hardening/phase-3/fix-1-report.md | 0 | 5 | +5 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/re-review-2-security.md | 0 | 5 | +5 (new) | docs |
| plugins/agents-core/seed/AGENTS.md | 166 | 171 | +5 | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-1/fix-1-report.md | 0 | 4 | +4 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-2/fix-1-report.md | 0 | 4 | +4 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-3/fix-2-report.md | 0 | 4 | +4 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/fix-3-report.md | 0 | 4 | +4 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/fix-1-report.md | 0 | 4 | +4 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-6/fix-2-report.md | 0 | 4 | +4 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/fix-1-report.md | 0 | 3 | +3 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-5/fix-1-report.md | 0 | 3 | +3 (new) | docs |
| docs/_plans/_runs/unattended-run-hardening/phase-4/fix-2-report.md | 0 | 2 | +2 (new) | docs |
| plugins/agents-core/hooks/hooks.json | 28 | 30 | +2 | docs |
| plugins/agents-tasks/skills/complete-task/SKILL.md | 160 | 162 | +2 | docs |
| scripts/tests/run-all.sh | 30 | 32 | +2 | test |
| scripts/tests/test-codex-live.sh | 147 | 147 | +0 | test |

Total: +6665 / −235, 141 files. Code net +1660 (9 files). Test net +2222 (19 files). Docs net +2548 (113 files). Fixture net +0 (0 files).
Flagged: run_watch.py (new, 514), task_lanes.py (new, 347), task_run.py (+34 %, +303), task_report.py (new, 210), run-guard.sh (+47 %, +48), code net +1660 ≥ 300
