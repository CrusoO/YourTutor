/**
 * The teaching policy for practice sessions, a mirror of apps/api/app/orchestrator/policy.py
 * (rules R01 to R40). `(learner, session, event) -> action`, with no I/O. Diagnostic and
 * checkpoint sessions are online only, so they are not mirrored. Golden fixtures recorded from the
 * Python policy (packages/shared/fixtures/policy) run against both.
 */

import tables from "../../../../packages/shared/generated/policy_tables.json";
import { classify, FAST_STREAK_LIMIT, HELP_WITHOUT_ATTEMPT_LIMIT } from "./diagnosis";
import { leakCheck } from "./leak";
import {
  applyLadderEvent,
  KIND_ANSWER,
  KIND_HINT,
  KIND_LESSON,
  level as ladderLevelOf,
} from "./ladder";
import { applyMastery } from "./mastery";
import { DEFAULT_BKT } from "./bkt";
import { verifyResponse } from "./verify";
import {
  type Action,
  type CatalogItem,
  IDLE_END_MS,
  itemById,
  LATENCY_CAP_MS,
  type LearnerState,
  makeAction,
  MAX_WARMUP,
  PREREQ_BELOW,
  type PolicyEvent,
  primarySkill,
  hintText,
  type SessionState,
} from "./types";
import { parseAt } from "./time";

const T_LEVEL = 4;
const WHEEL_WRONG_STREAK = 3;
const WHEEL_ITEM_LIMIT = 10;
const FRUSTRATION_REVEALS = 2;
const FRUSTRATION_WRONG_RUN = 3;
const STEP_DOWN_ITEMS = 2;
const CHALLENGE_RUN = 3;
const PRAISE_GAP_ITEMS = 3;
const MAX_STRETCH_PER_SESSION = 2;
const TIERS = ["easy", "medium", "hard"];
const STUCK_CHOICES = ["start", "step", "restate", "might_be_right"];
const EXTENSION_ROLE: Record<number, string> = { 4: "apply", 5: "transfer" };

const BREAK_REPLACES = new Set([
  "hint",
  "show_item",
  "similar_item",
  "explain_back_prompt",
  "check_your_work",
  "predict",
  "warmup_item",
  "reveal_solution",
]);
const PROBE_REPLACES = new Set([
  "hint",
  "show_item",
  "similar_item",
  "explain_back_prompt",
  "check_your_work",
]);

type Transition = [string, string, string, string, string];
const TRANSITIONS = tables.transitions as Transition[];
const VARIANTS = tables.encouragement_variants as Record<string, string[]>;

export function ruleIdFor(stateBefore: string, event: string, action: string): string {
  for (const [ruleId, before, ev, , act] of TRANSITIONS) {
    if ((before === stateBefore || before === "any") && ev === event && act === action) {
      return ruleId;
    }
  }
  return `${stateBefore}:${event}->${action}`;
}

export function itemTier(difficulty: number): string {
  if (difficulty < 0.4) return "easy";
  if (difficulty <= 0.8) return "medium";
  return "hard";
}

// ------------------------------------------------------------------ entry point

export function policy(
  learner: LearnerState,
  session: SessionState,
  lastEvent: PolicyEvent | null,
): Action {
  const before = session.phase;
  if (lastEvent !== null && lastEvent.type === "request_hint") lastEvent.type = "request_help";
  session.last_event = lastEvent;
  session.last_correct = null;
  session.last_diagnosis = null;
  const action = policyInner(learner, session, lastEvent, before);
  if (action.type === "end_session") rateSession(learner, session);
  return action;
}

function policyInner(
  learner: LearnerState,
  session: SessionState,
  lastEvent: PolicyEvent | null,
  before: string,
): Action {
  if (lastEvent && lastEvent.latency_ms !== undefined && lastEvent.latency_ms !== null) {
    session.active_ms += Math.min(lastEvent.latency_ms, LATENCY_CAP_MS);
    session.last_active_at = session.now;
  }
  const finishing =
    lastEvent && lastEvent.type === "show_solution" && session.hint_level_shown >= 2;
  if (lastEvent && lastEvent.type !== "answer" && lastEvent.type !== "resume" && !finishing) {
    if (hardCap(session) || softCap(session)) {
      const reason = hardCap(session) ? "hard_cap" : "soft_cap";
      return annotate(endForCap(learner, session, reason), session, before, lastEvent);
    }
  }
  if (session.consent_revoked || (lastEvent && lastEvent.type === "consent_revoked")) {
    return annotate(end(session, "consent_revoked", false), session, before, lastEvent);
  }
  if (lastEvent && lastEvent.type === "resume") {
    session.phase = session.current_item_id ? "practice" : "start";
    session.ended_reason = null;
    if (session.last_action && session.last_action.type !== "end_session") {
      return annotate(session.last_action, session, before, lastEvent);
    }
    return annotate(
      makeAction("show_item", { item_id: session.current_item_id }),
      session,
      before,
      lastEvent,
    );
  }
  if (idleExpired(session, lastEvent)) {
    return annotate(end(session, "idle", true), session, before, lastEvent);
  }
  if (session.phase === "ended") {
    return annotate(
      makeAction("end_session", { ended_reason: session.ended_reason, resumable: true }),
      session,
      before,
      lastEvent,
    );
  }
  if (lastEvent && lastEvent.type === "idle_nudge") {
    return annotate(
      keep(session, makeAction("nudge", { item_id: session.current_item_id })),
      session,
      before,
      lastEvent,
    );
  }
  if (session.session_type !== "practice") {
    return annotate(flag(session, "online_only_session"), session, before, lastEvent);
  }
  return annotate(practice(learner, session, lastEvent), session, before, lastEvent);
}

