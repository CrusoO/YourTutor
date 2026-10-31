"""Animated story pipeline — plans an arc, then writes every scene in one call.

Two model calls. The PLAN (story_plan.v2) designs an arc (hook → build → reveal → wrap) and
describes what each scene shows plus a color_map for variable identity. The SCENES call
(story_scenes.v2) writes narration and shapes for all scenes together, enforcing six rules:
anchor, covariation, no-redundancy, disappear, color identity, and motion-per-scene.
The engine reads the result with its own sanitiser, which drops any shape it cannot draw, so this
module only checks the structure. The same safety screen and consent gate apply.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import key_for_model, settings
from app.explain.service import Completer, ExplainProvider, Gate, precheck, unavailable
from app.llm.prompt import STUDENT_TAG, Prompt
from app.llm.provider import ProviderError
from app.llm.rules import default_rules

PROMPTS = Path(__file__).parent / "prompts"
PLAN_FILE = PROMPTS / "story_plan.v2.md"
SCENES_FILE = PROMPTS / "story_scenes.v2.md"
PROMPT_VERSION = "story/v3"
MAX_SCENES = 7
MIN_SCENES = 3
PLAN_TOKENS = 1500  # on Groq the input plus the output budget must stay under 8,000 a minute
SCENES_TOKENS = 5600
ATTEMPTS = 2

REFUSE = '{"refuse": true}'
OPEN_SCOPE = (
    "Plan a video on any topic a curious student might want to learn about, in any subject. "
    "If the request is harmful, sexual, hateful, asks for personal advice or help with a crime, "
    f"reply with exactly {REFUSE} and nothing else."
)
SYLLABUS_SCOPE = (
    "Plan only topics from a school syllabus (classes 6 to 12) and the ideas they are built on. "
    f"If the request is not about that, reply with exactly {REFUSE} and nothing else."
)
OUT_OF_SCOPE_MESSAGE = (
    "I cannot help with that one. Try asking about something you would like to learn."
)

_TECHNICAL_KEYWORDS = frozenset(
    [
        "technically",
        "technical",
        "in depth",
        "in-depth",
        "indepth",
        "mathematically",
        "precisely",
        "formula",
        "derive",
        "proof",
        "theorem",
        "algebra",
        "quadratic",
        "polynomial",
        "equation",
        "calculus",
        "derivative",
        "integral",
        "trigonometry",
        "geometry",
        "vectors",
        "matrix",
        "coordinate",
        "function",
        "graph",
        "roots",
        "sum of roots",
        "product of roots",
        "vieta",
        "parabola",
        "linear equation",
        "simultaneous",
        "equation",
        "geometric",
        "3blue",
        "3b1b",
        "math",
    ]
)

_STYLE_PREAMBLES: dict[str, str] = {
    "technical": (
        "## VIDEO STYLE: MATHEMATICAL (3Blue1Brown)\n\n"
        "PALETTE: Dark stage. Use ONLY these five colors, consistent across all scenes:\n"
        "  blue=#3B82F6 (primary concept), teal=#4FC3F7 (secondary),\n"
        "  yellow=#FFD700 (key result), pink=#FF6B9D (contrast), white=ink (labels).\n"
        "Once a variable is blue, it is ALWAYS blue in every scene.\n\n"
        "CONSTRUCTION SEQUENCE: Every scene builds from empty to full:\n"
        "  1. Scene opens with axes or an empty framework shape (in:{s:0})\n"
        "  2. First concept appears (in:{s:0} or in:{s:1})\n"
        "  3. Relationship appears, pointing at the concept (in:{s:1} or in:{s:2})\n"
        "  4. The equation or result appears last (in:{s:2} or in:{s:3})\n"
        "Never show the answer before the question.\n\n"
        "SIZE ENCODES VALUE: If a shape represents a quantity, its r or w or h must encode that "
        "quantity. circle for mass=4 must be larger than circle for mass=1. Use t-expressions when "
        'the value changes: r:"2+3*t" makes the circle grow as the narrator explains.\n\n'
        "ARROWS ARE EQUATIONS: Every arrow between two shapes MUST have midLabel set to the "
        "relationship it represents: 'slope = k', '×2', '→ limit'. An arrow without a label is "
        "decoration, not mathematics.\n\n"
        'EASING: Use ease:"smooth" for all translations. Use ease:"spring" for the arrival of '
        'the key result. Never use ease:"linear" — it makes motion look mechanical.\n\n'
        "FOCUS: The narrator talks about one thing at a time. Give focus:true to the shape being "
        "discussed so it glows; others dim automatically.\n\n"
        "NARRATION: First-principles. Define every term before using it. Ask 'why does this work?' "
        "before showing the answer.\n"
    ),
    "animated": (
        "## VIDEO STYLE: CINEMATIC (Lamina Labs)\n\n"
        "PALETTE: Light whiteboard background. Use MANY bold colors simultaneously:\n"
        "blue characters, red danger/friction, green good/success, orange energy, purple mystery.\n"
        "Every filled shape has a bold saturated color. fill:none only for outlines and arrows.\n\n"
        "SCENE STRUCTURE: Each scene follows this exact pattern:\n"
        "  1. HEADING: A large bold text shape (size:8, bold:true) slides in from top\n"
        '     with how:"slide" in:{s:0}. Phrased as a question or bold claim.\n'
        '  2. CHARACTERS/OBJECTS: Physical metaphor shapes enter from left, using how:"slide" '
        '     and moves with ease:"back" so they overshoot and settle.\n'
        "  3. ACTION: Shapes move, interact, grow/shrink to show the concept.\n"
        "  4. LABEL ARROWS: Arrows connect related shapes, labeled with their relationship.\n\n"
        "LEFT-TO-RIGHT FLOW: Arrange multiple objects at the same y level, spaced evenly from "
        "x=15 to x=85. First object appears at x=15 (in:{s:0}), second at x=50 (in:{s:1}), "
        "third at x=85 (in:{s:2}). The composition tells the story left to right.\n\n"
        "PHYSICAL METAPHORS:\n"
        "  - Forces: use labeled arrows (push=blue right, friction=red left, gravity=green down)\n"
        '  - Energy: circle with fill:"orange", size encodes energy level\n'
        '  - Characters: rect or circle with a human-readable label ("student", "teacher")\n'
        "  - Comparison: two objects side by side, same shape, different size/color/label\n\n"
        'MOTION: Use ease:"back" for arrivals (overshoot-and-settle). Use ease:"spring" for '
        'emphasis. Use ease:"bounce" for physical impacts. Never use ease:"linear".\n\n'
        "DEPTH: Background shapes (context, surfaces) use opacity:0.4. Foreground focal shapes "
        "use opacity:1.0 and focus:true.\n\n"
        "NARRATION: Concrete and vivid. Use physical analogies. Never say 'as we can see' — "
        "describe what's HAPPENING, not what's visible.\n"
    ),
}


def _story_style(prompt: str) -> str:
    """Return 'technical' (3B1B) or 'animated' (Lamina Labs) based on prompt keywords."""
    low = prompt.lower()
    if any(k in low for k in _TECHNICAL_KEYWORDS):
        return "technical"
    return "animated"


FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
_COVARIATION = re.compile(
    r"\b(increases?|decreases?|grows?|falls?|rises?|oscillates?|speeds?\s+up|slows?\s+down|changes?|varies?)\b",
    re.I,
)
_T_EXPR = re.compile(r'"\s*:\s*"[^"]*\bt\b')


def extract_json(text: str) -> dict[str, Any] | None:
    """The JSON object in a model reply, with code fences and any words around it removed."""
    body = FENCE.sub("", text.strip())
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(body[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def salvage_scenes(text: str) -> list[dict[str, Any]]:
    """The complete scene objects of a reply that was cut off or is not valid as a whole.

    Walks the text after `"scenes": [`, counting braces outside strings, and parses each top-level
    object that closes. A scene that was cut off in the middle is left out."""
    at = text.find('"scenes"')
    open_at = text.find("[", at) if at >= 0 else -1
    if open_at < 0:
        return []
    scenes: list[dict[str, Any]] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for i in range(open_at + 1, len(text)):
        c = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    item = json.loads(text[start : i + 1])
                except ValueError:
                    item = None
                if isinstance(item, dict):
                    scenes.append(item)
                start = -1
        elif c == "]" and depth == 0:
            break
    return scenes


def _words(value: Any, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


_VALID_ROLES = {"hook", "build", "reveal", "wrap"}
_VALID_COLORS = {
    "blue",
    "red",
    "green",
    "yellow",
    "orange",
    "purple",
    "teal",
    "pink",
    "soft",
    "ink",
}


def clean_plan(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Clean and return the plan: title, color_map, and up to seven scenes."""
    if not data or not isinstance(data.get("scenes"), list):
        return None
    # color_map: only keep safe variable names and known color values
    _cm = data.get("color_map")
    raw_map: dict[str, object] = _cm if isinstance(_cm, dict) else {}
    color_map = {
        k[:32]: v
        for k, v in raw_map.items()
        if isinstance(k, str) and isinstance(v, str) and v in _VALID_COLORS
    }
    scenes = []
    for raw in data["scenes"][:MAX_SCENES]:
        if not isinstance(raw, dict):
            continue
        role = raw.get("role", "build")
        scene = {
            "role": role if role in _VALID_ROLES else "build",
            "heading": _words(raw.get("heading"), 60),
            "purpose": _words(raw.get("purpose"), 300),
            "story": _words(raw.get("story"), 300),
            "picture": _words(raw.get("picture"), 300),
        }
        if scene["heading"] and scene["story"]:
            scenes.append(scene)
    title = _words(data.get("title"), 120)
    if len(title) < 3 or len(scenes) < MIN_SCENES:
        return None
    return {"title": title, "color_map": color_map, "scenes": scenes}


