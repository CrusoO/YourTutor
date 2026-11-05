# How versions move: the release process

Source: Brownie-COMPLETE-PLAN-v3.md, Part 3 (5 Nov 2026), in the parent folder (not in this repo).
Dates and gates for each version are in [ROADMAP.md](ROADMAP.md).

## 1. Version numbers

- **MAJOR (v2, v3 and so on):** a new audience or channel, a new data contract or consent model, or a new teaching model.
- **MINOR (v1.1, v1.2 and so on):** new features or content packs behind flags.
- **PATCH (v1.1.1 and so on):** fixes only.
- **Prompts** have their own versions (for example `tutor.v3`), recorded with every LLM call.
- **Model IDs are pinned in config**, never "latest".

## 2. How a new feature enters (the intake checklist)

Before any code, every new feature gets a one-page Feature Card in `docs/features/<name>.md`. The folder does not exist yet. It is created with the first card, with the founder's approval.

1. **The problem**, and which research finding supports it (link).
2. **Who** it is for, and the tier (guest, minor, adult, corporate).
3. **Safety review:** can it expose a child, or weaken distress detection, the leak guard, the verifier or the registry?
4. **Privacy review:** new data? Retention? Consent change? If yes, update the privacy notice and the data inventory.
5. **Cost estimate:** tokens, hosting, people time.
6. **Success metric** and how it is measured.
7. **Flag name**, **kill switch**, and rollback plan.
8. **Owner** and the version it targets.

The founder approves the card. Then the feature is built **behind a flag**, off by default.

## 3. Branches and environments

- `main` is production.
- `release/x.y` is a release being stabilised.
- `integration` is where reviewed workstreams merge.
- `fix/...` and `feat/...` are workstream branches in their own worktrees.
- Environments: local, then **staging** (seeded test data, no real children), then production.
- **Database migrations go forward only.** Each has a written rollback plan and is tested on a copy of production-shaped data.

## 4. The release train

1. **Monthly minor release** outside exam windows. Patches at any time.
2. **Exam freeze:** 1 Feb to 31 Mar 2027 (boards), and two weeks before major school exams later. Fixes only, with the founder's approval.
3. **Staged rollout:** internal, then one teacher or class, then 10%, then everyone. Watch the gates at each step: errors, safety flags, time to first token, cost, drop-off.
4. **Release checklist:**
   - all tests and the safety eval are green;
   - a content audit sample is done;
   - a performance check against targets is done;
   - docs are updated (PLAN, CHANGELOG, ROADMAP, and the privacy notice if data changed);
   - a backup is taken;
   - a rollback is tested.
5. **Post-release review within 7 days:** what moved in the metrics, what broke, what to change. Written in `docs/releases/vX.Y.md` (folder created with the first release note).

## 5. Model and prompt upgrades

- A new model version (for example a future Haiku) is treated like a feature. Run the eval suite first:
  - safety eval;
  - leak-guard tests;
  - a tutor-quality set graded blind by two teachers;
  - cost and latency.
- Switch only behind a flag. Roll out in stages. Keep the old model ID available for rollback.
- A prompt change is a new prompt version plus the same eval.

## 6. Cleanup rules (apply to every refactor PR)

From Part 5 of the source plan:
1. Clean before you build. v0.95 Clean Base happens after Safe Base and before Board Sprint features.
2. Refactor PRs never change behaviour. The same tests pass before and after. Nothing new is added in the same PR.
3. Delete only with evidence: no references (grep), no imports, no routes, no tests depending on it, and no flag that turns it on in any environment. Record each deletion in [REMOVED.md](../REMOVED.md) with what, why, evidence, and the restore commit.
4. Ask before deleting anything not clearly dead, anything another session or worktree uses, untracked files you did not create, branches, worktrees, and anything with personal data.
5. One category per PR (dead env, dead code, stale docs, tests, dependencies).
6. Archive history. Move stale docs to `docs/archive/` with a header saying "superseded by", and the date.
