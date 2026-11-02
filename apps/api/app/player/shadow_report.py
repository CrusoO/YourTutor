"""`python -m app.player.shadow_report --student <id>`: BKT-F against the live BKT for one student.

Read-only. It replays the student's logged practice through both models (see `bktf_shadow`) and
prints how well each predicted the answers. It shows an id and counts only: no names or other
personal data.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections import Counter, defaultdict
from collections.abc import Sequence

from app.config import settings
from app.db.session import session_factory
from app.learner.bktf import AttemptKind
from app.learner.bktf_shadow import ShadowStep, compare
from app.orchestrator.types import default_params
from app.player.ladder_log import shadow_steps_for_student
from app.player.runtime import bkt_params_by_skill, load_catalog

# TUNABLE-DEFAULT: below this many attempts a log-loss difference is mostly noise.
MIN_ATTEMPTS_TO_JUDGE = 30
# TUNABLE-DEFAULT: a log-loss difference smaller than this is a tie, not a win or a loss.
MEANINGFUL_LOG_LOSS_DIFF = 0.005
# TUNABLE-DEFAULT: with no gap this long, forgetting cannot show. Practice seconds apart (a seeded
# preview, or one sitting) leaves BKT-F and the live model nearly identical.
MIN_MEANINGFUL_GAP_DAYS = 1.0


def format_report(student_id: uuid.UUID, steps: Sequence[ShadowStep]) -> str:
    lines = [f"BKT-F shadow report for student {student_id}"]
    if not steps:
        return "\n".join([*lines, "No logged practice attempts to replay."])

    result = compare(steps)
    lines += [
        f"attempts replayed: {result.attempts}",
        f"log-loss, live BKT: {result.live_log_loss:.4f}",
        f"log-loss, BKT-F:    {result.shadow_log_loss:.4f}   (lower is better)",
    ]
    if result.attempts < MIN_ATTEMPTS_TO_JUDGE:
        lines.append(
            f"Too few attempts to judge (under {MIN_ATTEMPTS_TO_JUDGE}); do not act on this."
        )
    elif abs(result.shadow_log_loss - result.live_log_loss) < MEANINGFUL_LOG_LOSS_DIFF:
        lines.append("No meaningful difference between the two models on these answers.")
    elif result.shadow_is_better:
        lines.append(
            "BKT-F predicted these answers better. One student is not enough to promote it."
        )
    else:
        lines.append("BKT-F did not predict these answers better.")
    if max(step.gap_days for step in steps) < MIN_MEANINGFUL_GAP_DAYS:
        lines.append(
            f"No gap between attempts reaches {MIN_MEANINGFUL_GAP_DAYS:g} day, so forgetting was "
            "not exercised: BKT-F ~ the live model."
        )

    by_skill: dict[str, list[ShadowStep]] = defaultdict(list)
    for step in steps:
        by_skill[step.skill_id].append(step)
    lines += ["", f"{'skill':<28} {'n':>3} {'guess':>5} {'hint':>4} {'live p':>7} {'BKT-F p':>8}"]
    for skill_id, rows in sorted(by_skill.items()):
        kinds = Counter(row.kind for row in rows)
        last = rows[-1]
        lines.append(
            f"{skill_id[:28]:<28} {len(rows):>3} {kinds[AttemptKind.RAPID_GUESS]:>5} "
            f"{kinds[AttemptKind.HINTED]:>4} {last.p_live:>7.3f} {last.p_shadow:>8.3f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.player.shadow_report")
    parser.add_argument("--student", required=True, help="student id (uuid)")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    try:
        student_id = uuid.UUID(args.student)
    except ValueError:
        print("ERROR: --student must be a uuid", file=sys.stderr)
        return 1
    with session_factory(args.database_url)() as db:
        catalog = load_catalog(db, allow_draft=settings.allow_draft_content)
        params = bkt_params_by_skill(db)
        for item in catalog:
            params.setdefault(item.primary_skill, default_params())
        steps = shadow_steps_for_student(db, student_id, catalog, params)
    print(format_report(student_id, steps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