function practice(learner: LearnerState, session: SessionState, event: PolicyEvent | null): Action {
  if (event === null) return enterPracticeLoop(learner, session);
  if (event.type === "predict_response") {
    session.phase = "worked_example";
    const item = itemById(session);
    return keep(
      session,
      makeAction("worked_example", {
        item_id: session.current_item_id,
        skill_id: session.current_skill,
        text: item ? item.authored_explanation : "",
      }),
    );
  }
  if (event.type === "continue") return onContinue(learner, session);
  if (event.type === "request_help") return onHint(learner, session);
  if (event.type === "break_choice") return onBreakChoice(learner, session, event);
  if (event.type === "stuck_choice") return onStuckChoice(learner, session, event);
  if (event.type === "stuck_step") return onStuckStep(learner, session, event);
  if (event.type === "show_solution") return onShowSolution(session);
  if (event.type === "answer") return onAnswer(learner, session, event);
  if (event.type === "explain_back") return onExplainBack(session, event);
  return enterPracticeLoop(learner, session);
}

function enterPracticeLoop(learner: LearnerState, session: SessionState): Action {
  if (hardCap(session)) return endForCap(learner, session, "hard_cap");
  if (softCap(session)) return endForCap(learner, session, "soft_cap");
  if (!session.warmup_done) {
    const due = dueSkills(learner, session);
    if (due.length) {
      session.warmup_done = true;
      session.warmup_left = Math.min(MAX_WARMUP, due.length);
      return showWarmup(learner, session, due);
    }
    session.warmup_done = true;
  }
  return selectSkillOrItem(learner, session);
}

function onContinue(learner: LearnerState, session: SessionState): Action {
  if (session.phase === "representation") {
    const target = session.probe_for || session.current_skill;
    session.probe_for = null;
    return showPractice(learner, session, target);
  }
  if (session.phase === "worked_example") {
    lessonComplete(learner, session);
    return showPractice(learner, session, session.current_skill);
  }
  if (session.phase === "reveal") return similarItem(learner, session);
  if (session.phase === "explain_back") return selectSkillOrItem(learner, session);
  return enterPracticeLoop(learner, session);
}

function onHint(learner: LearnerState, session: SessionState): Action {
  const item = itemById(session);
  if (item === null) return enterPracticeLoop(learner, session);
  if (session.phase === "probe") return flag(session, "no_help_in_probe");
  if (session.phase === "stuck" || session.phase === "stuck_step") {
    return keep(session, stuckPointAction(session, item));
  }
  if (
    session.stuck_item_id !== item.id &&
    session.last_wrong_item_id !== item.id &&
    session.hint_level_shown === 0
  ) {
    return askStuckPoint(learner, session, item);
  }
  if (session.hint_level_shown >= 2) {
    session.phase = "practice";
    return keep(session, makeAction("show_item", { item_id: item.id, skill_id: primarySkill(item) }));
  }
  return deliverHint(learner, session, item);
}

function stuckChoices(item: CatalogItem): string[] {
  return STUCK_CHOICES.filter(
    (choice) =>
      (choice !== "step" || item.step_hints.length > 0) &&
      (choice !== "restate" || !!item.hint_restate),
  );
}

function stuckPointAction(_session: SessionState, item: CatalogItem): Action {
  return makeAction("ask_stuck_point", {
    item_id: item.id,
    skill_id: primarySkill(item),
    extras: { choices: stuckChoices(item), step_count: item.step_hints.length },
  });
}

function askStuckPoint(learner: LearnerState, session: SessionState, item: CatalogItem): Action {
  maybeBkt(learner, session, item, "request_hint", false);
  maybeLadder(learner, session, item, KIND_HINT, null);
  noteItemSeen(session, item);
  session.stuck_item_id = item.id;
  session.help_without_attempt += 1;
  if (session.help_without_attempt >= HELP_WITHOUT_ATTEMPT_LIMIT) return offerBreak(session);
  session.phase = "stuck";
  return keep(session, stuckPointAction(session, item));
}

function onStuckChoice(learner: LearnerState, session: SessionState, event: PolicyEvent): Action {
  const item = itemById(session);
  if (session.phase !== "stuck" || item === null) return flag(session, "not_in_stuck_picker");
  const choice = (event.response ?? "").trim();
  const offered = stuckChoices(item);
  if (!offered.includes(choice)) return flag(session, "bad_choice");
  if (choice === "start") {
    if (session.hint_level_shown >= 2) {
      session.phase = "practice";
      return keep(
        session,
        makeAction("show_item", { item_id: item.id, skill_id: primarySkill(item) }),
      );
    }
    return deliverHint(learner, session, item);
  }
  if (choice === "step") {
    session.phase = "stuck_step";
    return keep(
      session,
      makeAction("ask_stuck_step", {
        item_id: item.id,
        skill_id: primarySkill(item),
        extras: { step_count: item.step_hints.length },
      }),
    );
  }
  if (choice === "restate") {
    session.phase = "practice";
    return keep(
      session,
      makeAction("hint", {
        item_id: item.id,
        skill_id: primarySkill(item),
        text: item.hint_restate,
        source: "authored",
        extras: { kind: "restate" },
      }),
    );
  }
  session.phase = "practice";
  if (session.last_wrong_item_id === item.id) return checkYourWork(session, item, "recheck");
  return keep(
    session,
    makeAction("show_item", {
      item_id: item.id,
      skill_id: primarySkill(item),
      extras: { prompt_submit: true },
    }),
  );
}

function pythonInt(text: string): number | null {
  const t = text.trim();
  return /^[+-]?\d+$/.test(t) ? Number(t) : null;
}

function onStuckStep(_learner: LearnerState, session: SessionState, event: PolicyEvent): Action {
  const item = itemById(session);
  if (session.phase !== "stuck_step" || item === null) return flag(session, "not_in_stuck_picker");
  const index = pythonInt(event.response ?? "");
  if (index === null) return flag(session, "bad_step");
  if (!(index >= 0 && index < item.step_hints.length)) return flag(session, "bad_step");
  let text = item.step_hints[index];
  if (leakCheck(text, item.answer_sympy, 1)) text = hintText(item, 1);
  session.phase = "practice";
  return keep(
    session,
    makeAction("hint", {
      item_id: item.id,
      skill_id: primarySkill(item),
      text,
      source: "authored",
      extras: { kind: "step", step: index },
    }),
  );
}

