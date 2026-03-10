"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create diamond table
    op.create_table('diamond',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create vertex table
    op.create_table('vertex',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('diamond_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('adversary', 'victimology', 'capability', 'infrastructure', name='vertextype'), nullable=False),
        sa.ForeignKeyConstraint(['diamond_id'], ['diamond.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indicator table
    op.create_table('indicator',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('raw_value', sa.String(), nullable=True),
        sa.Column('kind', sa.Enum('ip', 'domain', 'email', 'tool', 'ttp', 'other', name='indicatorkind'), nullable=False),
        sa.Column('hash', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('value')
    )
    op.create_index(op.f('ix_indicator_value'), 'indicator', ['value'], unique=False)
    
    # Create vertex_indicator junction table
    op.create_table('vertex_indicator',
        sa.Column('vertex_id', sa.Integer(), nullable=False),
        sa.Column('indicator_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['indicator_id'], ['indicator.id'], ),
        sa.ForeignKeyConstraint(['vertex_id'], ['vertex.id'], ),
        sa.PrimaryKeyConstraint('vertex_id', 'indicator_id')
    )
    
    # Create edge table
    op.create_table('edge',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('src_diamond_id', sa.Integer(), nullable=False),
        sa.Column('dst_diamond_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('overlap_count', sa.Integer(), nullable=False),
        sa.Column('is_manual', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['dst_diamond_id'], ['diamond.id'], ),
        sa.ForeignKeyConstraint(['src_diamond_id'], ['diamond.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('edge')
    op.drop_table('vertex_indicator')
    op.drop_table('indicator')
    op.drop_table('vertex')
    op.drop_table('diamond')

