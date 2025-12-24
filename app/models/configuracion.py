from app import db
from datetime import datetime

class ConfiguracionConsultorio(db.Model):
    """Configuración general del consultorio"""
    __tablename__ = 'configuracion_consultorio'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Datos generales
    nombre = db.Column(db.String(200), nullable=False)
    razon_social = db.Column(db.String(200))
    ruc = db.Column(db.String(20), nullable=False)
    direccion = db.Column(db.Text)
    telefono = db.Column(db.String(50))
    email = db.Column(db.String(120))
    sitio_web = db.Column(db.String(200))
    
    # Logo
    logo_filename = db.Column(db.String(200))
    logo_path = db.Column(db.String(500))
    
    # Datos de facturación
    punto_expedicion = db.Column(db.String(20), nullable=False, default='001-001')
    timbrado = db.Column(db.String(20))
    fecha_inicio_timbrado = db.Column(db.Date)
    fecha_fin_timbrado = db.Column(db.Date)
    numero_factura_actual = db.Column(db.Integer, default=1)
    
    # Información adicional
    slogan = db.Column(db.String(500))
    horario_atencion = db.Column(db.Text)
    
    # Control
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    actualizado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    def __repr__(self):
        return f'<ConfiguracionConsultorio {self.nombre}>'
    
    @staticmethod
    def get_configuracion():
        """Obtener la configuración actual (siempre debe haber solo un registro)"""
        config = ConfiguracionConsultorio.query.first()
        if not config:
            # Crear configuración por defecto si no existe
            config = ConfiguracionConsultorio(
                nombre='Consultorio Médico',
                ruc='80012345-6',
                punto_expedicion='001-001',
                numero_factura_actual=1
            )
            db.session.add(config)
            db.session.commit()
        return config
    
    def generar_numero_factura(self):
        """Generar el siguiente número de factura"""
        numero = f"{self.punto_expedicion}-{str(self.numero_factura_actual).zfill(7)}"
        self.numero_factura_actual += 1
        db.session.commit()
        return numero