function checkYourWork(session: SessionState, item: CatalogItem, kind: string): Action {
  session.phase = "practice";
  return keep(
    session,
    makeAction("check_your_work", {
      item_id: item.id,
      skill_id: primarySkill(item),
      extras: { check_kind: kind },
    }),
  );
}

function deliverHint(learner: LearnerState, session: SessionState, item: CatalogItem): Action {
  const lvl = session.hint_level_shown + 1;
  let text = hintText(item, lvl);
  if (leakCheck(text, item.answer_sympy, lvl)) text = hintText(item, lvl);
  maybeBkt(learner, session, item, "request_hint", false);
  if (session.last_event !== null && session.last_event.type === "request_help") {
    maybeLadder(learner, session, item, KIND_HINT, null);
  }
  session.hint_level_shown = lvl;
  session.phase = "practice";
  const misconception = matchMisconception(item, session.last_wrong_response ?? "");
  const targeted = session.misconception_text[misconception ?? ""];
  if (lvl === 1 && targeted && !leakCheck(targeted, item.answer_sympy, 1)) text = targeted;
  return keep(
    session,
    makeAction("hint", {
      item_id: item.id,
      skill_id: primarySkill(item),
      hint_level: lvl,
      misconception_id: misconception,
      text,
      source: "authored",
    }),
  );
}

function onShowSolution(session: SessionState): Action {
  if (session.hint_level_shown < 2) return flag(session, "illegal_reveal");
  return reveal(session);
}

// ------------------------------------------------------------------ answers

type Outcome = { first: boolean; correct: boolean; hinted: boolean; tier: string };

function judge(item: CatalogItem, response: string): boolean {
  return verifyResponse(response, {
    type: item.type,
    answer_sympy: item.answer_sympy,
    accept: item.accept,
    options: item.options,
  });
}

function onAnswer(learner: LearnerState, session: SessionState, event: PolicyEvent): Action {
  const item = itemById(session, event.item_id) ?? itemById(session);
  if (item === null) return onAnswerBase(learner, session, event);
  if (session.phase === "probe" && primarySkill(item) === session.probe_skill) {
    return answerProbe(learner, session, item, event);
  }
  const firstAnswer = !session.answered_items.has(item.id);
  const hinted =
    session.hint_level_shown > 0 ||
    session.stuck_item_id === item.id ||
    session.last_wrong_item_id === item.id;
  const tierBefore = itemTier(item.difficulty);
  const action = onAnswerBase(learner, session, event);
  if (action.rejected || session.last_correct === null) return action;
  const correct = !!session.last_correct;
  session.last_failure = !correct;
  if (firstAnswer) noteFirstAnswer(session, item, correct);
  return applyG2bRules(learner, session, item, action, {
    first: firstAnswer,
    correct,
    hinted,
    tier: tierBefore,
  });
}

function onAnswerBase(learner: LearnerState, session: SessionState, event: PolicyEvent): Action {
  const item = itemById(session, event.item_id) ?? itemById(session);
  if (item === null) return enterPracticeLoop(learner, session);
  const correct = judge(item, event.response ?? "");
  if (item.pool !== "practice") return flag(session, "checkpoint_item_in_practice");
  session.last_correct = correct;
  trackEngagement(session, item, event);
  session.last_diagnosis = classify(item, event.response ?? "", correct, learner, session);
  maybeBkt(learner, session, item, "answer", correct);
  maybeLadder(learner, session, item, KIND_ANSWER, correct);

  if (correct) {
    session.items_completed += 1;
    session.shown_item_ids.push(item.id);
    session.last_wrong_item_id = null;
    session.stuck_item_id = null;
    if (session.phase === "warmup") return selectSkillOrItem(learner, session);
    return afterCorrect(learner, session, item);
  }
  const firstAttempt = session.last_wrong_item_id !== item.id;
  session.last_wrong_response = event.response ?? "";
  session.last_wrong_item_id = item.id;
  if (
    firstAttempt &&
    session.hint_level_shown === 0 &&
    session.last_diagnosis !== null &&
    session.last_diagnosis.class === "slip"
  ) {
    return checkYourWork(session, item, String(session.last_diagnosis.detail));
  }
  if (session.hint_level_shown >= 2) {
    session.attempt_after_hint2 = true;
    return reveal(session);
  }
  return deliverHint(learner, session, item);
}

function noteItemSeen(session: SessionState, item: CatalogItem): void {
  if (!session.seen_items.has(item.id)) {
    session.seen_items.add(item.id);
    const skill = primarySkill(item);
    session.skill_items[skill] = (session.skill_items[skill] ?? 0) + 1;
  }
}

function noteFirstAnswer(session: SessionState, item: CatalogItem, correct: boolean): void {
  session.answered_items.add(item.id);
  noteItemSeen(session, item);
  const skill = primarySkill(item);
  session.wrong_first_streak[skill] = correct ? 0 : (session.wrong_first_streak[skill] ?? 0) + 1;
}

function wheelSpinning(learner: LearnerState, session: SessionState, skill: string): boolean {
  if (session.wheel_skills.has(skill) || ladderLevel(learner, skill) >= T_LEVEL) return false;
  return (
    (session.wrong_first_streak[skill] ?? 0) >= WHEEL_WRONG_STREAK ||
    (session.skill_items[skill] ?? 0) >= WHEEL_ITEM_LIMIT
  );
}

