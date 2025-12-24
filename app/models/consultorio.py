from app import db
from datetime import datetime
from app.models.usuario import Paciente, Medico, Especialidad

class Cita(db.Model):
    """Modelo para citas médicas"""
    __tablename__ = 'citas'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidades.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.Text)
    estado = db.Column(db.String(20), nullable=False, default='pendiente')  
    # Estados: pendiente, confirmada, cancelada, completada, no_asistio
    observaciones = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_confirmacion = db.Column(db.DateTime)
    usuario_registro_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Relaciones (paciente y medico vienen por backref desde usuario.py)
    consulta = db.relationship('Consulta', backref='cita', uselist=False, lazy=True)
    especialidad = db.relationship('Especialidad', foreign_keys=[especialidad_id])
    
    def __repr__(self):
        return f'<Cita {self.id} - {self.fecha} {self.hora}>'

class Consulta(db.Model):
    """Modelo para consultas médicas"""
    __tablename__ = 'consultas'
    
    id = db.Column(db.Integer, primary_key=True)
    cita_id = db.Column(db.Integer, db.ForeignKey('citas.id'), unique=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidades.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    motivo = db.Column(db.Text, nullable=False)
    diagnostico = db.Column(db.Text, nullable=False)
    observaciones = db.Column(db.Text)
    
    # Signos vitales
    presion_arterial = db.Column(db.String(20))
    temperatura = db.Column(db.Numeric(4, 1))
    pulso = db.Column(db.Integer)
    peso = db.Column(db.Numeric(5, 2))
    altura = db.Column(db.Numeric(5, 2))
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    recetas = db.relationship('Receta', backref='consulta', lazy=True)
    insumos_usados = db.relationship('ConsultaInsumo', backref='consulta', lazy=True)
    procedimientos_realizados = db.relationship('ConsultaProcedimiento', backref='consulta', lazy=True)
    ordenes_estudio = db.relationship('OrdenEstudio', backref='consulta', lazy=True)
    # Relación a Especialidad para acceso desde plantillas (consulta.especialidad.nombre)
    especialidad = db.relationship('Especialidad', foreign_keys=[especialidad_id])
    
    def __repr__(self):
        return f'<Consulta {self.id} - {self.fecha}>'

class Receta(db.Model):
    """Modelo para recetas médicas (medicamentos externos)"""
    __tablename__ = 'recetas'
    
    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'), nullable=False)
    medicamento = db.Column(db.String(200), nullable=False)
    dosis = db.Column(db.String(100), nullable=False)
    frecuencia = db.Column(db.String(100), nullable=False)
    duracion = db.Column(db.String(50), nullable=False)
    indicaciones = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Receta {self.medicamento}>'

class OrdenEstudio(db.Model):
    """Modelo para órdenes de estudios y análisis"""
    __tablename__ = 'ordenes_estudio'
    
    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # estudio, analisis
    descripcion = db.Column(db.Text, nullable=False)
    indicaciones = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OrdenEstudio {self.tipo} - {self.id}>'

class Insumo(db.Model):
    """Modelo para insumos médicos"""
    __tablename__ = 'insumos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    # Código interno o SKU para identificación rápida en listas
    codigo = db.Column(db.String(50), nullable=True)
    # Categoría para clasificar insumos (medicamento, material, consumible, equipo)
    categoria = db.Column(db.String(50), nullable=False, default='consumible')
    precio_compra = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Precio de costo
    precio_venta = db.Column(db.Numeric(10, 2), nullable=False, default=0)   # Precio de venta

    # Nota: la columna antigua `precio_unitario` fue renombrada en la DB a
    # `precio_venta`. Para mantener compatibilidad con código y plantillas
    # que aún usan `insumo.precio_unitario`, exponemos un property que
    # devuelve `precio_venta` en lugar de mapear otra columna (evita SELECT
    # sobre una columna inexistente si la BD ya fue migrada).
    @property
    def precio_unitario(self):
        return self.precio_venta
    cantidad_actual = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=10)
    unidad_medida = db.Column(db.String(20), nullable=False, default='unidad')
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    especialidades = db.relationship('InsumoEspecialidad', backref='insumo', lazy=True)
    movimientos = db.relationship('MovimientoInsumo', backref='insumo', lazy=True)
    
    @property
    def requiere_reposicion(self):
        return self.cantidad_actual < self.stock_minimo

    @property
    def stock(self):
        """Compatibilidad: algunas plantillas usan `insumo.stock`.
        Devolvemos `cantidad_actual` para evitar romper vistas antiguas.
        """
        return self.cantidad_actual
    
    @property
    def margen_ganancia(self):
        """Calcula el margen de ganancia porcentual"""
        if self.precio_compra > 0:
            return ((self.precio_venta - self.precio_compra) / self.precio_compra) * 100
        return 0
    
    def __repr__(self):
        return f'<Insumo {self.nombre}>'

