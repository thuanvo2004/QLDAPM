"""add conversation_id to messages

Revision ID: 7cc541d28e19
Revises: 
Create Date: 2025-09-12 00:37:08.746129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7cc541d28e19'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('conversation_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'conversations', ['conversation_id'], ['id'])

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('isPremiumActive', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('isPremiumActive')

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('conversation_id')