def plan_prompt(question: str, restricted: bool, style: str = "animated") -> Prompt:
    scope = SYLLABUS_SCOPE if restricted else OPEN_SCOPE
    preamble = _STYLE_PREAMBLES.get(style, "")
    base = PLAN_FILE.read_text(encoding="utf-8").strip()
    system = (preamble + "\n\n" + base if preamble else base) + "\n\n" + scope
    cleaned = STUDENT_TAG.sub("", question)
    user = f"<student_text>\n{cleaned}\n</student_text>\n\nPlan the video."
    return Prompt(system=system, user=user, version=f"{PROMPT_VERSION}/plan/{style}", max_words=700)


def scenes_prompt(question: str, plan: dict[str, Any], style: str = "animated") -> Prompt:
    preamble = _STYLE_PREAMBLES.get(style, "")
    base = SCENES_FILE.read_text(encoding="utf-8").strip()
    system = (preamble + "\n\n" + base) if preamble else base
    cleaned = STUDENT_TAG.sub("", question)
    lines = [
        f"<student_text>\n{cleaned}\n</student_text>",
        "",
        f"Title: {plan['title']}",
    ]
    color_map = plan.get("color_map") or {}
    if color_map:
        entries = ", ".join(f"{k} → {v}" for k, v in color_map.items())
        lines += [f"color_map: {entries}", ""]
    lines += [
        "The plan, one line per scene"
        " (role | heading | purpose | what it says | what the viewer sees):"
    ]
    for i, s in enumerate(plan["scenes"], 1):
        role = s.get("role", "build")
        lines.append(
            f"{i}. [{role}] {s['heading']} | {s['purpose'] or role} | {s['story']} | {s['picture']}"
        )
    lines += ["", f"Write all {len(plan['scenes'])} scenes now. Reply with the JSON object only."]
    return Prompt(
        system=system,
        user="\n".join(lines),
        version=f"{PROMPT_VERSION}/scenes/{style}",
        max_words=3500,
    )


