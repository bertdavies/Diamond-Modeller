"""Add index to diamond label

Revision ID: 003_add_index_to_diamond_label
Revises: 002_add_color_to_diamond
Create Date: 2025-09-05 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_index_to_diamond_label'
down_revision = '002_add_color_to_diamond'
branch_labels = None
depends_on = None


def upgrade():
    # Add index to diamond label for better performance
    op.create_index('ix_diamond_label', 'diamond', ['label'])


def downgrade():
    # Remove index
    op.drop_index('ix_diamond_label', 'diamond')