function applyG2bRules(
  learner: LearnerState,
  session: SessionState,
  item: CatalogItem,
  action: Action,
  outcome: Outcome,
): Action {
  const skill = primarySkill(item);
  updateRuns(session, skill, outcome);
  if (session.fast_streak >= FAST_STREAK_LIMIT && BREAK_REPLACES.has(action.type)) {
    return offerBreak(session);
  }
  let reason: string | null = null;
  if (wheelSpinning(learner, session, skill)) {
    session.wheel_skills.add(skill);
    reason = "wheel_spinning";
    if (session.teacher_share) session.alerts.push({ skill_id: skill, type: "wheel_spinning" });
  }
  const diagnosis = session.last_diagnosis;
  if (diagnosis && diagnosis.class === "prerequisite_gap" && diagnosis.detail) {
    reason = reason ?? "prerequisite_gap";
  }
  if (reason !== null && PROBE_REPLACES.has(action.type)) {
    const prereq = reason === "prerequisite_gap" && diagnosis ? diagnosis.detail : null;
    const probe = startProbe(learner, session, skill, prereq);
    if (probe !== null) return probe;
  }
  const next = challengeOrTierUp(learner, session, item, action, outcome);
  return maybePraise(session, item, next, outcome);
}

function updateRuns(session: SessionState, skill: string, outcome: Outcome): void {
  if (outcome.first) {
    session.wrong_run = outcome.correct ? 0 : session.wrong_run + 1;
    if (outcome.correct) {
      if (outcome.tier === "easy") session.skill_failed.delete(skill);
    } else {
      session.skill_failed.add(skill);
    }
  }
  const unhintedCorrect = outcome.first && outcome.correct && !outcome.hinted;
  session.unhinted_run = unhintedCorrect ? session.unhinted_run + 1 : 0;
  if (
    (session.reveals >= FRUSTRATION_REVEALS || session.wrong_run >= FRUSTRATION_WRONG_RUN) &&
    session.tier_down_items === 0
  ) {
    session.tier_down_items = STEP_DOWN_ITEMS;
    session.reveals = 0;
    session.wrong_run = 0;
  }
}

function effectiveTier(session: SessionState, wanted: string): string {
  let index = TIERS.includes(wanted) ? TIERS.indexOf(wanted) : 1;
  if (session.tier_down_items > 0) {
    session.tier_down_items -= 1;
    index = Math.max(0, index - 1);
  } else if (session.tier_up_next) {
    session.tier_up_next = false;
    index = Math.min(TIERS.length - 1, index + 1);
  }
  return TIERS[index];
}

function announceStepDown(session: SessionState, wanted: string, shifted: string): boolean {
  return (
    TIERS.indexOf(shifted) < TIERS.indexOf(wanted) &&
    session.tier_down_items === STEP_DOWN_ITEMS - 1
  );
}

function offerBreak(session: SessionState): Action {
  session.fast_streak = 0;
  session.help_without_attempt = 0;
  session.phase = "break_choice";
  const action = makeAction("break_or_switch", {
    item_id: session.current_item_id,
    skill_id: session.current_skill,
    extras: { choices: ["break", "switch", "continue"] },
  });
  action.rule_id = "R35";
  return keep(session, action);
}

function onBreakChoice(learner: LearnerState, session: SessionState, event: PolicyEvent): Action {
  if (session.phase !== "break_choice") return flag(session, "not_in_break_choice");
  const choice = (event.response ?? "").trim();
  if (!["break", "switch", "continue"].includes(choice)) return flag(session, "bad_choice");
  session.phase = "practice";
  const item = itemById(session);
  if (choice === "break") return end(session, "break", true);
  if (choice === "switch" && session.current_skill) {
    const skill = session.current_skill;
    session.blocked_skills.add(skill);
    const nxt = selectSkillOrItem(learner, session);
    if (!(nxt.type === "end_session" && nxt.ended_reason === "chapter_complete")) return nxt;
    session.blocked_skills.delete(skill);
    session.phase = "practice";
    session.ended_reason = null;
  }
  if (item === null) return enterPracticeLoop(learner, session);
  return keep(session, makeAction("show_item", { item_id: item.id, skill_id: primarySkill(item) }));
}

function challengeOrTierUp(
  learner: LearnerState,
  session: SessionState,
  item: CatalogItem,
  action: Action,
  outcome: Outcome,
): Action {
  if (session.unhinted_run < CHALLENGE_RUN) return action;
  session.unhinted_run = 0;
  if (outcome.tier !== "hard") {
    session.tier_up_next = true;
    if (action.type === "show_item" && Object.keys(action.extras).length === 0) {
      if (
        session.shown_item_ids.length &&
        session.shown_item_ids[session.shown_item_ids.length - 1] === action.item_id
      ) {
        session.shown_item_ids.pop();
      }
      return showPractice(learner, session, primarySkill(item));
    }
    return action;
  }
  if (action.type !== "show_item" && action.type !== "explain_back_prompt") return action;
  return challengeItem(session, primarySkill(item)) ?? action;
}

function challengeItem(session: SessionState, skill: string): Action | null {
  let picked = pickItem(session, skill, { pKnown: 0.9, preferTier: "hard", roles: ["transfer"] });
  if (picked === null || picked.role !== "transfer") {
    for (const other of session.overlay_skill_ids) {
      if (other === skill || session.blocked_skills.has(other)) continue;
      picked = pickItem(session, other, { pKnown: 0.9, preferTier: "hard", roles: ["transfer"] });
      if (picked !== null) break;
    }
  }
  if (picked === null) return null;
  session.current_skill = primarySkill(picked);
  session.current_item_id = picked.id;
  session.hint_level_shown = 0;
  session.attempt_after_hint2 = false;
  session.phase = "practice";
  session.shown_item_ids.push(picked.id);
  const action = makeAction("show_item", {
    item_id: picked.id,
    skill_id: primarySkill(picked),
    extras: { challenge: true },
  });
  action.rule_id = "R37";
  return keep(session, action);
}

function maybePraise(
  session: SessionState,
  item: CatalogItem,
  action: Action,
  outcome: Outcome,
): Action {
  if (!(outcome.first && outcome.correct) || outcome.tier === "easy") return action;
  if (session.items_completed - session.last_praise_at < PRAISE_GAP_ITEMS) return action;
  let trigger: string | null = null;
  if (outcome.tier === "hard" && !outcome.hinted) trigger = "hard_success";
  else if (session.skill_failed.has(primarySkill(item))) trigger = "recovery";
  session.skill_failed.delete(primarySkill(item));
  if (trigger === null || action.type === "end_session") return action;
  return attachPraise(session, action, trigger);
}

