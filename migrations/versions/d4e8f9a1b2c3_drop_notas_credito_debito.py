"""drop notas_credito y notas_debito

Revision ID: d4e8f9a1b2c3
Revises: 9ce7b2a4c12f
Create Date: 2025-12-29 11:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e8f9a1b2c3'
down_revision = '9ce7b2a4c12f'
branch_labels = None
depends_on = None


def upgrade():
    """Eliminar tablas notas_credito y notas_debito que no se usan"""
    # Eliminar tabla notas_debito
    op.drop_table('notas_debito')
    
    # Eliminar tabla notas_credito
    op.drop_table('notas_credito')


def downgrade():
    """Recrear tablas en caso de rollback"""
    # Recrear notas_credito
    op.create_table('notas_credito',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(length=50), nullable=False),
        sa.Column('venta_id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=False),
        sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=False),
        sa.Column('usuario_registro_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['usuario_registro_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero')
    )
    
    # Recrear notas_debito
    op.create_table('notas_debito',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(length=50), nullable=False),
        sa.Column('venta_id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=False),
        sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=False),
        sa.Column('usuario_registro_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['usuario_registro_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero')
    )
