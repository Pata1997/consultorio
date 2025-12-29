"""
Utilidades para recursos humanos - gestión de disponibilidad médica
"""
from datetime import date, time
from app.models import Vacacion, Permiso, Medico


def medico_disponible_en_fecha(medico_id, fecha, hora_inicio=None, hora_fin=None):
    """
    Verifica si un médico está disponible en fecha/hora específica
    Considera vacaciones y permisos aprobados
    
    Args:
        medico_id: ID del médico
        fecha: date object o string YYYY-MM-DD
        hora_inicio: time object (opcional, para verificar permisos por hora)
        hora_fin: time object (opcional, para verificar permisos por hora)
    
    Returns:
        tuple: (disponible: bool, motivo_si_no: str o None)
        
    Ejemplos:
        >>> medico_disponible_en_fecha(1, date(2025, 1, 15))
        (False, "De vacaciones del 10/01 al 20/01")
        
        >>> medico_disponible_en_fecha(2, date(2025, 1, 5), time(14, 0), time(15, 0))
        (False, "Permiso de 14:00 a 16:00")
    """
    # Convertir string a date si es necesario
    if isinstance(fecha, str):
        from datetime import datetime
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    
    # Obtener el usuario asociado al médico para verificar vacaciones/permiso por usuario
    medico = Medico.query.get(medico_id)
    if not medico or not medico.usuario:
        return True, None
    usuario_id = medico.usuario.id
    
    # 1. Verificar vacaciones aprobadas (por usuario)
    vacacion = Vacacion.query.filter(
        Vacacion.usuario_id == usuario_id,
        Vacacion.estado == 'aprobada',
        Vacacion.fecha_inicio <= fecha,
        Vacacion.fecha_fin >= fecha
    ).first()
    
    if vacacion:
        return False, f"De vacaciones del {vacacion.fecha_inicio.strftime('%d/%m')} al {vacacion.fecha_fin.strftime('%d/%m')}"
    
    # 2. Verificar permisos aprobados en esa fecha
    permiso = Permiso.query.filter(
        Permiso.usuario_id == usuario_id,
        Permiso.fecha == fecha,
        Permiso.estado == 'aprobado'
    ).first()
    
    if permiso:
        # Si no tiene horas específicas = permiso todo el día
        if not permiso.hora_inicio or not permiso.hora_fin:
            return False, "Permiso todo el día"
        
        # Si se proporcionaron horas para verificar
        if hora_inicio and hora_fin:
            # Verificar si hay solapamiento de horarios
            # Permiso: 14:00-16:00, Cita: 15:00-16:00 → Solapa
            # Permiso: 14:00-16:00, Cita: 16:00-17:00 → No solapa
            if permiso.hora_inicio < hora_fin and permiso.hora_fin > hora_inicio:
                return False, f"Permiso de {permiso.hora_inicio.strftime('%H:%M')} a {permiso.hora_fin.strftime('%H:%M')}"
        else:
            # Sin horas específicas para verificar, pero hay permiso → marcar como no disponible
            return False, f"Permiso de {permiso.hora_inicio.strftime('%H:%M')} a {permiso.hora_fin.strftime('%H:%M')}"
    
    return True, None


def obtener_medicos_disponibles(medicos, fecha, hora_inicio=None, hora_fin=None):
    """
    Filtra lista de médicos según disponibilidad en fecha/hora
    Agrega atributo 'disponible' y 'motivo_no_disponible' a cada médico
    
    Args:
        medicos: Lista de objetos Medico
        fecha: date object
        hora_inicio: time object (opcional)
        hora_fin: time object (opcional)
    
    Returns:
        tuple: (medicos_disponibles: list, medicos_no_disponibles: list)
        
    Ejemplo:
        disponibles, no_disponibles = obtener_medicos_disponibles(
            medicos, date(2025, 1, 15), time(14, 0), time(15, 0)
        )
    """
    medicos_disponibles = []
    medicos_no_disponibles = []
    
    for medico in medicos:
        disponible, motivo = medico_disponible_en_fecha(
            medico.id, fecha, hora_inicio, hora_fin
        )
        
        # Agregar atributos temporales para uso en templates
        medico.disponible = disponible
        medico.motivo_no_disponible = motivo
        
        if disponible:
            medicos_disponibles.append(medico)
        else:
            medicos_no_disponibles.append(medico)
    
    return medicos_disponibles, medicos_no_disponibles