function attachPraise(session: SessionState, action: Action, trigger: string): Action {
  const options = VARIANTS[trigger];
  action.extras = {
    ...action.extras,
    encouragement: { trigger, variant: options[session.praise_count % options.length] },
  };
  session.last_praise_at = session.items_completed;
  session.praise_count += 1;
  return action;
}

function serveWin(session: SessionState): Action | null {
  const skills = [session.current_skill, ...session.overlay_skill_ids].filter(
    (s): s is string => !!s,
  );
  let item: CatalogItem | null = null;
  for (const skill of new Set(skills)) {
    item = pickItem(session, skill, { pKnown: 0.0, preferTier: "easy", roles: ["procedure"] });
    if (item !== null) break;
  }
  if (item === null) return null;
  session.win_served = true;
  session.phase = "practice";
  session.current_skill = primarySkill(item);
  session.current_item_id = item.id;
  session.hint_level_shown = 0;
  session.attempt_after_hint2 = false;
  session.shown_item_ids.push(item.id);
  const action = makeAction("show_item", {
    item_id: item.id,
    skill_id: primarySkill(item),
    extras: { win: true },
  });
  action.rule_id = "R40";
  return keep(session, action);
}

function endForCap(_learner: LearnerState, session: SessionState, reason: string): Action {
  if (session.last_failure && !session.win_served) {
    const win = serveWin(session);
    if (win !== null) return win;
  }
  const action = end(session, reason, false);
  if (!session.last_failure) attachPraise(session, action, "session_end");
  return action;
}

function lowestMasteryPrerequisite(
  learner: LearnerState,
  session: SessionState,
  target: string,
): string | null {
  const candidates = (session.prerequisites[target] ?? []).filter(
    (sid) =>
      !session.probe_done.has(sid) &&
      eligibleItems(session, sid, new Set()).some((row) => primarySkill(row) === sid),
  );
  if (!candidates.length) return null;
  return [...candidates].sort((a, b) => {
    const pa = pKnown(learner, a, session);
    const pb = pKnown(learner, b, session);
    return pa !== pb ? pa - pb : a < b ? -1 : a > b ? 1 : 0;
  })[0];
}

function startProbe(
  learner: LearnerState,
  session: SessionState,
  target: string,
  prereq: string | null,
): Action | null {
  if (prereq !== null && session.probe_done.has(prereq)) return null;
  const chosen = prereq || lowestMasteryPrerequisite(learner, session, target);
  const item = chosen
    ? pickItem(session, chosen, {
        pKnown: pKnown(learner, chosen, session),
        preferTier: "easy",
        roles: ["procedure"],
      })
    : null;
  if (chosen === null || item === null) return changeRepresentation(session, target);
  session.probe_done.add(chosen);
  session.probe_skill = chosen;
  session.probe_for = target;
  session.phase = "probe";
  session.current_skill = chosen;
  session.current_item_id = item.id;
  session.hint_level_shown = 0;
  session.attempt_after_hint2 = false;
  session.shown_item_ids.push(item.id);
  const action = makeAction("show_item", {
    item_id: item.id,
    skill_id: chosen,
    extras: { probe: true, for_skill: target },
  });
  action.rule_id = "R33";
  return keep(session, action);
}

function changeRepresentation(session: SessionState, target: string): Action {
  session.phase = "representation";
  session.probe_for = target;
  session.current_skill = target;
  let current = itemById(session);
  if (current === null || primarySkill(current) !== target) {
    current = session.catalog.find((row) => primarySkill(row) === target) ?? null;
    session.current_item_id = current ? current.id : null;
  }
  const action = makeAction("worked_example", {
    item_id: session.current_item_id,
    skill_id: target,
    text: current ? current.authored_explanation : "",
    extras: { representation_change: true },
  });
  action.rule_id = "R33";
  return keep(session, action);
}

function answerProbe(
  learner: LearnerState,
  session: SessionState,
  item: CatalogItem,
  event: PolicyEvent,
): Action {
  const correct = judge(item, event.response ?? "");
  session.last_correct = correct;
  session.last_diagnosis = null;
  maybeBkt(learner, session, item, "answer", correct);
  maybeLadder(learner, session, item, KIND_ANSWER, correct);
  session.items_completed += 1;
  session.answered_items.add(item.id);
  noteItemSeen(session, item);
  const prereq = session.probe_skill;
  const target = session.probe_for;
  session.probe_skill = null;
  if (correct && target) return changeRepresentation(session, target);
  session.probe_for = null;
  session.phase = "practice";
  if (prereq) {
    session.scheduled_prereq = prereq;
    session.scheduled_left = 2;
  }
  return selectSkillOrItem(learner, session);
}

function trackEngagement(session: SessionState, item: CatalogItem, event: PolicyEvent): void {
  const fast =
    event.latency_ms !== undefined &&
    event.latency_ms !== null &&
    item.min_plausible_ms !== null &&
    event.latency_ms < item.min_plausible_ms;
  session.fast_streak = fast ? session.fast_streak + 1 : 0;
  session.help_without_attempt = 0;
}

function afterCorrect(learner: LearnerState, session: SessionState, item: CatalogItem): Action {
  const skill = primarySkill(item);
  const mastery = learner.mastery.get(skill);
  const firstUnhinted =
    mastery !== undefined &&
    mastery.unhinted_correct >= 1 &&
    session.hint_level_shown === 0 &&
    !session.explain_back_done.has(skill);
  const reached =
    mastery !== undefined &&
    mastery.p_known >= 0.95 &&
    mastery.unhinted_correct >= 3 &&
    !session.explain_back_done.has(skill);
  if (firstUnhinted || reached) {
    session.phase = "explain_back";
    session.explain_back_done.add(skill);
    return keep(
      session,
      makeAction("explain_back_prompt", {
        item_id: item.id,
        skill_id: skill,
        text: item.authored_explanation,
      }),
    );
  }
  return selectSkillOrItem(learner, session);
}

