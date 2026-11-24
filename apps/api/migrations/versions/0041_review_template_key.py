"""Template version key on review decisions (behind REVIEW_TEMPLATE_APPROVAL_ENABLED).

Adds the nullable column `content_reviews.template_key`: sha256 hex of
"template_id|template_hash|generator_version" of the item when the decision was recorded, set by the
server only. NULL for items with no template and for rows written before this change. Template
approval counts only rows whose key equals the template version's current key.

Idempotent on SQLite and Postgres: upgrade adds the column only if absent; downgrade drops it only
if present.

Revision ID: 0041_review_template_key
Revises: 0040_reviewer_code_issues
Create Date: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_review_template_key"
down_revision: str | None = "0040_reviewer_code_issues"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "content_reviews"
COLUMN = "template_key"


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    if COLUMN in _columns():
        return
    with op.batch_alter_table(TABLE) as batch:
        batch.add_column(sa.Column(COLUMN, sa.String(64), nullable=True))


def downgrade() -> None:
    if COLUMN not in _columns():
        return
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_column(COLUMN)
