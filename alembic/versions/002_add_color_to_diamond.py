"""Add color to diamond

Revision ID: 002_add_color_to_diamond
Revises: 001_initial_migration
Create Date: 2025-09-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_color_to_diamond'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add color column to diamond table
    op.add_column('diamond', sa.Column('color', sa.String(), nullable=False, server_default='#4ecdc4'))


def downgrade():
    # Remove color column from diamond table
    op.drop_column('diamond', 'color')
