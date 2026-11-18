"""comments

Revision ID: b2d4f6a8c0e1
Revises: a1c2e3f4b5d6
Create Date: 2026-11-18 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2d4f6a8c0e1"
down_revision = "a1c2e3f4b5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "comment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("comment", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_comment_timestamp"), ["timestamp"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_comment_post_id"), ["post_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_comment_user_id"), ["user_id"], unique=False
        )


def downgrade():
    with op.batch_alter_table("comment", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_comment_user_id"))
        batch_op.drop_index(batch_op.f("ix_comment_post_id"))
        batch_op.drop_index(batch_op.f("ix_comment_timestamp"))
    op.drop_table("comment")
