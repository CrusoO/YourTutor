# Parked features

Features kept in the code but not active. Checked against the code on 2026-11-10 (flag names and entry points are from `apps/api/app/config.py` and the files named below).

| Feature | State | Switch | Where | What turning it on needs |
|---|---|---|---|---|
| Ask module (Study Mode Ask) | Off. The chat route in `app/ask/flow.py` returns early unless the flag is set | `ASK_ENABLED` (`settings.ask_enabled`, default `False`). `EXPLAIN_ENABLED` is separate: the signed-out explain and chat routes use it | `apps/api/app/ask/` (`flow`, `gate`, `guard`, `embed`, `evals`, `load`) | An LLM key. The retrieval step uses a hashing embedder, which is a stand-in. The founder decides whether it stays here or moves to `experimental/` |
| BKT-F (forgetting-aware BKT) | Not in the live path. No flag: it is an offline replay tool, so nothing calls it while a student practises | None. Run `python -m app.player.shadow_report --student <id>` (read-only) | `app/learner/bktf.py`, `bktf_shadow.py`, `bktf_sim.py`, `app/player/shadow_report.py`, `ladder_log.py` | Promotion is decided on logged attempts (see PLAN.md Decisions), not by a flag |
| Loop B (shadow trait profile) | Off. `app/player/loop_b_hook.py` runs when a practice session ends and returns at once unless the flag is set | `LOOP_B_ENABLED` (`settings.loop_b_enabled`, default `False`) | `app/learner/loop_b.py`, `loop_b_store.py`, `app/player/loop_b_hook.py` | It writes a shadow trait profile per learner, so it needs the consent and legal decisions in the master plan (OPEN-16) first |

Also off by default: `RESEARCH_MODULE` (`settings.research_module`).

Related: [REMOVED.md](../REMOVED.md), [ROADMAP.md](ROADMAP.md).