# Tabla intermedia para insumos y especialidades
class InsumoEspecialidad(db.Model):
    """Relación entre insumos y especialidades"""
    __tablename__ = 'insumo_especialidades'
    
    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidades.id'), nullable=False)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<InsumoEspecialidad I:{self.insumo_id} E:{self.especialidad_id}>'

class ConsultaInsumo(db.Model):
    """Insumos utilizados en una consulta"""
    __tablename__ = 'consulta_insumos'
    
    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_uso = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con insumo para acceder a datos
    insumo_rel = db.relationship('Insumo', foreign_keys=[insumo_id])
    
    def __repr__(self):
        return f'<ConsultaInsumo C:{self.consulta_id} I:{self.insumo_id}>'

class MovimientoInsumo(db.Model):
    """Movimientos de inventario de insumos"""
    __tablename__ = 'movimientos_insumo'
    
    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, salida, ajuste
    cantidad = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.Text)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MovimientoInsumo {self.tipo} - {self.cantidad}>'

class Procedimiento(db.Model):
    """Modelo para procedimientos médicos"""
    __tablename__ = 'procedimientos'
    
    id = db.Column(db.Integer, primary_key=True)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidades.id'), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Procedimiento {self.nombre}>'


class ProcedimientoPrecio(db.Model):
    """Precios por procedimiento por médico o por especialidad.

    Regla de resolución (prioridad):
        1) precio específico para (procedimiento_id, medico_id)
        2) precio para (procedimiento_id, especialidad_id)
        3) procedimiento.precio (valor por defecto)
    """
    __tablename__ = 'procedimiento_precios'

    id = db.Column(db.Integer, primary_key=True)
    procedimiento_id = db.Column(db.Integer, db.ForeignKey('procedimientos.id'), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidades.id'), nullable=True)
    precio = db.Column(db.Numeric(10, 2), nullable=False)

    # Relaciones convenientes para plantillas
    procedimiento_rel = db.relationship('Procedimiento', foreign_keys=[procedimiento_id])
    medico = db.relationship('Medico', foreign_keys=[medico_id])
    especialidad = db.relationship('Especialidad', foreign_keys=[especialidad_id])

    def __repr__(self):
        target = f"medico:{self.medico_id}" if self.medico_id else f"esp:{self.especialidad_id}"
        return f'<ProcedimientoPrecio P:{self.procedimiento_id} {target}={self.precio}>'

class ConsultaProcedimiento(db.Model):
    """Procedimientos realizados en una consulta"""
    __tablename__ = 'consulta_procedimientos'
    
    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'), nullable=False)
    procedimiento_id = db.Column(db.Integer, db.ForeignKey('procedimientos.id'), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    observaciones = db.Column(db.Text)
    fecha_realizacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con procedimiento
    procedimiento_rel = db.relationship('Procedimiento', foreign_keys=[procedimiento_id])
    
    def __repr__(self):
        return f'<ConsultaProcedimiento C:{self.consulta_id} P:{self.procedimiento_id}>'
