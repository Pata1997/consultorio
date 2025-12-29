"""Funciones de control de acceso basado en roles (RBAC)"""
from flask_login import current_user

def get_filtered_query(model, **filters):
    """
    Retorna query filtrado automáticamente según el rol del usuario
    Para médicos, filtra por medico_id
    Para admin y otros roles, retorna todo
    """
    query = model.query
    
    # Si es médico, filtrar por su ID
    if current_user.rol == 'medico' and hasattr(current_user, 'medico') and current_user.medico:
        if hasattr(model, 'medico_id'):
            query = query.filter_by(medico_id=current_user.medico.id)
    
    # Aplicar filtros adicionales
    if filters:
        query = query.filter_by(**filters)
    
    return query

def can_access_data(obj):
    """
    Verifica si el usuario actual puede acceder a un objeto específico
    """
    # Admin puede todo
    if current_user.rol == 'admin':
        return True
    
    # Médico solo puede acceder a sus propios datos
    if current_user.rol == 'medico':
        if hasattr(obj, 'medico_id') and hasattr(current_user, 'medico'):
            return obj.medico_id == current_user.medico.id
    
    # Recepcionista puede ver todo (lectura)
    if current_user.rol == 'recepcionista':
        return True
    
    return False

def get_menu_items():
    """Retorna items del menú según el rol del usuario"""
    if not current_user.is_authenticated:
        return []
    
    if current_user.rol == 'admin':
        return [
            {'name': 'Dashboard', 'icon': 'speedometer2', 'url': 'main.index'},
            {'name': 'Agendamiento', 'icon': 'calendar-check', 'url': 'agendamiento.listar_citas', 'submenu': [
                {'name': 'Citas', 'url': 'agendamiento.listar_citas'},
                {'name': 'Nueva Cita', 'url': 'agendamiento.nueva_cita'},
                {'name': 'Citas por Confirmar', 'url': 'agendamiento.citas_por_confirmar'},
                {'name': 'Pacientes', 'url': 'agendamiento.listar_pacientes'},
            ]},
            {'name': 'Consultorio', 'icon': 'clipboard-pulse', 'url': 'consultorio.listar_consultas', 'submenu': [
                {'name': 'Consultas', 'url': 'consultorio.listar_consultas'},
                {'name': 'Insumos', 'url': 'consultorio.listar_insumos'},
            ]},
            {'name': 'RRHH', 'icon': 'people', 'url': 'rrhh.listar_medicos', 'submenu': [
                {'name': 'Médicos', 'url': 'rrhh.listar_medicos'},
                {'name': 'Horarios', 'url': 'rrhh.listar_horarios'},
                {'name': 'Vacaciones', 'url': 'rrhh.listar_vacaciones'},
                {'name': 'Permisos', 'url': 'rrhh.listar_permisos'},
            ]},
        ]
    
    elif current_user.rol == 'medico':
        return [
            {'name': 'Dashboard', 'icon': 'speedometer2', 'url': 'main.medico_dashboard'},
            {'name': 'Consultorio', 'icon': 'clipboard-pulse', 'url': 'consultorio.mis_consultas', 'submenu': [
                {'name': 'Mis Citas Hoy', 'url': 'consultorio.mis_citas_hoy'},
                {'name': 'Mis Consultas', 'url': 'consultorio.mis_consultas'},
                {'name': 'Insumos', 'url': 'consultorio.listar_insumos'},
            ]},
        ]
    
    elif current_user.rol == 'recepcionista':
        return [
            {'name': 'Dashboard', 'icon': 'speedometer2', 'url': 'main.recepcionista_dashboard'},
            {'name': 'Agendamiento', 'icon': 'calendar-check', 'url': 'agendamiento.listar_citas', 'submenu': [
                {'name': 'Citas', 'url': 'agendamiento.listar_citas'},
                {'name': 'Nueva Cita', 'url': 'agendamiento.nueva_cita'},
                {'name': 'Citas por Confirmar', 'url': 'agendamiento.citas_por_confirmar'},
                {'name': 'Pacientes', 'url': 'agendamiento.listar_pacientes'},
            ]},
        ]
    
    elif current_user.rol in ['cajero', 'cajera']:
        return [
            {'name': 'Dashboard', 'icon': 'speedometer2', 'url': 'main.cajero_dashboard'},
            {'name': 'Caja', 'icon': 'cash-stack', 'url': 'facturacion.estado_caja', 'submenu': [
                {'name': 'Estado de Caja', 'url': 'facturacion.estado_caja'},
                {'name': 'Ventas pendientes', 'url': 'facturacion.ventas_pendientes'},
                {'name': 'Nueva Venta', 'url': 'facturacion.nueva_venta'},
                {'name': 'Ventas', 'url': 'facturacion.listar_ventas'},
            ]},
            {'name': 'Reportes', 'icon': 'graph-up', 'url': 'facturacion.reporte_ventas'},
        ]
    
    return []
