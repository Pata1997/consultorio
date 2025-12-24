from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Cita, Consulta, Venta, Paciente
from datetime import date, timedelta

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    """Página principal - Redirige según el rol"""
    if current_user.rol == 'admin':
        return admin_dashboard()
    elif current_user.rol == 'medico':
        return medico_dashboard()
    elif current_user.rol == 'recepcionista':
        return recepcionista_dashboard()
    elif current_user.rol == 'cajero':
        return cajero_dashboard()
    else:
        return render_template('main/index.html')

def admin_dashboard():
    """Dashboard para administradores"""
    hoy = date.today()
    manana = hoy + timedelta(days=1)
    
    # Estadísticas del día
    citas_hoy = Cita.query.filter_by(fecha=hoy).count()
    citas_pendientes = Cita.query.filter_by(fecha=hoy, estado='pendiente').count()
    citas_confirmadas = Cita.query.filter_by(fecha=hoy, estado='confirmada').count()
    
    # Citas pendientes de mañana (para confirmar)
    citas_por_confirmar = Cita.query.filter_by(
        fecha=manana, 
        estado='pendiente'
    ).count()
    
    # Citas próximas
    citas_proximas = Cita.query.filter_by(fecha=hoy).order_by(Cita.hora).limit(10).all()
    
    return render_template('main/admin_dashboard.html',
                         citas_hoy=citas_hoy,
                         citas_pendientes=citas_pendientes,
                         citas_confirmadas=citas_confirmadas,
                         citas_por_confirmar=citas_por_confirmar,
                         citas_proximas=citas_proximas)

@bp.route('/medico/dashboard')
@login_required
def medico_dashboard():
    """Dashboard para médicos"""
    from app.decorators import require_roles
    from functools import wraps
    
    # Verificar rol
    if current_user.rol != 'medico':
        from flask import abort
        abort(403)
    
    hoy = date.today()
    medico_id = current_user.medico.id
    
    # Estadísticas del médico
    citas_hoy_pendientes = Cita.query.filter_by(
        medico_id=medico_id, fecha=hoy, estado='pendiente'
    ).count()
    
    citas_hoy_confirmadas = Cita.query.filter_by(
        medico_id=medico_id, fecha=hoy, estado='confirmada'
    ).count()
    
    pacientes_atendidos_hoy = Cita.query.filter_by(
        medico_id=medico_id, fecha=hoy, estado='atendida'
    ).count()
    
    # Próxima cita
    proxima_cita = Cita.query.filter(
        Cita.medico_id == medico_id,
        Cita.fecha >= hoy,
        Cita.estado.in_(['pendiente', 'confirmada'])
    ).order_by(Cita.fecha, Cita.hora).first()
    
    # Citas de hoy
    citas_hoy = Cita.query.filter_by(
        medico_id=medico_id, fecha=hoy
    ).filter(Cita.estado.in_(['pendiente', 'confirmada'])).order_by(Cita.hora).all()
    
    # Consultas completadas vs pendientes
    consultas_completadas = Consulta.query.filter_by(medico_id=medico_id).count()
    citas_totales = Cita.query.filter_by(medico_id=medico_id).count()
    
    return render_template('main/medico_dashboard.html',
                         citas_pendientes=citas_hoy_pendientes,
                         citas_confirmadas=citas_hoy_confirmadas,
                         pacientes_atendidos=pacientes_atendidos_hoy,
                         proxima_cita=proxima_cita,
                         citas_hoy=citas_hoy,
                         consultas_completadas=consultas_completadas,
                         citas_totales=citas_totales)

