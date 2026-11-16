import { HINT_COPY, LABELS } from "./copy.en";
import { type AnswerSet, answerSetFor, hintLeaks } from "./leak";
import { Poly } from "./poly";
import { describeAnswer, renderSteps, stateAfter } from "./steps";
import type { MathCandidate, RuleId, Solution } from "./types";

/**
 * The four-level hint ladder:
 *   1 strategy in words, 2 the next operation (not its result), 3 the first step's lead-in, 4 the full steps.
 * Levels 1 to 3 are checked by the leak filter and never contain a root or the final value. A text that fails is
 * dropped for the next, plainer candidate; if none passes the level is left out.
 */

export type LadderLevel = { level: 1 | 2 | 3 | 4; id: string; text: string; fallback: boolean };
export type Ladder = { levels: LadderLevel[]; answers: AnswerSet | null };

type Cand = { id: string; text: string; allowedStates?: string[] };

function degreeOf(c: MathCandidate): number {
  if (!c.lhs || !c.rhs) return 0;
  const l = Poly.parseCoeffs(c.lhs);
  const r = Poly.parseCoeffs(c.rhs);
  return l && r ? l.sub(r).degree : 0;
}

function strategy(c: MathCandidate): Cand[] {
  const v = c.variable;
  switch (c.kind) {
    case "arith":
      return [{ id: "hint.strategy.arith", text: HINT_COPY.strategy.arith() }];
    case "poly_simplify":
      return [{ id: "hint.strategy.simplify", text: HINT_COPY.strategy.simplify() }];
    case "linear_system":
      return [{ id: "hint.strategy.system", text: HINT_COPY.strategy.system() }];
    case "poly_eq": {
      const d = degreeOf(c);
      if (d <= 1) return [{ id: "hint.strategy.linear", text: HINT_COPY.strategy.linear(v) }];
      if (d === 2)
        return [
          { id: "hint.strategy.quadratic", text: HINT_COPY.strategy.quadratic() },
          { id: "hint.strategy.quadratic_plain", text: HINT_COPY.strategy.quadraticPlain() },
        ];
      return [{ id: "hint.strategy.polynomial", text: HINT_COPY.strategy.polynomial() }];
    }
  }
}

function nextOperation(c: MathCandidate, sol: Solution): Cand[] {
  const n = HINT_COPY.nextStep;
  const first = sol.steps[0];
  const generic: Cand = { id: "hint.next.generic", text: n.undoGeneric() };
  if (!first) return [generic];
  const a = first.args;
  const by: Partial<Record<RuleId, Cand[]>> = {
    expand_bracket: [{ id: "hint.next.tidy", text: n.tidy() }],
    collect_like_terms: [{ id: "hint.next.tidy", text: n.tidy() }],
    subtract_both_sides: [
      { id: "hint.next.subtract", text: n.undoAdd(a.amount ?? "") },
      { id: "hint.next.unknown_generic", text: /[a-z]/.test(a.amount ?? "") ? n.unknownGeneric() : n.undoGeneric() },
    ],
    add_both_sides: [
      { id: "hint.next.add", text: n.undoSub(a.amount ?? "") },
      { id: "hint.next.unknown_generic", text: /[a-z]/.test(a.amount ?? "") ? n.unknownGeneric() : n.undoGeneric() },
    ],
    multiply_both_sides: a.which
      ? [{ id: "hint.next.eliminate", text: n.eliminate() }]
      : [
          { id: "hint.next.multiply", text: n.multiply(a.factor ?? "") },
          { id: "hint.next.scale", text: n.scale() },
        ],
    divide_both_sides: [
      { id: "hint.next.divide", text: n.divide(a.factor ?? "") },
      { id: "hint.next.divide_generic", text: n.divideGeneric() },
    ],
    write_standard_form: [{ id: "hint.next.standard_form", text: n.standardForm() }],
    factor_quadratic: [{ id: "hint.next.factor", text: n.factor() }],
    discriminant: [{ id: "hint.next.discriminant", text: n.discriminant() }],
    rational_root: [{ id: "hint.next.rational_root", text: n.rationalRoot() }],
    eval_operation: [
      { id: "hint.next.arith", text: n.arith(a.a ?? "", a.op ?? "", a.b ?? "") },
      { id: "hint.next.arith_generic", text: n.arithGeneric() },
    ],
    eliminate_unknown: [{ id: "hint.next.eliminate", text: n.eliminate() }],
  };
  return [...(by[first.rule] ?? []), generic];
}

const LEAD_IN_SAFE: RuleId[] = [
  "expand_bracket",
  "collect_like_terms",
  "write_standard_form",
  "add_both_sides",
  "subtract_both_sides",
  "multiply_both_sides",
  "divide_both_sides",
  "eval_operation",
  "eliminate_unknown",
];

function leadIn(sol: Solution): Cand[] {
  const first = sol.steps[0];
  const generic: Cand = { id: "hint.lead.generic", text: HINT_COPY.leadIn.generic() };
  if (first && LEAD_IN_SAFE.includes(first.rule)) {
    const st = stateAfter(sol.steps, 0);
    if (st && !st.includes(";")) return [{ id: "hint.lead.state", text: HINT_COPY.leadIn.state(st), allowedStates: [st] }, generic];
  }
  return [generic];
}

export function buildLadder(c: MathCandidate, sol: Solution): Ladder {
  if (sol.status === "unsupported") return { levels: [], answers: null };
  const answers = answerSetFor(c, sol);
  const levels: LadderLevel[] = [];
  const pick = (level: 1 | 2 | 3, cands: Cand[]) => {
    for (let i = 0; i < cands.length; i++) {
      const cand = cands[i];
      const verdict = hintLeaks(cand.text, level, answers, { allowedStates: cand.allowedStates });
      if (!verdict.leaks) {
        levels.push({ level, id: cand.id, text: cand.text, fallback: i > 0 });
        return;
      }
    }
  };
  pick(1, strategy(c));
  pick(2, nextOperation(c, sol));
  pick(3, leadIn(sol));
  const letters = c.kind === "linear_system" ? c.variable : c.kind === "poly_eq" ? c.variable : "";
  const lines = renderSteps(sol.steps);
  const closing = sol.status === "solved" ? describeAnswer(sol, letters) : HINT_COPY.noSolution;
  levels.push({
    level: 4,
    id: "hint.full_steps",
    text: [HINT_COPY.stepsHeader, ...lines.map((l, i) => `${i + 1}. ${l}`), closing, LABELS.device]
      .filter(Boolean)
      .join("\n"),
    fallback: false,
  });
  return { levels, answers };
}
