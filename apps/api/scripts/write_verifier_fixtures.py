"""Write packages/shared/fixtures/verifier/cases.json from the Python verifier.

The Python verifier is the authority: this script only records what it answers for a list of
cases, so the offline TypeScript verifier can be held to the same answers.

    PYTHONPATH=. python scripts/write_verifier_fixtures.py
"""

from __future__ import annotations

import json

from app.registries.paths import repo_root
from app.verifier.check import verify_response

NUM = {"type": "numeric", "answer_sympy": "5", "accept": ["5"], "options": []}
EXPR = {"type": "expression", "answer_sympy": "5", "accept": ["5", "x=5"], "options": []}
NEG = {"type": "expression", "answer_sympy": "-3", "accept": ["-3"], "options": []}
FRAC = {"type": "expression", "answer_sympy": "1/3", "accept": ["1/3"], "options": []}
DEC = {"type": "numeric", "answer_sympy": "2.5", "accept": ["2.5"], "options": []}
ALG = {"type": "expression", "answer_sympy": "2*x + 2", "accept": [], "options": []}
MCQ = {
    "type": "mcq",
    "answer_sympy": "b",
    "accept": [],
    "options": [{"id": "a", "en": "Seven"}, {"id": "b", "en": "Nine"}, {"id": "c", "en": "Eleven"}],
}
YESNO = {
    "type": "mcq",
    "answer_sympy": "yes",
    "accept": [],
    "options": [{"id": "yes", "en": "Yes"}, {"id": "no", "en": "No"}],
}

CASES: list[tuple[str, dict, str, str]] = [
    ("exact", NUM, "5", "default_ascii"),
    ("wrong number", NUM, "6", "default_ascii"),
    ("surrounding spaces", NUM, "  5  ", "default_ascii"),
    ("x equals form", EXPR, "x = 5", "default_ascii"),
    ("x equals form without spaces", NUM, "x=5", "default_ascii"),
    ("wrong x equals form", NUM, "x = 6", "default_ascii"),
    ("devanagari digit", NUM, "५", "default_ascii"),
    ("bengali digit", NUM, "৫", "default_ascii"),
    ("arithmetic that equals the answer", NUM, "2+3", "default_ascii"),
    ("arithmetic that does not", NUM, "2+4", "default_ascii"),
    ("multiplication sign", NUM, "5×1", "default_ascii"),
    ("division sign", NUM, "10÷2", "default_ascii"),
    ("unicode minus", NEG, "−3", "default_ascii"),
    ("negative by arithmetic", NEG, "0-3", "default_ascii"),
    ("negative wrong sign", NEG, "3", "default_ascii"),
    ("fraction exact", FRAC, "1/3", "default_ascii"),
    ("fraction as decimal", FRAC, "0.33333333333", "default_ascii"),
    ("fraction rough decimal is wrong", FRAC, "0.33", "default_ascii"),
    ("decimal answer", DEC, "2.5", "default_ascii"),
    ("decimal as fraction", DEC, "5/2", "default_ascii"),
    ("decimal comma rejected without the profile", DEC, "2,5", "default_ascii"),
    ("decimal comma accepted with the profile", DEC, "2,5", "decimal_comma"),
    ("decimal point still fine with the comma profile", DEC, "2.5", "decimal_comma"),
    ("leading zero is not a number", NUM, "05", "default_ascii"),
    ("trailing dot", NUM, "5.", "default_ascii"),
    ("dont know", NUM, "I don't know", "default_ascii"),
    ("idk", NUM, "idk", "default_ascii"),
    ("empty", NUM, "", "default_ascii"),
    ("only spaces", NUM, "   ", "default_ascii"),
    ("letters only", NUM, "five", "default_ascii"),
    ("injection attempt", NUM, "__import__('os')", "default_ascii"),
    ("too long", NUM, "1" * 80, "default_ascii"),
    ("too many parentheses", NUM, "(" * 12 + "5" + ")" * 12, "default_ascii"),
    ("power", NUM, "10^1/2", "default_ascii"),
    ("implicit multiplication in algebra", ALG, "2(x+1)", "default_ascii"),
    ("algebra reordered", ALG, "2 + 2x", "default_ascii"),
    ("algebra not equal", ALG, "2x + 3", "default_ascii"),
    ("algebra with an equals prefix", ALG, "y = 2x + 2", "default_ascii"),
    ("mcq by id", MCQ, "b", "default_ascii"),
    ("mcq by label", MCQ, "Nine", "default_ascii"),
    ("mcq by label, lower case", MCQ, "nine", "default_ascii"),
    ("mcq wrong id", MCQ, "a", "default_ascii"),
    ("mcq wrong label", MCQ, "Seven", "default_ascii"),
    ("mcq unknown", MCQ, "z", "default_ascii"),
    ("yes no right", YESNO, "yes", "default_ascii"),
    ("yes no wrong", YESNO, "no", "default_ascii"),
    ("yes no label", YESNO, "Yes", "default_ascii"),
]


def main() -> None:
    rows = []
    for name, item, response, profile in CASES:
        got = verify_response(
            response,
            answer_sympy=item["answer_sympy"],
            accept=item["accept"],
            item_type=item["type"],
            options=item["options"],
            notation_profile=profile,
        )
        rows.append(
            {"name": name, "item": item, "response": response, "profile": profile, "expected": got}
        )
    out = repo_root() / "packages" / "shared" / "fixtures" / "verifier" / "cases.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    note = "Recorded from apps/api/app/verifier/check.py by scripts/write_verifier_fixtures.py."
    payload = {"note": note, "cases": rows}
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} cases to {out}")


if __name__ == "__main__":
    main()
