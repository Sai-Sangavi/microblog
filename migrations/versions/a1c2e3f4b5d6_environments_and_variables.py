"""environments and variables

Revision ID: a1c2e3f4b5d6
Revises: 834b1a697901
Create Date: 2026-11-18 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1c2e3f4b5d6"
down_revision = "834b1a697901"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_project_user_id"), ["user_id"], unique=False
        )

    op.create_table(
        "environment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name"),
    )
    with op.batch_alter_table("environment", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_environment_project_id"), ["project_id"], unique=False
        )

    op.create_table(
        "variable",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("shared_value", sa.Text(), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "key"),
    )
    with op.batch_alter_table("variable", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_variable_project_id"), ["project_id"], unique=False
        )

    op.create_table(
        "variable_override",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variable_id", sa.Integer(), nullable=False),
        sa.Column("environment_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["environment.id"]),
        sa.ForeignKeyConstraint(["variable_id"], ["variable.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variable_id", "environment_id"),
    )
    with op.batch_alter_table("variable_override", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_variable_override_variable_id"),
            ["variable_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_variable_override_environment_id"),
            ["environment_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("variable_override", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_variable_override_environment_id"))
        batch_op.drop_index(batch_op.f("ix_variable_override_variable_id"))
    op.drop_table("variable_override")

    with op.batch_alter_table("variable", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_variable_project_id"))
    op.drop_table("variable")

    with op.batch_alter_table("environment", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_environment_project_id"))
    op.drop_table("environment")

    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_project_user_id"))
    op.drop_table("project")
