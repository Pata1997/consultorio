"""Utilidades para auditoría"""
from app.models.auditoria import AuditLog
from flask import request
from flask_login import current_user

def get_ip():
    """Obtener IP del cliente"""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    return request.remote_addr

def audit(accion, tabla, registro_id, cambios=None, descripcion=None):
    """
    Registrar una acción en el audit log
    
    Args:
        accion: str - crear, editar, eliminar, aprobar, rechazar, etc.
        tabla: str - nombre de la tabla afectada
        registro_id: int - ID del registro
        cambios: dict - opcional, detalles de cambios {"campo": {"antes": val, "despues": val}}
        descripcion: str - opcional, descripción adicional
    """
    if current_user and current_user.is_authenticated:
        AuditLog.registrar(
            usuario_id=current_user.id,
            accion=accion,
            tabla=tabla,
            registro_id=registro_id,
            cambios=cambios,
            descripcion=descripcion,
            ip=get_ip()
        )
