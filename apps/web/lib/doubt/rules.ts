import type { MathKind, RuleId } from "./types";

/**
 * The closed rule table. Every step the solver writes names one of these ids; the wording lives in copy.en.ts, keyed
 * by id. Nothing here moves a term "across" an equals sign: the only way to change a side is to do the same operation
 * to both sides (inverse operations), or to rewrite one side without changing its value.
 */
export const RULE_TABLE: Record<RuleId, { classes: MathKind[]; sameBothSides: boolean }> = {
  write_equation: { classes: ["poly_eq", "linear_system"], sameBothSides: false },
  expand_bracket: { classes: ["poly_eq", "poly_simplify"], sameBothSides: false },
  collect_like_terms: { classes: ["poly_eq", "poly_simplify"], sameBothSides: false },
  add_both_sides: { classes: ["poly_eq", "linear_system"], sameBothSides: true },
  subtract_both_sides: { classes: ["poly_eq", "linear_system"], sameBothSides: true },
  multiply_both_sides: { classes: ["poly_eq", "linear_system"], sameBothSides: true },
  divide_both_sides: { classes: ["poly_eq", "linear_system"], sameBothSides: true },
  write_standard_form: { classes: ["poly_eq"], sameBothSides: true },
  factor_quadratic: { classes: ["poly_eq"], sameBothSides: false },
  zero_product: { classes: ["poly_eq"], sameBothSides: false },
  rational_root: { classes: ["poly_eq"], sameBothSides: false },
  discriminant: { classes: ["poly_eq"], sameBothSides: false },
  quadratic_formula: { classes: ["poly_eq"], sameBothSides: false },
  simplify_surd: { classes: ["poly_eq"], sameBothSides: false },
  no_real_roots: { classes: ["poly_eq"], sameBothSides: false },
  no_solution: { classes: ["poly_eq", "linear_system"], sameBothSides: false },
  identity: { classes: ["poly_eq"], sameBothSides: false },
  eval_operation: { classes: ["arith"], sameBothSides: false },
  eliminate_unknown: { classes: ["linear_system"], sameBothSides: false },
  solve_one_unknown: { classes: ["linear_system"], sameBothSides: false },
  substitute_back: { classes: ["linear_system"], sameBothSides: false },
  substitute_check: { classes: ["poly_eq", "linear_system", "arith"], sameBothSides: false },
  state_result: { classes: ["poly_eq", "linear_system", "arith", "poly_simplify"], sameBothSides: false },
};

export const RULE_IDS = Object.keys(RULE_TABLE) as RuleId[];

/** Words that may surround a maths expression without making the line a sentence. Data, like the finder rules. */
export type DetectWords = { fillers: string[]; splitters: string[] };

export const DEFAULT_DETECT_WORDS: DetectWords = {
  fillers: [
    // English
    "solve", "find", "simplify", "evaluate", "calculate", "compute", "expand", "work", "out", "what", "whats", "what's",
    "is", "the", "value", "of", "for", "please", "pls", "plz", "help", "me", "with", "this", "answer", "equation", "sum",
    "if", "then", "give", "tell", "show", "get", "to", "unknown", "number",
    // Hinglish
    "hal", "karo", "kro", "karna", "kariye", "nikalo", "nikalein", "nikalna", "batao", "bata", "do", "dijiye", "ka",
    "ki", "ke", "ko", "mujhe", "ye", "yeh", "iska", "jawab", "kya", "hai", "hain", "sawal", "question", "mann", "maan",
    "sabit", "sarl", "saral",
    // Hindi (Devanagari)
    "हल", "करो", "करें", "निकालो",
    "बताओ", "का", "की", "के", "मान",
    "ज्ञात", "कीजिए", "सरल", "है",
    "मुझे", "क्या",
  ],
  splitters: ["and", "aur", "और", "&"],
};
