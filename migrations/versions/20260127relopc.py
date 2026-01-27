"""
Agregar relaciones opcionales a tablas sueltas.
"""

# revision identifiers, used by Alembic.
revision = '20260127relopc'
down_revision = 'f44cc4a7596e'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
	# Agregar columnas usuario_id y especialidad_id donde corresponde
	op.add_column('insumos', sa.Column('especialidad_id', sa.Integer(), nullable=True))
	op.add_column('insumos', sa.Column('usuario_id', sa.Integer(), nullable=True))
	op.add_column('especialidades', sa.Column('usuario_id', sa.Integer(), nullable=True))
	op.add_column('procedimientos', sa.Column('usuario_id', sa.Integer(), nullable=True))
	op.add_column('formas_pago', sa.Column('usuario_id', sa.Integer(), nullable=True))
	op.add_column('configuracion_consultorio', sa.Column('consultorio_id', sa.Integer(), nullable=True))
	op.add_column('horarios_atencion', sa.Column('especialidad_id', sa.Integer(), nullable=True))
	op.add_column('medico_especialidades', sa.Column('usuario_id', sa.Integer(), nullable=True))
	op.add_column('insumo_especialidades', sa.Column('usuario_id', sa.Integer(), nullable=True))
	op.add_column('procedimiento_precios', sa.Column('usuario_id', sa.Integer(), nullable=True))
	# Agregar ForeignKey donde corresponde
	op.create_foreign_key('fk_insumos_especialidad', 'insumos', 'especialidades', ['especialidad_id'], ['id'])
	op.create_foreign_key('fk_insumos_usuario', 'insumos', 'usuarios', ['usuario_id'], ['id'])
	op.create_foreign_key('fk_especialidades_usuario', 'especialidades', 'usuarios', ['usuario_id'], ['id'])
	op.create_foreign_key('fk_procedimientos_usuario', 'procedimientos', 'usuarios', ['usuario_id'], ['id'])
	op.create_foreign_key('fk_formas_pago_usuario', 'formas_pago', 'usuarios', ['usuario_id'], ['id'])
	op.create_foreign_key('fk_horarios_atencion_especialidad', 'horarios_atencion', 'especialidades', ['especialidad_id'], ['id'])
	op.create_foreign_key('fk_medico_especialidades_usuario', 'medico_especialidades', 'usuarios', ['usuario_id'], ['id'])
	op.create_foreign_key('fk_insumo_especialidades_usuario', 'insumo_especialidades', 'usuarios', ['usuario_id'], ['id'])
	op.create_foreign_key('fk_procedimiento_precios_usuario', 'procedimiento_precios', 'usuarios', ['usuario_id'], ['id'])

def downgrade():
	op.drop_constraint('fk_procedimiento_precios_usuario', 'procedimiento_precios', type_='foreignkey')
	op.drop_constraint('fk_insumo_especialidades_usuario', 'insumo_especialidades', type_='foreignkey')
	op.drop_constraint('fk_medico_especialidades_usuario', 'medico_especialidades', type_='foreignkey')
	op.drop_constraint('fk_horarios_atencion_especialidad', 'horarios_atencion', type_='foreignkey')
	op.drop_constraint('fk_formas_pago_usuario', 'formas_pago', type_='foreignkey')
	op.drop_constraint('fk_procedimientos_usuario', 'procedimientos', type_='foreignkey')
	op.drop_constraint('fk_especialidades_usuario', 'especialidades', type_='foreignkey')
	op.drop_constraint('fk_insumos_usuario', 'insumos', type_='foreignkey')
	op.drop_constraint('fk_insumos_especialidad', 'insumos', type_='foreignkey')
	op.drop_column('procedimiento_precios', 'usuario_id')
	op.drop_column('insumo_especialidades', 'usuario_id')
	op.drop_column('medico_especialidades', 'usuario_id')
	op.drop_column('horarios_atencion', 'especialidad_id')
	op.drop_column('configuracion_consultorio', 'consultorio_id')
	op.drop_column('formas_pago', 'usuario_id')
	op.drop_column('procedimientos', 'usuario_id')
	op.drop_column('especialidades', 'usuario_id')
	op.drop_column('insumos', 'usuario_id')
	op.drop_column('insumos', 'especialidad_id')