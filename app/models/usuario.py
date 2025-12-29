from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class Usuario(UserMixin, db.Model):
    """Modelo para usuarios del sistema (médicos, recepcionistas, admin)"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # admin, medico, recepcionista, enfermera
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con médico si es usuario tipo médico
    medico = db.relationship('Medico', backref='usuario', uselist=False, lazy=True)
    
    def set_password(self, password):
        """Encriptar contraseña"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'

class Paciente(db.Model):
    """Modelo para pacientes"""
    __tablename__ = 'pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    ruc = db.Column(db.String(20))  # RUC para facturación
    razon_social = db.Column(db.String(200))  # Nombre comercial si tiene RUC
    condicion_tributaria = db.Column(db.String(100))  # Responsable inscripto, monotributo, etc.
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(1), nullable=False)  # M, F
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    direccion = db.Column(db.Text)
    direccion_facturacion = db.Column(db.Text)  # Dirección para facturación
    ciudad = db.Column(db.String(100))
    alergias = db.Column(db.Text)
    tipo_sangre = db.Column(db.String(5))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    citas = db.relationship('Cita', backref='paciente', lazy=True)
    consultas = db.relationship('Consulta', backref='paciente', lazy=True)
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def nombre_facturacion(self):
        """Retorna razón social si tiene RUC, sino nombre completo"""
        return self.razon_social if self.razon_social else self.nombre_completo
    
    @property
    def edad(self):
        from datetime import date
        today = date.today()
        return today.year - self.fecha_nacimiento.year - (
            (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
    
    def __repr__(self):
        return f'<Paciente {self.nombre_completo}>'

class Especialidad(db.Model):
    """Modelo para especialidades médicas"""
    __tablename__ = 'especialidades'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    precio_consulta = db.Column(db.Numeric(10, 2), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    medicos = db.relationship('MedicoEspecialidad', backref='especialidad', lazy=True)
    insumos = db.relationship('InsumoEspecialidad', backref='especialidad', lazy=True)
    procedimientos = db.relationship('Procedimiento', backref='especialidad', lazy=True)
    
    def __repr__(self):
        return f'<Especialidad {self.nombre}>'

class Medico(db.Model):
    """Modelo para médicos"""
    __tablename__ = 'medicos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    registro_profesional = db.Column(db.String(50), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    fecha_ingreso = db.Column(db.Date, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    especialidades = db.relationship('MedicoEspecialidad', backref='medico', lazy=True)
    horarios = db.relationship('HorarioAtencion', backref='medico', lazy=True)
    citas = db.relationship('Cita', backref='medico', lazy=True)
    consultas = db.relationship('Consulta', backref='medico', lazy=True)
    # Nota: Vacaciones/Permisos/Asistencias ahora están ligados a Usuario (usuario_id)
    # y no directamente a Medico. Acceder vía usuario.vacaciones / usuario.permisos.
    
    @property
    def nombre_completo(self):
        return f"Dr. {self.nombre} {self.apellido}"
    
    def __repr__(self):
        return f'<Medico {self.nombre_completo}>'

# Tabla intermedia para médicos y especialidades (muchos a muchos)
class MedicoEspecialidad(db.Model):
    """Relación entre médicos y especialidades"""
    __tablename__ = 'medico_especialidades'
    
    id = db.Column(db.Integer, primary_key=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidades.id'), nullable=False)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MedicoEspecialidad M:{self.medico_id} E:{self.especialidad_id}>'

class HorarioAtencion(db.Model):
    """Horarios de atención de los médicos"""
    __tablename__ = 'horarios_atencion'
    
    id = db.Column(db.Integer, primary_key=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0=Lunes, 6=Domingo
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    duracion_consulta = db.Column(db.Integer, nullable=False, default=30)  # minutos
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        return f'<Horario {dias[self.dia_semana]} {self.hora_inicio}-{self.hora_fin}>'