function onExplainBack(session: SessionState, event: PolicyEvent): Action {
  session.stored_explain_text = event.text ?? event.response ?? null;
  const item = itemById(session);
  session.phase = "select_skill";
  return keep(
    session,
    makeAction("explain_back_result", {
      item_id: session.current_item_id,
      skill_id: session.current_skill,
      text: item ? item.authored_explanation : "",
      grade: null,
      store_text: true,
      llm_called: false,
    }),
  );
}

function reveal(session: SessionState): Action {
  const item = itemById(session)!;
  const lead = hintText(item, 3);
  const body = item.solution_steps.join(" ");
  session.reveals += 1;
  session.phase = "reveal";
  session.similar_from_item_id = item.id;
  return keep(
    session,
    makeAction("reveal_solution", {
      item_id: item.id,
      skill_id: primarySkill(item),
      text: `${lead} ${body}`.trim(),
      extras: { hint3: lead },
    }),
  );
}

function similarItem(learner: LearnerState, session: SessionState): Action {
  const source = itemById(session, session.similar_from_item_id) ?? itemById(session);
  if (source === null) return selectSkillOrItem(learner, session);
  const sourceTier = itemTier(source.difficulty);
  const wanted = effectiveTier(session, sourceTier);
  const announce = announceStepDown(session, sourceTier, wanted);
  const nxt = pickItem(session, primarySkill(source), {
    pKnown: source.difficulty,
    exclude: new Set([source.id]),
    preferTier: wanted,
    roles: [source.role],
  });
  if (nxt === null) return contentGap(learner, session, primarySkill(source), wanted);
  session.current_item_id = nxt.id;
  session.current_skill = primarySkill(nxt);
  session.hint_level_shown = 0;
  session.attempt_after_hint2 = false;
  session.phase = "practice";
  session.shown_item_ids.push(nxt.id);
  return keep(
    session,
    makeAction("similar_item", {
      item_id: nxt.id,
      skill_id: primarySkill(nxt),
      extras: announce ? { support: "step_down" } : {},
    }),
  );
}

function selectSkillOrItem(learner: LearnerState, session: SessionState): Action {
  if (hardCap(session) || softCap(session)) {
    return endForCap(learner, session, hardCap(session) ? "hard_cap" : "soft_cap");
  }
  if (session.warmup_left > 0) {
    const due = dueSkills(learner, session);
    if (due.length) return showWarmup(learner, session, due);
    session.warmup_left = 0;
  }
  const stretch = stretchSkill(learner, session);
  if (stretch !== null) {
    session.stretch_served += 1;
    session.stretch_skills.add(stretch);
    session.introduced_skills.add(stretch);
    return showPractice(learner, session, stretch);
  }
  const skill = chooseSkill(learner, session);
  if (skill === null) {
    const done = end(session, "chapter_complete", false);
    if (!session.last_failure) attachPraise(session, done, "session_end");
    return done;
  }
  session.current_skill = skill;
  if (!session.introduced_skills.has(skill)) {
    session.phase = "predict";
    session.lesson_prereq_levels[skill] = (session.prerequisites[skill] ?? []).map((sid) =>
      ladderLevel(learner, sid),
    );
    return keep(
      session,
      makeAction("predict", { skill_id: skill, item_id: null, text: predictionFor(session, skill) }),
    );
  }
  return showPractice(learner, session, skill);
}

function showPractice(learner: LearnerState, session: SessionState, skill: string | null): Action {
  if (skill === null) return end(session, "chapter_complete", false);
  const wanted = itemTier(pKnown(learner, skill, session));
  const [roles, required] = rolesFor(learner, session, skill);
  const shifted = effectiveTier(session, wanted);
  const announce = announceStepDown(session, wanted, shifted);
  const item = pickItem(session, skill, {
    pKnown: pKnown(learner, skill, session),
    roles,
    preferTier: shifted !== wanted ? shifted : null,
  });
  if (item === null) return contentGap(learner, session, skill, wanted);
  if (required && item.role !== roles[0]) logRoleGap(session, skill, roles[0], wanted);
  session.introduced_skills.add(skill);
  session.current_skill = skill;
  session.current_item_id = item.id;
  session.hint_level_shown = 0;
  session.attempt_after_hint2 = false;
  session.phase = "practice";
  session.shown_item_ids.push(item.id);
  const extras = announce ? { support: "step_down" } : {};
  return keep(session, makeAction("show_item", { item_id: item.id, skill_id: skill, extras }));
}

function showWarmup(learner: LearnerState, session: SessionState, due: string[]): Action {
  const skill = due[0];
  const item = pickItem(session, skill, {
    pKnown: pKnown(learner, skill, session),
    roles: warmupRoles(learner, skill),
  });
  if (item === null) {
    session.warmup_left = 0;
    return selectSkillOrItem(learner, session);
  }
  session.warmup_left = Math.max(0, session.warmup_left - 1);
  session.current_skill = skill;
  session.current_item_id = item.id;
  session.phase = "warmup";
  session.shown_item_ids.push(item.id);
  return keep(
    session,
    makeAction("warmup_item", { item_id: item.id, skill_id: skill, extras: { warmup: true } }),
  );
}

// ------------------------------------------------------------------ choosing

function ladderLevel(learner: LearnerState, skillId: string): number {
  const row = learner.ladders.get(skillId);
  return row ? ladderLevelOf(row) : 0;
}

function byPKnownThenId(learner: LearnerState, session: SessionState) {
  return (a: string, b: string) => {
    const pa = pKnown(learner, a, session);
    const pb = pKnown(learner, b, session);
    return pa !== pb ? pa - pb : a < b ? -1 : a > b ? 1 : 0;
  };
}

