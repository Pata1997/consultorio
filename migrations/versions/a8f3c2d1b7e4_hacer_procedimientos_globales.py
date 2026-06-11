"""Hacer procedimientos globales

Revision ID: a8f3c2d1b7e4
Revises: 5303954ce265
Create Date: 2026-06-11 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a8f3c2d1b7e4'
down_revision = '5303954ce265'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('procedimientos', schema=None) as batch_op:
        batch_op.alter_column(
            'especialidad_id',
            existing_type=sa.Integer(),
            nullable=True
        )
        batch_op.alter_column(
            'precio',
            existing_type=sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0')
        )


def downgrade():
    with op.batch_alter_table('procedimientos', schema=None) as batch_op:
        batch_op.alter_column(
            'precio',
            existing_type=sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=None
        )
        batch_op.alter_column(
            'especialidad_id',
            existing_type=sa.Integer(),
            nullable=False
        )
