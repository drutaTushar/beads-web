"""Add child_order column to dependencies table

Revision ID: ed1d26e0873a
Revises: 4bfcc158532b
Create Date: 2025-10-15 22:56:08.798354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed1d26e0873a'
down_revision: Union[str, Sequence[str], None] = '4bfcc158532b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add child_order column to dependencies table
    op.add_column('dependencies', sa.Column('child_order', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove child_order column from dependencies table
    op.drop_column('dependencies', 'child_order')
