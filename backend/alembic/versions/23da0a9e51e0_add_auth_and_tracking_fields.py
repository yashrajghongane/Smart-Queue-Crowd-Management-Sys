"""add_auth_and_tracking_fields

Revision ID: 23da0a9e51e0
Revises: bf8caeb980ea
Create Date: 2026-09-26 01:48:01.222074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23da0a9e51e0'
down_revision: Union[str, None] = 'bf8caeb980ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('staff_users') as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint('uq_staff_users_username', ['username'])

    with op.batch_alter_table('zones') as batch_op:
        batch_op.add_column(sa.Column('current_occupancy', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('devices') as batch_op:
        batch_op.add_column(sa.Column('credential_hash', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('last_sequence', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('devices') as batch_op:
        batch_op.drop_column('last_sequence')
        batch_op.drop_column('credential_hash')

    with op.batch_alter_table('zones') as batch_op:
        batch_op.drop_column('current_occupancy')

    with op.batch_alter_table('staff_users') as batch_op:
        batch_op.drop_constraint('uq_staff_users_username', type_='unique')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('username')