function chooseSkill(learner: LearnerState, session: SessionState): string | null {
  const scheduled = session.scheduled_prereq;
  if (scheduled && session.scheduled_left > 0) {
    session.scheduled_left -= 1;
    if (session.scheduled_left === 0) session.scheduled_prereq = null;
    return scheduled;
  }
  session.scheduled_prereq = null;
  session.scheduled_left = 0;
  let target: string | null = null;
  for (const skillId of session.overlay_skill_ids) {
    if (session.blocked_skills.has(skillId)) continue;
    if (ladderLevel(learner, skillId) < T_LEVEL) {
      target = skillId;
      break;
    }
  }
  if (target === null) return extensionSkill(learner, session);
  const weak = (session.prerequisites[target] ?? []).filter(
    (sid) => pKnown(learner, sid, session) < PREREQ_BELOW,
  );
  if (weak.length) return [...weak].sort(byPKnownThenId(learner, session))[0];
  return target;
}

function stretchSkill(learner: LearnerState, session: SessionState): string | null {
  if (session.session_type !== "practice" || session.stretch_served >= MAX_STRETCH_PER_SESSION) {
    return null;
  }
  for (const skillId of session.overlay_skill_ids) {
    if (session.blocked_skills.has(skillId) || session.stretch_skills.has(skillId)) continue;
    const ladder = learner.ladders.get(skillId);
    if (ladder === undefined || !(ladderLevelOf(ladder) in EXTENSION_ROLE)) continue;
    const lvl = ladderLevelOf(ladder);
    const due = ladder.flags[`stretch_after_${lvl}`];
    if (!due || parseAt(String(due)) > session.now) continue;
    const role = EXTENSION_ROLE[lvl];
    if (eligibleItems(session, skillId, new Set()).some((row) => row.role === role)) return skillId;
  }
  return null;
}

function extensionSkill(learner: LearnerState, session: SessionState): string | null {
  for (const skillId of session.overlay_skill_ids) {
    if (session.blocked_skills.has(skillId)) continue;
    const role = EXTENSION_ROLE[ladderLevel(learner, skillId)];
    if (role === undefined) continue;
    if (eligibleItems(session, skillId, new Set()).some((row) => row.role === role)) {
      session.introduced_skills.add(skillId);
      return skillId;
    }
    logRoleGap(session, skillId, role, itemTier(pKnown(learner, skillId, session)));
  }
  return null;
}

function rolesFor(
  learner: LearnerState,
  session: SessionState,
  skill: string,
): [string[], boolean] {
  const ladder = learner.ladders.get(skill);
  const lvl = ladder ? ladderLevelOf(ladder) : 0;
  if (lvl === 4) return [["apply", "procedure"], true];
  if (lvl === 5) return [["transfer", "procedure"], true];
  if (!(ladder ? ladder.achieved : []).includes(2) && lvl < T_LEVEL) {
    const shown = session.shown_item_ids.filter((id) => {
      const row = itemById(session, id);
      return row !== null && primarySkill(row) === skill;
    }).length;
    const slot = shown % 4;
    if (slot === 1) return [["recall", "procedure"], false];
    if (slot === 3) return [["explain", "procedure"], false];
  }
  return [["procedure"], true];
}

function warmupRoles(learner: LearnerState, skill: string): string[] {
  const lvl = ladderLevel(learner, skill);
  if (lvl === 4) return ["apply", "procedure"];
  if (lvl === 5) return ["transfer", "procedure"];
  return ["procedure"];
}

function logRoleGap(session: SessionState, skill: string, role: string, tier: string): void {
  if (session.content_gaps.some((g) => g.skill === skill && g.role === role)) return;
  session.content_gaps.push({
    skill,
    tier,
    role,
    item_ids_seen: [...session.shown_item_ids],
    reason: "role_missing",
  });
}

function contentGap(
  learner: LearnerState,
  session: SessionState,
  skill: string,
  tier: string,
): Action {
  const gap = { skill, tier, item_ids_seen: [...session.shown_item_ids] };
  session.content_gaps.push(gap);
  session.blocked_skills.add(skill);
  session.phase = "start";
  const action = makeAction("content_gap", { skill_id: skill, extras: { ...gap } });
  session.last_action = action;
  const follow = selectSkillOrItem(learner, session);
  follow.extras = { ...follow.extras, content_gap: gap };
  return follow;
}

function eligibleItems(session: SessionState, skill: string, skip: Set<string>): CatalogItem[] {
  return session.catalog.filter(
    (row) =>
      row.pool === "practice" &&
      primarySkill(row) === skill &&
      !skip.has(row.id) &&
      row.status !== "retired" &&
      (row.status === "approved" || session.allow_draft),
  );
}

