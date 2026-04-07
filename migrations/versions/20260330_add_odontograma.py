"""
Agregar tabla odontogramas para snapshots de odontograma de consulta.
"""

# revision identifiers, used by Alembic.
revision = '20260330odontograma'
down_revision = '20260127relopc'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'odontogramas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('consulta_id', sa.Integer(), sa.ForeignKey('consultas.id'), nullable=False),
        sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=True),
        sa.Column('datos', sa.JSON(), nullable=False),
    )
    op.create_foreign_key('fk_odontogramas_consulta', 'odontogramas', 'consultas', ['consulta_id'], ['id'])
    op.create_foreign_key('fk_odontogramas_paciente', 'odontogramas', 'pacientes', ['paciente_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_odontogramas_paciente', 'odontogramas', type_='foreignkey')
    op.drop_constraint('fk_odontogramas_consulta', 'odontogramas', type_='foreignkey')
    op.drop_table('odontogramas')
