import type { Frac } from "./frac";
import type { QNum } from "./surd";

/** Parsed expression tree. Numbers are exact. */
export type Ast =
  | { t: "num"; v: Frac }
  | { t: "var"; name: string }
  | { t: "neg"; a: Ast }
  | { t: "sqrt"; a: Ast }
  | { t: "bin"; op: "+" | "-" | "*" | "/" | "^"; a: Ast; b: Ast };

export type ParseFail =
  | "parse"
  | "function"
  | "multi_unknown"
  | "too_big"
  | "irrational"
  | "nonlinear"
  | "div_zero"
  | "rational_function"
  | "inequality"
  | "word_problem";

export type MathKind = "arith" | "poly_eq" | "linear_system" | "poly_simplify";

/**
 * What the device understood. Plain data (strings only), so it can be shown, compared and, later and only after the
 * student confirms it, sent as `doubt-expr/1`. The unknown is always canonical `x` (and `y`) in the `*Text` and
 * coefficient fields; `display` keeps the student's own letters.
 */
export type MathCandidate = {
  schema: "doubt-expr/1";
  kind: MathKind;
  /** The student's letter for the unknown ("x" when there is none). For a system, the two letters joined: "xy". */
  variable: string;
  display: string;
  /** arith and poly_simplify: canonical explicit text (`2*(3+4)`, `(x+1)^2`). */
  expr?: string;
  /** arith only: the value the student wrote after "=", when there was one. */
  claimed?: string;
  /** poly_eq: canonical text of each side, and each side as coefficients (lowest degree first). */
  lhsText?: string;
  rhsText?: string;
  lhs?: string[];
  rhs?: string[];
  /** linear_system: two equations in x and y: a*x + b*y = c. */
  system?: { coeffs: string[][]; consts: string[]; texts: string[] };
};

export type Detect =
  | { kind: "candidate"; candidate: MathCandidate }
  | { kind: "unsupported"; why: ParseFail }
  | { kind: "none" };

export type RuleId =
  | "write_equation"
  | "expand_bracket"
  | "collect_like_terms"
  | "add_both_sides"
  | "subtract_both_sides"
  | "multiply_both_sides"
  | "divide_both_sides"
  | "write_standard_form"
  | "factor_quadratic"
  | "zero_product"
  | "rational_root"
  | "discriminant"
  | "quadratic_formula"
  | "simplify_surd"
  | "no_real_roots"
  | "no_solution"
  | "identity"
  | "eval_operation"
  | "eliminate_unknown"
  | "solve_one_unknown"
  | "substitute_back"
  | "substitute_check"
  | "state_result";

export type Step = { rule: RuleId; args: Record<string, string>; before: string; after: string };

export type SolutionStatus = "solved" | "no_solution" | "identity" | "unsupported";

export type Answer =
  /** Exact rational answers (roots, or the single numeric value), ascending. */
  | { kind: "values"; values: string[] }
  /** Roots including irrational ones: `values` rational roots, `surds` canonical "p+q√d" forms. */
  | { kind: "surd"; values: string[]; surds: string[] }
  /** poly_simplify: the simplified polynomial (canonical coefficient strings, lowest degree first) and its display. */
  | { kind: "expr"; value: string; coeffs: string[] }
  /** linear_system: the unique pair. */
  | { kind: "pair"; x: string; y: string }
  | { kind: "none" };

export type Solution = {
  status: SolutionStatus;
  why?: string;
  answer: Answer;
  steps: Step[];
  /** Exact substitution of every root back into the original equation passed. */
  checked: { by: "substitution"; exact: true; ok: boolean };
  /** Every answer as an exact number (roots, the value, or x then y). Internal; not serialised. */
  exact: QNum[];
  /** arith with a claimed value: whether the student's statement is true. */
  claimTrue?: boolean;
  /** Closed registry id, device only. */
  misconceptionTag: string | null;
};