@bp.route('/recepcionista/dashboard')
@login_required
def recepcionista_dashboard():
    """Dashboard para recepcionistas"""
    from app.models import Medico
    from sqlalchemy import func
    
    if current_user.rol != 'recepcionista':
        from flask import abort
        abort(403)
    
    hoy = date.today()
    manana = hoy + timedelta(days=1)
    
    # Estadísticas del día (todos los médicos)
    citas_hoy = Cita.query.filter_by(fecha=hoy).count()
    citas_pendientes = Cita.query.filter_by(fecha=hoy, estado='pendiente').count()
    citas_confirmadas = Cita.query.filter_by(fecha=hoy, estado='confirmada').count()
    
    # Citas por confirmar (mañana)
    citas_por_confirmar_count = Cita.query.filter_by(
        fecha=manana,
        estado='pendiente'
    ).count()
    
    # Citas próximas de hoy
    citas_proximas = Cita.query.filter_by(fecha=hoy).order_by(Cita.hora).limit(10).all()
    
    # Estadísticas de ocupación
    total_slots_disponibles = 50  # Esto se podría calcular dinámicamente
    ocupacion = int((citas_hoy / total_slots_disponibles * 100)) if total_slots_disponibles > 0 else 0
    
    # Resumen por médico
    citas_por_medico = []
    medicos = Medico.query.all()
    for medico in medicos:
        citas = Cita.query.filter_by(medico_id=medico.id, fecha=hoy).all()
        if citas:
            citas_por_medico.append({
                'nombre': medico.nombre_completo,
                'total': len(citas),
                'pendientes': len([c for c in citas if c.estado == 'pendiente']),
                'confirmadas': len([c for c in citas if c.estado == 'confirmada']),
                'atendidas': len([c for c in citas if c.estado == 'atendida'])
            })
    
    return render_template('main/recepcionista_dashboard.html',
                         citas_hoy=citas_hoy,
                         citas_pendientes=citas_pendientes,
                         citas_confirmadas=citas_confirmadas,
                         citas_por_confirmar_count=citas_por_confirmar_count,
                         citas_proximas=citas_proximas,
                         ocupacion=ocupacion,
                         citas_por_medico=citas_por_medico)

@bp.route('/cajero/dashboard')
@login_required
def cajero_dashboard():
    """Dashboard para cajeros"""
    from app.models import Caja, Venta
    
    if current_user.rol != 'cajero':
        from flask import abort
        abort(403)
    
    hoy = date.today()
    
    # Verificar si tiene caja abierta
    caja_abierta = Caja.query.filter_by(
        usuario_apertura_id=current_user.id,
        estado='abierta'
    ).first()
    
    # Estadísticas del día
    ventas_hoy = Venta.query.filter(
        Venta.fecha >= hoy,
        Venta.fecha < hoy + timedelta(days=1)
    ).all()
    
    total_vendido_hoy = sum(float(v.total) for v in ventas_hoy if v.estado == 'pagada')
    ventas_pendientes = len([v for v in ventas_hoy if v.estado == 'pendiente'])
    ventas_pagadas = len([v for v in ventas_hoy if v.estado == 'pagada'])
    
    # Si tiene caja abierta, ventas de su caja
    ventas_mi_caja = []
    total_mi_caja = 0
    if caja_abierta:
        # Mostrar sólo facturas pagadas del día para la caja del cajero
        ventas_mi_caja = Venta.query.filter(
            Venta.caja_id == caja_abierta.id,
            Venta.estado == 'pagada',
            Venta.fecha >= hoy,
            Venta.fecha < hoy + timedelta(days=1)
        ).order_by(Venta.fecha.desc()).limit(10).all()
        total_mi_caja = sum(float(v.total) for v in ventas_mi_caja)
    
    return render_template('main/cajero_dashboard.html',
                         caja_abierta=caja_abierta,
                         ventas_hoy=len(ventas_hoy),
                         total_vendido_hoy=total_vendido_hoy,
                         ventas_pendientes=ventas_pendientes,
                         ventas_pagadas=ventas_pagadas,
                         ventas_mi_caja=ventas_mi_caja,
                         total_mi_caja=total_mi_caja)

@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard con estadísticas"""
    return render_template('main/dashboard.html')