function pickItem(
  session: SessionState,
  skill: string,
  opts: {
    pKnown: number;
    exclude?: Set<string>;
    preferTier?: string | null;
    roles?: string[];
  },
): CatalogItem | null {
  const wanted = opts.preferTier || itemTier(opts.pKnown);
  let eligible = eligibleItems(session, skill, opts.exclude ?? new Set());
  for (const role of opts.roles ?? []) {
    const roleRows = eligible.filter((row) => row.role === role);
    if (roleRows.length) {
      eligible = roleRows;
      break;
    }
  }
  const leftover = eligible.filter((row) => !session.shown_item_ids.includes(row.id));
  const pool = leftover.length ? leftover : eligible;
  if (!pool.length) return null;
  const inTier = pool.filter((row) => itemTier(row.difficulty) === wanted);
  const chosen = [...(inTier.length ? inTier : nearestTier(pool, wanted))];
  chosen.sort((a, b) => {
    const [sa, ta] = shownKey(a);
    const [sb, tb] = shownKey(b);
    if (sa !== sb) return sa - sb;
    if (ta !== tb) return ta - tb;
    if (a.difficulty !== b.difficulty) return a.difficulty - b.difficulty;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
  return chosen[0];
}

function nearestTier(pool: CatalogItem[], wanted: string): CatalogItem[] {
  const order = ["easy", "medium", "hard"];
  const idx = order.includes(wanted) ? order.indexOf(wanted) : 1;
  const neighbors: string[] = [];
  if (idx > 0) neighbors.push(order[idx - 1]);
  if (idx + 1 < order.length) neighbors.push(order[idx + 1]);
  if (idx === 2) neighbors.push("easy");
  for (const tier of neighbors) {
    const rows = pool.filter((row) => itemTier(row.difficulty) === tier);
    if (rows.length) return rows;
  }
  return pool;
}

function shownKey(item: CatalogItem): [number, number] {
  return item.last_shown_at === null ? [0, 0] : [1, item.last_shown_at];
}

function pKnown(learner: LearnerState, skillId: string, session: SessionState): number {
  const row = learner.mastery.get(skillId);
  if (row !== undefined) return row.p_known;
  return (session.bkt_params[skillId] ?? DEFAULT_BKT).p_init;
}

function dueSkills(learner: LearnerState, session: SessionState): string[] {
  const due: string[] = [];
  for (const [skillId, card] of learner.cards) {
    if (card.due.getTime() <= session.now) due.push(skillId);
  }
  return due.slice(0, MAX_WARMUP);
}

// ------------------------------------------------------------------ learner updates

function maybeBkt(
  learner: LearnerState,
  session: SessionState,
  item: CatalogItem,
  eventType: string,
  correct: boolean,
): void {
  const params: Record<string, typeof DEFAULT_BKT> = {};
  for (const sid of new Set([primarySkill(item), ...session.overlay_skill_ids])) {
    params[sid] = session.bkt_params[sid] ?? DEFAULT_BKT;
  }
  applyMastery(
    learner,
    {
      item_id: item.id,
      skill_id: primarySkill(item),
      event_type: eventType,
      correct,
      pool: session.phase === "warmup" ? "warmup" : session.session_type,
      session_id: sessionKey(session),
      is_warmup: session.phase === "warmup",
      at: session.now,
    },
    params,
    session.bkt_memory,
  );
}

function eventId(session: SessionState): string {
  const event = session.last_event;
  if (event !== null && event.event_id) return event.event_id;
  session.event_counter += 1;
  return `auto-${session.event_counter}`;
}

function maybeLadder(
  learner: LearnerState,
  session: SessionState,
  item: CatalogItem,
  kind: string,
  correct: boolean | null,
): void {
  if (session.session_type !== "practice") return;
  const skill = primarySkill(item);
  const row = learner.mastery.get(skill);
  const known = row !== undefined ? row.p_known : pKnown(learner, skill, session);
  applyLadderEvent(
    learner.ladders,
    {
      event_id: eventId(session),
      skill_id: skill,
      kind,
      at: session.now,
      item_id: item.id,
      correct,
      pool: session.phase === "warmup" ? "warmup" : "practice",
      role: item.role,
      structure: item.structure,
    },
    known,
  );
}

function lessonComplete(learner: LearnerState, session: SessionState): void {
  const skill = session.current_skill;
  if (skill === null || session.session_type !== "practice") return;
  const params = session.bkt_params[skill] ?? DEFAULT_BKT;
  if (!learner.mastery.has(skill)) {
    learner.mastery.set(skill, {
      skill_id: skill,
      p_known: params.p_init,
      attempts: 0,
      unhinted_correct: 0,
      hinted_correct: 0,
    });
  }
  applyLadderEvent(
    learner.ladders,
    { event_id: eventId(session), skill_id: skill, kind: KIND_LESSON, at: session.now },
    0.0,
  );
}

function sessionKey(session: SessionState): string {
  return session.session_key || "session";
}

function rateSession(learner: LearnerState, session: SessionState): void {
  if (session.session_type !== "practice" || session.ended_reason === "consent_revoked") return;
  const key = sessionKey(session);
  applyMastery(
    learner,
    { item_id: "", skill_id: "", event_type: "session_end", session_id: key, at: session.now },
    {},
    session.bkt_memory,
  );
  session.bkt_memory.session_unhinted.delete(key);
}

function matchMisconception(item: CatalogItem, response: string): string | null {
  const text = response.trim();
  for (const [mid, answers] of item.misconception_rules) {
    if (answers.includes(text)) return mid;
  }
  return null;
}

function predictionFor(session: SessionState, skill: string): string {
  for (const row of session.catalog) {
    if (primarySkill(row) === skill && row.prediction_prompt) return row.prediction_prompt;
  }
  return "What do you think the first step is?";
}

function idleExpired(session: SessionState, event: PolicyEvent | null): boolean {
  if (event && event.idle_ms !== undefined && event.idle_ms !== null && event.idle_ms >= IDLE_END_MS) {
    return true;
  }
  if (session.last_active_at === null) return false;
  return session.now - session.last_active_at >= IDLE_END_MS;
}

const softCap = (s: SessionState) => s.active_ms >= s.soft_active_ms || s.items_completed >= s.soft_item_cap;
const hardCap = (s: SessionState) => s.active_ms >= s.hard_active_ms;

function end(session: SessionState, reason: string, resumable: boolean): Action {
  session.phase = "ended";
  session.ended_reason = reason;
  return keep(session, makeAction("end_session", { ended_reason: reason, resumable }));
}

function flag(session: SessionState, flagName: string): Action {
  return keep(
    session,
    makeAction(session.last_action ? session.last_action.type : "show_item", {
      item_id: session.current_item_id,
      skill_id: session.current_skill,
      guardrail_flag: flagName,
      rejected: true,
    }),
  );
}

function keep(session: SessionState, action: Action): Action {
  session.last_action = action;
  session.llm_called = session.llm_called || action.llm_called;
  return action;
}

function annotate(
  action: Action,
  session: SessionState,
  before: string,
  event: PolicyEvent | null,
): Action {
  const ev = event ? event.type : "start";
  action.state_before = before;
  action.state_after = session.phase;
  action.rule_id = action.rule_id || ruleIdFor(before, ev, action.type);
  session.last_action = action;
  return action;
}
