from app import db
from datetime import datetime

class Caja(db.Model):
    """Modelo para control de caja"""
    __tablename__ = 'cajas'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha_apertura = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_cierre = db.Column(db.DateTime)
    monto_inicial = db.Column(db.Numeric(10, 2), nullable=False)
    monto_final = db.Column(db.Numeric(10, 2))
    estado = db.Column(db.String(20), nullable=False, default='abierta')  # abierta, cerrada
    usuario_apertura_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario_cierre_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    observaciones = db.Column(db.Text)
    
    # Relaciones
    ventas = db.relationship('Venta', backref='caja', lazy=True)
    
    def __repr__(self):
        return f'<Caja {self.id} - {self.fecha_apertura}>'

class Venta(db.Model):
    """Modelo para ventas y facturación"""
    __tablename__ = 'ventas'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(50), unique=True, nullable=False)
    timbrado = db.Column(db.String(20))  # Timbrado de SET Paraguay
    
    # Datos de facturación
    ruc_factura = db.Column(db.String(20))
    nombre_factura = db.Column(db.String(200), nullable=False)
    direccion_factura = db.Column(db.Text)
    
    caja_id = db.Column(db.Integer, db.ForeignKey('cajas.id'), nullable=False)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'))
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    iva = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='pendiente')  # pendiente, pagada, anulada
    tipo = db.Column(db.String(20), nullable=False, default='contado')  # contado, credito
    usuario_registro_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    observaciones = db.Column(db.Text)
    
    # Relaciones
    detalles = db.relationship('VentaDetalle', backref='venta', lazy=True, cascade='all, delete-orphan')
    pagos = db.relationship('Pago', backref='venta', lazy=True)
    # Relación con paciente (para acceder desde plantillas como venta.paciente)
    paciente = db.relationship('Paciente', foreign_keys=[paciente_id], lazy=True)
    
    @property
    def saldo_pendiente(self):
        total_pagado = sum(pago.monto for pago in self.pagos if pago.estado == 'confirmado')
        return float(self.total) - total_pagado
    
    def __repr__(self):
        return f'<Venta {self.numero_factura}>'

class VentaDetalle(db.Model):
    """Detalle de items en la venta"""
    __tablename__ = 'venta_detalles'
    
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    concepto = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tipo_item = db.Column(db.String(20), nullable=False)  # consulta, procedimiento, insumo
    item_id = db.Column(db.Integer)  # ID del item original (procedimiento_id o insumo_id)
    
    def __repr__(self):
        return f'<VentaDetalle {self.concepto}>'

class FormaPago(db.Model):
    """Formas de pago disponibles"""
    __tablename__ = 'formas_pago'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)  # efectivo, tarjeta_debito, tarjeta_credito, cheque, transferencia
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    requiere_referencia = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<FormaPago {self.nombre}>'

class Pago(db.Model):
    """Modelo para pagos de ventas"""
    __tablename__ = 'pagos'
    
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    referencia = db.Column(db.String(100))  # Número de cheque, últimos 4 dígitos tarjeta, etc.
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False, default='confirmado')  # confirmado, rechazado
    usuario_registro_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    observaciones = db.Column(db.Text)
    
    # Relación con forma de pago
    forma_pago_rel = db.relationship('FormaPago', foreign_keys=[forma_pago_id])
    
    def __repr__(self):
        return f'<Pago {self.id} - {self.monto}>'

class NotaCredito(db.Model):
    """Notas de crédito"""
    __tablename__ = 'notas_credito'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    usuario_registro_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='activa')  # activa, anulada
    
    def __repr__(self):
        return f'<NotaCredito {self.numero}>'

class NotaDebito(db.Model):
    """Notas de débito"""
    __tablename__ = 'notas_debito'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    usuario_registro_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='activa')  # activa, anulada
    
    def __repr__(self):
        return f'<NotaDebito {self.numero}>'
