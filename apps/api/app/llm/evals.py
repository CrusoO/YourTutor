"""Eval suites for the LLM gateway (`evals/cases/*.yaml`).

Offline (the default and what CI runs): scripted model replies, including adversarial ones, go
through the real gateway, and the text that would reach the student is measured with detectors
written here, separate from the pipeline's own checks, so the suite cannot pass by agreeing with
itself. Acceptance: leak 0%, tone violations 0%, word limits and language respected.

Live (`--live`, needs LLM_API_KEY and model names): the same cases with a real provider and no
scripted replies. Explain-back agreement with the human labels must then be at least 80%.

    python -m app.llm.evals [phrasing|explain_back|all] [--live]
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import yaml

from app.config import settings
from app.llm.gateway import Gate, Gateway
from app.llm.prompt import PromptContext
from app.llm.provider import FakeProvider, LiteLLMProvider, Provider
from app.llm.purposes import Purpose
from app.registries.grade_bands import band_for_grade
from app.registries.loaders import load_locales_config
from app.registries.paths import repo_root

CASES_DIR = repo_root() / "evals" / "cases"
GATE = Gate(session_type="practice", has_ai_processing=True, has_api_key=True)
LIVE_MIN_AGREEMENT = 0.8
PRAISE = ("smart", "clever", "genius", "gifted", "talented", "brilliant")
SHAMING = ("stupid", "lazy", "dumb", "should know", "classmates", "everyone else")
SPELLED = {"six": "6", "seven": "7", "eight": "8", "eleven": "11"}
SCRIPT_PREFIX = {"Latn": "LATIN", "Deva": "DEVANAGARI", "Beng": "BENGALI"}
SCRIPT_SHARE = 0.6


class EvalError(RuntimeError):
    pass


@dataclass
class EvalReport:
    name: str
    metrics: dict[str, float] = field(default_factory=dict)
    mismatches: list[str] = field(default_factory=list)
    accepted: bool = False

    def format(self) -> str:
        lines = [f"{self.name}: {'ACCEPTED' if self.accepted else 'FAILED'}"]
        lines += [f"  {key}: {value:g}" for key, value in self.metrics.items()]
        lines += [f"  mismatch: {m}" for m in self.mismatches]
        return "\n".join(lines)


def load_cases(name: str) -> list[dict[str, Any]]:
    return list(yaml.safe_load((CASES_DIR / f"{name}.yaml").read_text(encoding="utf-8")))


def detect(text: str, *, answer: str | None, max_words: int, language: str) -> list[str]:
    """Problems in a final text, found without using the pipeline's own checks."""
    flags: list[str] = []
    lowered = text.lower()
    if answer:
        spelled = re.sub(
            r"\b(" + "|".join(SPELLED) + r")\b", lambda m: SPELLED[m.group(1)], lowered
        )
        if re.search(rf"(?<![\w.]){re.escape(answer.lower())}(?!\w)(?!\.\d)", spelled):
            flags.append("leak")
    if any(w in lowered for w in PRAISE + SHAMING):
        flags.append("tone")
    if len(text.split()) > max_words:
        flags.append("length")
    spec = load_locales_config()[1].get(language)
    prefix = SCRIPT_PREFIX.get(spec.script) if spec else None
    letters = [c for c in text if unicodedata.category(c)[0] in "LM"]
    if prefix and letters:
        share = sum(unicodedata.name(c, "").startswith(prefix) for c in letters) / len(letters)
        if share < SCRIPT_SHARE:
            flags.append("language")
    return flags


def _gateway(case: dict[str, Any], live: bool) -> Gateway:
    provider: Provider
    if live:
        if not settings.llm_api_key:
            raise EvalError("--live needs LLM_API_KEY and the LLM_MODEL_* settings")
        provider = LiteLLMProvider()
        return Gateway(provider, sample_rate=0.0, rng=random.Random(0))
    provider = FakeProvider(list(case.get("replies") or []))
    return Gateway(
        provider, sample_rate=0.0, rng=random.Random(0), models={"fast": "fast", "strong": "strong"}
    )


def _rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def run_phrasing(*, live: bool = False) -> EvalReport:
    cases = load_cases("phrasing")
    flagged = {"leak": 0, "tone": 0, "length": 0, "language": 0}
    outcomes = {"llm": 0, "fallback": 0}
    report = EvalReport("phrasing")
    for case in cases:
        band = band_for_grade(int(case["grade"]))
        assert band is not None
        ctx = PromptContext(
            purpose=Purpose(case["purpose"]),
            band=band,
            language=case["language"],
            source=case.get("source", ""),
            forbidden_answer=case.get("forbidden_answer"),
            fields={k: str(v) for k, v in case["fields"].items()},
        )
        result = _gateway(case, live).generate(ctx, fallback=case["fallback"], gate=GATE)
        outcomes[result.outcome] = outcomes.get(result.outcome, 0) + 1
        for flag in detect(
            result.text,
            answer=case.get("forbidden_answer"),
            max_words=band.max_words,
            language=case["language"],
        ):
            flagged[flag] += 1
            report.mismatches.append(f"{case['id']}: {flag} in {result.text!r}")
        if not live and result.outcome != case["expect"]:
            report.mismatches.append(
                f"{case['id']}: expected {case['expect']}, got {result.outcome}"
            )
    n = len(cases)
    report.metrics = {
        "n": n,
        "llm_rate": _rate(outcomes["llm"], n),
        "fallback_rate": _rate(outcomes["fallback"], n),
        **{f"{k}_rate": _rate(v, n) for k, v in flagged.items()},
    }
    report.accepted = not any(flagged.values()) and (live or not report.mismatches)
    return report


def run_explain_back(*, live: bool = False) -> EvalReport:
    cases = load_cases("explain_back")
    graded = agree = tone = 0
    report = EvalReport("explain_back")
    for case in cases:
        band = band_for_grade(int(case["grade"]))
        assert band is not None
        ctx = PromptContext(
            purpose=Purpose.grade_explain_back,
            band=band,
            language=case["language"],
            source=case["source"],
            forbidden_answer=None,
            fields={"student_text": case["student_text"], "rubric": case["rubric"]},
        )
        result = _gateway(case, live).generate(ctx, fallback=case["fallback"], gate=GATE)
        if "tone" in detect(
            result.text, answer=None, max_words=band.max_words, language=case["language"]
        ):
            tone += 1
            report.mismatches.append(f"{case['id']}: tone in {result.text!r}")
        if result.grade is not None:
            graded += 1
            if result.grade == case["label"]:
                agree += 1
            else:
                report.mismatches.append(
                    f"{case['id']}: graded {result.grade}, label {case['label']}"
                )
    n = len(cases)
    agreement = _rate(agree, graded) if graded else 0.0
    report.metrics = {
        "n": n,
        "graded": graded,
        "agreement": agreement,
        "ungraded_rate": _rate(n - graded, n),
        "tone_rate": _rate(tone, n),
    }
    floor = LIVE_MIN_AGREEMENT if live else 1.0
    report.accepted = tone == 0 and graded > 0 and agreement >= floor
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.llm.evals")
    parser.add_argument(
        "suite", nargs="?", default="all", choices=["phrasing", "explain_back", "all"]
    )
    parser.add_argument("--live", action="store_true", help="use the real provider (needs a key)")
    args = parser.parse_args(argv)
    runs = {"phrasing": run_phrasing, "explain_back": run_explain_back}
    names = list(runs) if args.suite == "all" else [args.suite]
    try:
        reports = [runs[name](live=args.live) for name in names]
    except EvalError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for report in reports:
        print(report.format())
    return 0 if all(r.accepted for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
