# ADR 0004: Content factory, trusted kernel and honest labels

**Status:** accepted. The owner approved this architecture decision explicitly on 14 Nov 2026.

## Context

`Item.tier` was a free YAML field and `gate.tier_is_servable` trusted it, so any edit could mark a
question "checked". Only one method (a SymPy solve of a regex-parsed stem) ever checked an answer,
templates were tested by sampling with silent skips, and nothing computed a tier from evidence.
Classes 9 to 12 need thousands of questions in maths, physics, chemistry and biology; we cannot
review each one, so we must trust a small amount of code instead and say exactly what it proves.

## Decision

1. **A small trusted kernel** (`app/factory/kernel/`, pure standard library, under 1,500 lines, size
   and imports enforced by a test): exact rationals, polynomials, integer nullspace for atom and
   charge balance, exact Punnett enumeration, unit conversion with dimension vectors, and one
   frozen, versioned, hashed house-constants table (g = 9.8, R = 8.314, school-style atomic masses;
   owner decision D7; marked unreviewed until the owner signs it off). `verify(spec, answer,
   witness)` per domain (algebra, stoichiometry, kinematics, genetics) fails closed on any
   exception, timeout, unknown kind or missing witness.
2. **Certificates, LCF style.** Only kernel functions can build a `Certificate` (the constructor
   needs a module-private key). Generators, SymPy, Hypothesis, Z3, round-trip checks and LLM drafts
   produce data and rejections, never acceptances. A method that disagrees is never outvoted. An
   item certificate needs the kernel plus at least one method from another independence group. A
   certificate records kernel and checker versions and the constants-table hash, so any change to
   them makes old certificates stale. Template certificates are exhaustive over the declared
   parameter box up to 200,000 tuples; above that a seeded sample of 29,956 gives a one-sided 95%
   Clopper-Pearson bound of 1e-4 on the failure rate of the checkers over that box. Any failure
   means no certificate.
3. **Review pipeline.** Seventeen ordered checkers (schema, rights, syllabus scope, well-posedness,
   units, methods 1..n, allowed-methods trace, key consistency, distractors, leak, language, facts,
   diagram, originality, dedupe, stamp). Plugins register through `app/factory/registry.py`. The
   fact and diagram checkers fail closed on any item that carries facts or a diagram. Every
   implemented checker is proved by seeded-fault injection (sign flip, wrong constant, unit slip,
   off-by-one atom, dropped root, swapped option and others) at a 100% kill rate per class.
4. **Honest labels only.** The factory can emit `calculation-checked`,
   `fact-checked-against-sources` and `diagram-spec-checked`. `human-reviewed` and
   `teacher-approved` are not in the record's label type and are refused by name: only a person
   can grant them. The wording shown to learners lives in `app/content/labels.py`.
5. **Tier is computed, not typed.** A tier A (or a factory tier B) counts only when the item carries
   a `vrec/1` record that hashes correctly, names the item's current content hash, carries a label
   that maps to that tier, and whose hash is in the hash-chained stamp ledger
   (`content/factory/ledger.jsonl`). The loader drops a hand-written tier A with a warning; a
   hand-written B still stands only with a recorded reviewer, as before; C always stands.
   Items with no tier keep today's status rule. `python -m app.factory stamp` is the only writer.
6. **Suspension.** `items.suspended_at` switches an item off whatever its tier or status. It is
   logged in the ledger, re-applied on every content load, and lifted only by a person or a
   re-certification.
7. **Error budget (owner decision D4).** The target is about one error per 1,000 student responses
   at 95% confidence, estimated by audit sampling (random and exposure-weighted). We never claim
   "perfect". A certificate proves the key equals the model's output over the declared box; it does
   not prove the stem describes the model, which is why wording, hints and a sample audit remain.

## Not auto-served (hard exclusions)

Free-text and short-answer biology; any item whose key or a fact was written by an LLM (an LLM may
draft wording around a deterministic answer, and every number is recomputed); facts with fewer than
two independent confirmations; diagrams without an engine QA pass (fail closed, until an engine
ADR exposes the figure spec hash); translations (they stay pending the owner's reviewers, English
only at launch).

## Consequences

- New package `app/factory/`, migration 0035 (columns only), CLI `python -m app.factory`.
- `SERVE_TIER_A_UNREVIEWED` still defaults to false; stamped tier A items serve only when the owner
  turns it on, and only if they are original and not suspended.
- Shared-mistake risk remains (a wrong table value used by every method); mitigations are
  independence groups, golden vectors written by a different author, a pinned constants hash and the
  audit loop. The ledger is evidence, not a secret: it can be forged by someone who rewrites it and
  the git history.

## Rule for hint and worked-step writing (all lanes)

Hint ladders and worked steps teach "do the same operation to both sides" (inverse operations). They
never teach the "move it across and flip the sign" shortcut, because it hides why the step is valid
and produces sign slips. Lane reviewers and the wording audit reject a hint that uses it.
