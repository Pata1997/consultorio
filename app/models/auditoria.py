from app import db
from datetime import datetime
import json

class AuditLog(db.Model):
    """Modelo para registro de auditoría del sistema"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    accion = db.Column(db.String(50), nullable=False)  # crear, editar, eliminar, aprobar, rechazar
    tabla = db.Column(db.String(100), nullable=False)  # usuarios, citas, consultas, ventas, etc.
    registro_id = db.Column(db.Integer, nullable=False)  # ID del registro afectado
    cambios = db.Column(db.JSON, nullable=True)  # Detalles de cambios {"campo": {"antes": val, "despues": val}}
    descripcion = db.Column(db.Text, nullable=True)  # Descripción adicional
    ip = db.Column(db.String(45), nullable=True)  # IPv4 o IPv6
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relación con usuario
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], lazy=True)
    
    def __repr__(self):
        return f'<AuditLog {self.id} - {self.accion} en {self.tabla}>'
    
    @staticmethod
    def registrar(usuario_id, accion, tabla, registro_id, cambios=None, descripcion=None, ip=None):
        """Registrar una acción en el audit log"""
        try:
            log = AuditLog(
                usuario_id=usuario_id,
                accion=accion,
                tabla=tabla,
                registro_id=registro_id,
                cambios=cambios,
                descripcion=descripcion,
                ip=ip
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            db.session.rollback()
            print(f"Error registrando audit log: {e}")
            return None
