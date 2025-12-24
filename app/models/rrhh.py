from app import db
from datetime import datetime

class Vacacion(db.Model):
    """Modelo para vacaciones del personal médico"""
    __tablename__ = 'vacaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='anual')  # anual, extraordinaria
    estado = db.Column(db.String(20), nullable=False, default='pendiente')  # pendiente, aprobada, rechazada
    motivo = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    aprobado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_aprobacion = db.Column(db.DateTime)
    observaciones = db.Column(db.Text)
    
    @property
    def dias_solicitados(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1
    
    def __repr__(self):
        return f'<Vacacion M:{self.medico_id} {self.fecha_inicio} - {self.fecha_fin}>'

class Permiso(db.Model):
    """Modelo para permisos del personal"""
    __tablename__ = 'permisos'
    
    id = db.Column(db.Integer, primary_key=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time)
    hora_fin = db.Column(db.Time)
    tipo = db.Column(db.String(20), nullable=False)  # medico, personal, familiar, enfermedad
    motivo = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='pendiente')  # pendiente, aprobado, rechazado
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    aprobado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_aprobacion = db.Column(db.DateTime)
    observaciones = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Permiso M:{self.medico_id} {self.fecha}>'

class Asistencia(db.Model):
    """Modelo para registro de asistencia del personal"""
    __tablename__ = 'asistencias'
    
    id = db.Column(db.Integer, primary_key=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora_entrada = db.Column(db.Time, nullable=False)
    hora_salida = db.Column(db.Time)
    estado = db.Column(db.String(20), nullable=False, default='presente')  # presente, tarde, ausente
    observaciones = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Asistencia M:{self.medico_id} {self.fecha}>'