def clean_scene(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """One scene: heading, narration (2+ sentences), shapes."""
    if not data:
        return None
    sentences = (
        [_words(s, 320) for s in data["sentences"]]
        if isinstance(data.get("sentences"), list)
        else []
    )
    sentences = [s for s in sentences if re.search(r"\w", s)][:12]
    if len(sentences) < 2:
        return None
    visuals = [v for v in data.get("visuals", []) if isinstance(v, dict)][:30]
    return {"heading": _words(data.get("heading"), 80), "sentences": sentences, "visuals": visuals}


def _scenes_of(text: str) -> list[dict[str, Any]]:
    data = extract_json(text)
    raw = data.get("scenes") if data else None
    items = (
        [s for s in raw if isinstance(s, dict)] if isinstance(raw, list) else salvage_scenes(text)
    )
    return [c for c in (clean_scene(s) for s in items) if c is not None]


def _candidates(default_model: str) -> list[tuple[str, str]]:
    """The (model, key) pairs to try, best first: the story model if set, then the general one."""
    pairs: list[tuple[str, str]] = []
    if settings.llm_story_model:
        # Use provider-specific key (e.g. OPENROUTER_API_KEY for openrouter/* models)
        key = settings.llm_story_api_key or key_for_model(settings.llm_story_model)
        pairs.append((settings.llm_story_model, key))
    key = key_for_model(default_model) if default_model else settings.llm_api_key
    pairs.append((default_model, key))
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for p in pairs:
        if p[0] and p[1] and p not in seen:
            seen.add(p)
            result.append(p)
    return result


def _tokens(model: str, small: int, large: int) -> int:
    """Groq's free tier counts the output budget against 8,000 tokens a minute; others do not."""
    return small if model.startswith("groq/") else large


def _plan(
    provider: Completer, model: str, question: str, restricted: bool, style: str = "animated"
) -> dict[str, Any] | str | None:
    """The cleaned plan, or "refuse" when the model declined the request, or None."""
    for _ in range(ATTEMPTS):
        try:
            reply = provider.complete(plan_prompt(question, restricted, style), model)
        except ProviderError:
            continue
        data = extract_json(reply.text)
        if data and data.get("refuse") is True:
            return "refuse"
        plan = clean_plan(data)
        if plan:
            return plan
    return None


def _scenes(
    provider: Completer, model: str, question: str, plan: dict[str, Any], style: str = "animated"
) -> list[dict[str, Any]]:
    written: list[dict[str, Any]] = []
    for _ in range(ATTEMPTS):
        try:
            reply = provider.complete(scenes_prompt(question, plan, style), model)
        except ProviderError:
            continue
        found = _scenes_of(reply.text)
        if len(found) > len(written):
            written = found
        if len(written) >= len(plan["scenes"]):
            break
    return written


def _quick_qa(scenes: list[dict[str, Any]]) -> list[str]:
    """Python-side structural checks that can be repaired by the LLM in one pass."""
    issues: list[str] = []
    has_hook = any(s.get("role") == "hook" for s in scenes)
    has_reveal = any(s.get("role") == "reveal" for s in scenes)
    if not has_hook:
        issues.append(
            "No scene has role 'hook'. The first scene must have role:hook and end with a question."
        )
    if not has_reveal:
        issues.append(
            "No scene has role 'reveal'. Add a scene with role:reveal that answers the hook question."  # noqa: E501
        )
    for i, sc in enumerate(scenes):
        sents = sc.get("sentences", [])
        visuals = sc.get("visuals", [])
        # hook must end with question mark
        if sc.get("role") == "hook" and sents and not sents[-1].rstrip().endswith("?"):
            issues.append(
                f"Scene {i + 1} (hook): last sentence must end with '?' — change '{sents[-1][-40:]}' to a question."  # noqa: E501
            )
        # covariation: change word but no t-expression in visuals
        all_text = " ".join(sents)
        m_cov = _COVARIATION.search(all_text)
        if m_cov:
            vis_json = json.dumps(visuals)
            if not _T_EXPR.search(vis_json):
                issues.append(
                    f"Scene {i + 1}: narration mentions change ('{m_cov.group()}') but no shape uses a t-expression. Add a t-expression to animate the change."  # noqa: E501
                )
        # scene overloaded
        if len(visuals) > 6:
            issues.append(
                f"Scene {i + 1}: {len(visuals)} shapes is too many. Remove shapes so at most 6 are visible at once."  # noqa: E501
            )
        # unfilled labeled shapes
        for v in visuals:
            if v.get("kind") in ("circle", "rect") and v.get("label") and v.get("fill") == "none":
                issues.append(
                    f"Scene {i + 1}, shape '{v.get('id', '?')}': labeled {v['kind']} has fill:none. Set fill equal to its color."  # noqa: E501
                )
        # linear ease
        for v in visuals:
            for m in v.get("moves") or []:
                if isinstance(m, dict) and m.get("ease") == "linear":
                    issues.append(
                        f"Scene {i + 1}, shape '{v.get('id', '?')}': move uses ease:'linear'. Change to 'ease' or 'smooth'."  # noqa: E501
                    )
                    break
        # no motion in scene
        vis_json = json.dumps(visuals)
        has_t = _T_EXPR.search(vis_json)
        has_moves = '"moves"' in vis_json and '"dx"' in vis_json
        if not has_t and not has_moves:
            issues.append(
                f"Scene {i + 1}: no t-expression or moves. Add at least one animated shape (Rule 6)."  # noqa: E501
            )
    return issues


def repair_prompt(
    question: str,
    plan: dict[str, Any],
    scenes: list[dict[str, Any]],
    issues: list[str],
    style: str = "animated",
) -> Prompt:
    """Targeted repair call: return scenes JSON + numbered issues for the LLM to fix."""
    preamble = _STYLE_PREAMBLES.get(style, "")
    base = SCENES_FILE.read_text(encoding="utf-8").strip()
    system = (preamble + "\n\n" + base) if preamble else base
    issue_list = "\n".join(f"  {j + 1}. {iss}" for j, iss in enumerate(issues))
    scenes_json = json.dumps({"scenes": scenes}, ensure_ascii=False)
    user = (
        f"<student_text>\n{STUDENT_TAG.sub('', question)}\n</student_text>\n\n"
        f"The scenes below have these QA problems:\n{issue_list}\n\n"
        "Fix ONLY the listed problems. Do not change scenes or sentences that are not affected. "
        "Reply with the corrected JSON object only.\n\n"
        f"Current scenes:\n{scenes_json}"
    )
    return Prompt(
        system=system, user=user, version=f"{PROMPT_VERSION}/repair/{style}", max_words=3500
    )


def _repair(
    provider: Completer,
    model: str,
    question: str,
    plan: dict[str, Any],
    scenes: list[dict[str, Any]],
    issues: list[str],
    style: str = "animated",
) -> list[dict[str, Any]]:
    """One repair pass. Returns repaired scenes if they have at least as many scenes as before."""
    try:
        reply = provider.complete(repair_prompt(question, plan, scenes, issues, style), model)
    except ProviderError:
        return scenes
    fixed = _scenes_of(reply.text)
    return fixed if len(fixed) >= len(scenes) else scenes


def build_story(
    question: str,
    language: str,
    gate: Gate,
    provider: Completer | None = None,
    model: str | None = None,
    restricted: bool = False,
) -> dict[str, Any]:
    """Plan, then write every scene: {"kind": "story", "story": ..., "fallbacks": n}, or why not."""
    if language != "en":
        return unavailable("language")  # the engine's voices are English
    early, text_in, chosen = precheck(question, language, gate, provider, model)
    if early is not None:
        return early
    style = _story_style(question)
    # a given provider (a test) is used as it is; otherwise each configured model is tried in turn
    tries: list[tuple[str, Completer | None, Completer | None]] = (
        [(chosen, provider, provider)]
        if provider is not None
        else [
            (
                m,
                ExplainProvider(True, _tokens(m, PLAN_TOKENS, 4000), key),
                ExplainProvider(True, _tokens(m, SCENES_TOKENS, 14000), key),
            )
            for m, key in _candidates(chosen)
        ]
    )
    reason = "plan"
    for use, plan_provider, scene_provider in tries:
        plan = _plan(plan_provider, use, text_in, restricted, style)  # type: ignore[arg-type]
        if plan == "refuse":
            return {"kind": "out_of_scope", "message": OUT_OF_SCOPE_MESSAGE}
        if not isinstance(plan, dict):
            reason = "plan"
            continue
        written = _scenes(scene_provider, use, text_in, plan, style)  # type: ignore[arg-type]
        if len(written) < MIN_SCENES:
            reason = "scenes"
            continue
        # merge plan roles into scenes (roles are not in the LLM's response)
        for i, scene in enumerate(written[: len(plan["scenes"])]):
            scene["role"] = plan["scenes"][i]["role"]
        # QA: run a repair pass if structural issues are found
        qa_issues = _quick_qa(written[: len(plan["scenes"])])
        if qa_issues and scene_provider is not None:
            written = _repair(
                scene_provider, use, text_in, plan, written[: len(plan["scenes"])], qa_issues, style
            )
            # re-merge roles after repair (repair LLM may have dropped them)
            for i, scene in enumerate(written[: len(plan["scenes"])]):
                scene["role"] = plan["scenes"][i]["role"]
        scenes = []
        for i, scene in enumerate(written[: len(plan["scenes"])]):
            scene["heading"] = scene["heading"] or plan["scenes"][i]["heading"]
            scenes.append(scene)
        terms = default_rules().blocked_terms
        text = " ".join(s for sc in scenes for s in sc["sentences"]).lower()
        if any(re.search(rf"\b{re.escape(t)}\b", text) for t in terms):
            reason = "checks"
            continue
        story: dict[str, Any] = {"title": plan["title"], "scenes": scenes}
        if plan.get("color_map"):
            story["color_map"] = plan["color_map"]
        return {
            "kind": "story",
            "story": story,
            "fallbacks": len(plan["scenes"]) - len(scenes),
            "model": use.split("/")[0],
        }
    return unavailable(reason)
