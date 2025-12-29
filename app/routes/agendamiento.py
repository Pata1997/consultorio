from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Cita, Paciente, Medico, Especialidad, MedicoEspecialidad, HorarioAtencion, Vacacion, Permiso
from app.utils.rrhh_utils import medico_disponible_en_fecha
from datetime import datetime, date, time, timedelta
from sqlalchemy import and_, or_, func

bp = Blueprint('agendamiento', __name__, url_prefix='/agendamiento')

@bp.route('/citas')
@login_required
def listar_citas():
    """Listar todas las citas"""
    fecha_filtro = request.args.get('fecha', date.today().isoformat())
    estado_filtro = request.args.get('estado', 'todas')
    
    query = Cita.query
    
    # Filtrar por médico si es usuario médico
    if current_user.rol == 'medico' and current_user.medico:
        query = query.filter_by(medico_id=current_user.medico.id)
    
    # Filtrar por fecha
    if fecha_filtro:
        query = query.filter_by(fecha=datetime.strptime(fecha_filtro, '%Y-%m-%d').date())
    
    # Filtrar por estado
    if estado_filtro != 'todas':
        query = query.filter_by(estado=estado_filtro)
    
    citas = query.order_by(Cita.hora).all()
    
    return render_template('agendamiento/listar_citas.html', 
                         citas=citas,
                         fecha_filtro=fecha_filtro,
                         estado_filtro=estado_filtro)

@bp.route('/citas/confirmar/<int:id>', methods=['GET', 'POST'])
@login_required
def confirmar_cita(id):
    """Confirmar una cita pendiente"""
    cita = Cita.query.get_or_404(id)
    
    if cita.estado != 'pendiente':
        flash('Solo se pueden confirmar citas pendientes', 'warning')
        return redirect(url_for('agendamiento.listar_citas'))
    
    cita.estado = 'confirmada'
    cita.fecha_confirmacion = datetime.utcnow()
    db.session.commit()
    
    flash('Cita confirmada exitosamente', 'success')
    return redirect(url_for('agendamiento.listar_citas'))

@bp.route('/citas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cita(id):
    """Editar una cita existente"""
    cita = Cita.query.get_or_404(id)
    
    if cita.estado not in ['pendiente', 'confirmada']:
        flash('No se puede editar una cita cancelada o atendida', 'warning')
        return redirect(url_for('agendamiento.listar_citas'))
    
    if request.method == 'POST':
        fecha = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
        hora = datetime.strptime(request.form.get('hora'), '%H:%M').time()
        
        # Validar que la fecha no sea pasada
        if fecha < date.today():
            flash('No se pueden agendar citas en fechas pasadas', 'danger')
            return redirect(url_for('agendamiento.editar_cita', id=id))
        
        # Verificar disponibilidad (excluyendo la cita actual)
        cita_existente = Cita.query.filter(
            Cita.id != id,
            Cita.medico_id == cita.medico_id,
            Cita.fecha == fecha,
            Cita.hora == hora,
            Cita.estado.in_(['pendiente', 'confirmada'])
        ).first()
        
        if cita_existente:
            flash('El horario seleccionado ya está ocupado', 'danger')
            return redirect(url_for('agendamiento.editar_cita', id=id))
        
        cita.fecha = fecha
        cita.hora = hora
        cita.motivo = request.form.get('motivo', '')
        
        db.session.commit()
        
        flash('Cita actualizada exitosamente', 'success')
        return redirect(url_for('agendamiento.listar_citas'))
    
    return render_template('agendamiento/editar_cita.html', cita=cita)

@bp.route('/citas/cancelar/<int:id>', methods=['POST'])
@login_required
def cancelar_cita(id):
    """Cancelar una cita"""
    cita = Cita.query.get_or_404(id)
    
    if cita.estado not in ['pendiente', 'confirmada']:
        flash('No se puede cancelar esta cita', 'warning')
        return redirect(url_for('agendamiento.listar_citas'))
    # Permitir distinguir si la cancelación la realizó el paciente
    cancelada_por = request.form.get('cancelada_por')
    if cancelada_por == 'paciente':
        # nuevo estado corto para indicar cancelada por paciente
        cita.estado = 'cancelada_paciente'
        cita.observaciones = request.form.get('observaciones', 'Cancelada por el paciente')
    else:
        cita.estado = 'cancelada'
        cita.observaciones = request.form.get('observaciones', 'Cita cancelada')
    db.session.commit()
    
    flash('Cita cancelada exitosamente', 'info')
    return redirect(url_for('agendamiento.listar_citas'))

@bp.route('/citas/por-confirmar')
@login_required
def citas_por_confirmar():
    """Vista de citas pendientes de mañana para confirmar con pacientes"""
    manana = date.today() + timedelta(days=1)
    
    # Obtener citas pendientes de mañana
    citas = Cita.query.filter_by(
        fecha=manana,
        estado='pendiente'
    ).order_by(Cita.hora).all()
    
    return render_template('agendamiento/citas_por_confirmar.html',
                         citas=citas,
                         fecha_objetivo=manana)

@bp.route('/citas/marcar-contactado/<int:id>', methods=['POST'])
@login_required
def marcar_contactado(id):
    """Marcar una cita como 'paciente contactado'"""
    cita = Cita.query.get_or_404(id)
    
    # Agregar nota de contacto en observaciones
    nota_contacto = f"[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Paciente contactado por {current_user.username}"
    
    if cita.observaciones:
        cita.observaciones += f"\n{nota_contacto}"
    else:
        cita.observaciones = nota_contacto
    
    db.session.commit()
    
    flash('Cita marcada como contactada', 'success')
    return redirect(url_for('agendamiento.citas_por_confirmar'))

@bp.route('/citas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_cita():
    """Crear nueva cita"""
    if request.method == 'POST':
        # Convertir a enteros los IDs que vienen como strings del formulario
        paciente_id = int(request.form.get('paciente_id'))
        especialidad_id = int(request.form.get('especialidad_id'))
        medico_id = int(request.form.get('medico_id'))
        fecha = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
        hora = datetime.strptime(request.form.get('hora'), '%H:%M').time()
        motivo = request.form.get('motivo', '')
        
        # Validar que la fecha no sea pasada
        if fecha < date.today():
            flash('No se pueden agendar citas en fechas pasadas', 'danger')
            return redirect(url_for('agendamiento.nueva_cita'))
        
        # Verificar disponibilidad del médico (vacaciones/permisos)
        # Calcular hora_fin (asumiendo citas de 30 minutos)
        hora_fin = (datetime.combine(fecha, hora) + timedelta(minutes=30)).time()
        disponible, motivo_no_disponible = medico_disponible_en_fecha(
            medico_id, fecha, hora, hora_fin
        )
        
        if not disponible:
            flash(f'No se puede agendar: {motivo_no_disponible}', 'danger')
            return redirect(url_for('agendamiento.nueva_cita'))
        
        # Verificar disponibilidad
        cita_existente = Cita.query.filter_by(
            medico_id=medico_id,
            fecha=fecha,
            hora=hora
        ).filter(Cita.estado.in_(['pendiente', 'confirmada'])).first()
        
        if cita_existente:
            flash('El horario seleccionado ya está ocupado', 'danger')
            return redirect(url_for('agendamiento.nueva_cita'))
        
        # Crear cita
        cita = Cita(
            paciente_id=paciente_id,
            medico_id=medico_id,
            especialidad_id=especialidad_id,
            fecha=fecha,
            hora=hora,
            motivo=motivo,
            estado='pendiente',
            usuario_registro_id=current_user.id
        )
        
        db.session.add(cita)
        db.session.commit()
        
        flash('Cita agendada exitosamente', 'success')
        return redirect(url_for('agendamiento.listar_citas'))
    
    # GET - mostrar formulario
    pacientes = Paciente.query.filter_by(activo=True).order_by(Paciente.apellido).all()
    especialidades = Especialidad.query.filter_by(activo=True).all()
    
    return render_template('agendamiento/nueva_cita.html',
                         pacientes=pacientes,
                         especialidades=especialidades)

@bp.route('/api/disponibilidad-semanal/<int:medico_id>')
@login_required
def disponibilidad_semanal(medico_id):
    """API para obtener disponibilidad semanal del médico"""
    from datetime import timedelta
    
    # Obtener fecha inicial (lunes de la semana solicitada)
    fecha_str = request.args.get('fecha', date.today().isoformat())
    fecha_base = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    
    # Calcular el lunes de esa semana
    dias_desde_lunes = fecha_base.weekday()
    lunes = fecha_base - timedelta(days=dias_desde_lunes)
    
    # Generar 7 días desde el lunes
    dias_semana = [lunes + timedelta(days=i) for i in range(7)]
    
    # Obtener horarios del médico
    horarios = HorarioAtencion.query.filter_by(
        medico_id=medico_id,
        activo=True
    ).all()
    
    # Crear diccionario de horarios por día (usando número de día 0-6)
    horarios_por_dia = {}
    for h in horarios:
        if h.dia_semana not in horarios_por_dia:
            horarios_por_dia[h.dia_semana] = []
        horarios_por_dia[h.dia_semana].append({
            'hora_inicio': h.hora_inicio,
            'hora_fin': h.hora_fin
        })
    
    # Obtener vacaciones del médico
    medico = Medico.query.get_or_404(medico_id)
    vacaciones = Vacacion.query.filter(
        Vacacion.medico_id == medico_id,
        Vacacion.estado == 'aprobada',
        Vacacion.fecha_inicio <= dias_semana[-1],
        Vacacion.fecha_fin >= dias_semana[0]
    ).all()
    
    # Obtener permisos del médico
    permisos = Permiso.query.filter(
        Permiso.medico_id == medico_id,
        Permiso.estado == 'aprobado',
        Permiso.fecha.in_(dias_semana)
    ).all()
    
    # Obtener citas confirmadas
    citas = Cita.query.filter(
        Cita.medico_id == medico_id,
        Cita.fecha.in_(dias_semana),
        Cita.estado.in_(['pendiente', 'confirmada'])
    ).all()
    
    # Construir estructura de datos
    dias_espanol = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']
    calendario = []
    hoy = date.today()
    
    for fecha in dias_semana:
        dia_numero = fecha.weekday()  # 0=Lunes, 6=Domingo
        dia_label = f"{dias_espanol[dia_numero]} {fecha.day}"
        es_pasado = fecha < hoy
        
        # Verificar si el médico trabaja este día
        if dia_numero not in horarios_por_dia:
            calendario.append({
                'fecha': fecha.isoformat(),
                'dia_semana': dia_label,
                'trabaja': False,
                'es_pasado': es_pasado,
                'slots': []
            })
            continue
        
        # Verificar vacaciones
        en_vacaciones = any(
            v.fecha_inicio <= fecha <= v.fecha_fin
            for v in vacaciones
        )
        
        if en_vacaciones:
            calendario.append({
                'fecha': fecha.isoformat(),
                'dia_semana': dia_label,
                'trabaja': True,
                'en_vacaciones': True,
                'es_pasado': es_pasado,
                'slots': []
            })
            continue
        
        # Generar slots de 30 minutos para todos los horarios del día
        slots = []
        for horario in horarios_por_dia[dia_numero]:
            hora_inicio = horario['hora_inicio']
            hora_fin = horario['hora_fin']
            
            hora_actual = datetime.combine(fecha, hora_inicio)
            hora_fin_dt = datetime.combine(fecha, hora_fin)
            
            while hora_actual < hora_fin_dt:
                hora_str = hora_actual.strftime('%H:%M')
                
                # Verificar si el slot es pasado
                ahora = datetime.now()
                slot_pasado = (fecha < hoy) or (fecha == hoy and hora_actual.time() < ahora.time())
                
                # Verificar si hay permiso en este horario
                tiene_permiso = any(
                    p.fecha == fecha and 
                    p.hora_inicio <= hora_actual.time() < p.hora_fin
                    for p in permisos
                )
                
                # Verificar si hay cita
                tiene_cita = any(
                    c.fecha == fecha and c.hora == hora_actual.time()
                    for c in citas
                )
                
                # Determinar estado del slot
                if slot_pasado:
                    estado = 'pasado'
                elif tiene_permiso:
                    estado = 'permiso'
                elif tiene_cita:
                    estado = 'ocupado'
                else:
                    estado = 'disponible'
                
                slots.append({
                    'hora': hora_str,
                    'estado': estado
                })
                
                hora_actual += timedelta(minutes=30)
        
        calendario.append({
            'fecha': fecha.isoformat(),
            'dia_semana': dia_label,
            'trabaja': True,
            'en_vacaciones': False,
            'es_pasado': es_pasado,
            'slots': slots
        })
    
    # Información del mes para mostrar
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    mes_inicio = meses[lunes.month - 1]
    mes_fin = meses[dias_semana[-1].month - 1]
    
    # Formato del período
    if lunes.month == dias_semana[-1].month:
        periodo = f"{mes_inicio} {lunes.year}"
    else:
        periodo = f"{mes_inicio} - {mes_fin} {lunes.year}"
    
    return jsonify({
        'medico': {
            'id': medico.id,
            'nombre': f"Dr(a). {medico.usuario.username}" if medico.usuario else "Doctor"
        },
        'semana_inicio': lunes.isoformat(),
        'semana_fin': dias_semana[-1].isoformat(),
        'periodo': periodo,
        'calendario': calendario
    })

@bp.route('/api/buscar-pacientes')
@login_required
def buscar_pacientes():
    """API para buscar pacientes por nombre o cédula"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    # Buscar por nombre, apellido o cédula
    pacientes = Paciente.query.filter(
        and_(
            Paciente.activo == True,
            or_(
                Paciente.nombre.ilike(f'%{query}%'),
                Paciente.apellido.ilike(f'%{query}%'),
                Paciente.cedula.ilike(f'%{query}%')
            )
        )
    ).limit(10).all()
    
    resultados = [{
        'id': p.id,
        'nombre_completo': f"{p.nombre} {p.apellido}",
        'cedula': p.cedula,
        'texto': f"{p.nombre} {p.apellido} - CI: {p.cedula}"
    } for p in pacientes]
    
    return jsonify(resultados)


@bp.route('/api/procedimientos/precios')
@login_required
def api_procedimientos_precios():
    """Devuelve lista de procedimientos de una especialidad con precio resuelto

    Parámetros: medico_id (int, opcional), especialidad_id (int, requerido)
    """
    medico_id = request.args.get('medico_id', type=int)
    especialidad_id = request.args.get('especialidad_id', type=int)

    if not especialidad_id:
        return jsonify({'error': 'especialidad_id requerido'}), 400

    from app.models import Procedimiento, ProcedimientoPrecio

    procedimientos = Procedimiento.query.filter_by(especialidad_id=especialidad_id, activo=True).all()
    salida = []
    for p in procedimientos:
        precio = None
        if medico_id:
            pp = ProcedimientoPrecio.query.filter_by(procedimiento_id=p.id, medico_id=medico_id).first()
            if pp:
                precio = float(pp.precio)
        if precio is None:
            pp2 = ProcedimientoPrecio.query.filter_by(procedimiento_id=p.id, especialidad_id=especialidad_id).first()
            if pp2:
                precio = float(pp2.precio)
        if precio is None:
            precio = float(p.precio) if p.precio is not None else 0.0

        salida.append({'id': p.id, 'nombre': p.nombre, 'precio': precio})

    return jsonify(salida)

@bp.route('/api/buscar-especialidades')
@login_required
def buscar_especialidades():
    """API para buscar especialidades por nombre"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    especialidades = Especialidad.query.filter(
        and_(
            Especialidad.activo == True,
            Especialidad.nombre.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    resultados = [{
        'id': e.id,
        'nombre': e.nombre,
        'descripcion': e.descripcion or ''
    } for e in especialidades]
    
    return jsonify(resultados)

@bp.route('/api/medicos-por-especialidad/<int:especialidad_id>')
@login_required
def medicos_por_especialidad(especialidad_id):
    """API: Obtener médicos disponibles por especialidad"""
    fecha_str = request.args.get('fecha', date.today().isoformat())
    fecha_consulta = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    
    # Buscar médicos de la especialidad
    medicos_especialidad = MedicoEspecialidad.query.filter_by(
        especialidad_id=especialidad_id
    ).all()
    
    medicos_disponibles = []
    medicos_no_disponibles = []
    
    for me in medicos_especialidad:
        medico = me.medico
        
        # Verificar que esté activo
        if not medico.activo:
            continue
        
        # Verificar disponibilidad (vacaciones/permisos) - sin horario específico
        disponible, motivo = medico_disponible_en_fecha(
            medico.id, fecha_consulta, None, None
        )
        
        medico_info = {
            'id': medico.id,
            'nombre': medico.nombre_completo,
            'registro': medico.registro_profesional
        }
        
        if disponible:
            medicos_disponibles.append(medico_info)
        else:
            medico_info['motivo_no_disponible'] = motivo
            medicos_no_disponibles.append(medico_info)
    
    return jsonify({
        'disponibles': medicos_disponibles,
        'no_disponibles': medicos_no_disponibles
    })

@bp.route('/api/horarios-disponibles/<int:medico_id>')
@login_required
def horarios_disponibles(medico_id):
    """API: Obtener horarios disponibles de un médico"""
    fecha_str = request.args.get('fecha')
    fecha_consulta = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    dia_semana = fecha_consulta.weekday()  # 0=Lunes, 6=Domingo
    
    # Obtener horario del médico para ese día
    horario = HorarioAtencion.query.filter_by(
        medico_id=medico_id,
        dia_semana=dia_semana,
        activo=True
    ).first()
    
    if not horario:
        return jsonify([])
    
    # Generar slots de tiempo
    slots = []
    hora_actual = datetime.combine(fecha_consulta, horario.hora_inicio)
    hora_fin = datetime.combine(fecha_consulta, horario.hora_fin)
    duracion = timedelta(minutes=horario.duracion_consulta)
    
    while hora_actual < hora_fin:
        # Verificar si el slot está ocupado
        cita_existente = Cita.query.filter_by(
            medico_id=medico_id,
            fecha=fecha_consulta,
            hora=hora_actual.time()
        ).filter(Cita.estado.in_(['pendiente', 'confirmada'])).first()
        
        if not cita_existente:
            slots.append(hora_actual.strftime('%H:%M'))
        
        hora_actual += duracion
    
    return jsonify(slots)

@bp.route('/pacientes')
@login_required
def listar_pacientes():
    """Listar pacientes. Acepta parámetros 'q' o 'buscar' y realiza búsqueda por aproximación
    en nombre completo (nombre + apellido) y cédula."""
    # aceptar ambos parámetros para compatibilidad (q o buscar)
    busqueda = request.args.get('q') or request.args.get('buscar') or ''

    query = Paciente.query.filter_by(activo=True)

    if busqueda:
        pattern = f"%{busqueda}%"
        # Buscar por nombre, apellido, concatenación nombre + ' ' + apellido, y cédula
        nombre_completo = func.concat(Paciente.nombre, ' ', Paciente.apellido)
        query = query.filter(
            or_(
                Paciente.nombre.ilike(pattern),
                Paciente.apellido.ilike(pattern),
                nombre_completo.ilike(pattern),
                Paciente.cedula.ilike(pattern)
            )
        )

    pacientes = query.order_by(Paciente.apellido).all()

    return render_template('agendamiento/listar_pacientes.html', 
                         pacientes=pacientes,
                         busqueda=busqueda)


@bp.route('/pacientes/<int:id>')
@login_required
def ver_paciente(id):
    """Ver ficha completa del paciente"""
    from app.models import Consulta, Venta

    paciente = Paciente.query.get_or_404(id)

    ultimas_consultas = Consulta.query.filter_by(paciente_id=id).order_by(Consulta.fecha.desc()).limit(10).all()
    ultimas_citas = Cita.query.filter_by(paciente_id=id).order_by(Cita.fecha.desc()).limit(10).all()
    # Próxima cita (fecha >= hoy)
    try:
        proxima_cita = Cita.query.filter(Cita.paciente_id == id, Cita.fecha >= date.today()).order_by(Cita.fecha.asc()).first()
    except Exception:
        proxima_cita = None
    ventas = Venta.query.filter_by(paciente_id=id).order_by(Venta.fecha.desc()).limit(10).all()

    return render_template('agendamiento/ficha_paciente.html',
                           paciente=paciente,
                           ultimas_consultas=ultimas_consultas,
                           ultimas_citas=ultimas_citas,
                           ventas=ventas,
                           proxima_cita=proxima_cita)

@bp.route('/pacientes/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_paciente():
    """Registrar nuevo paciente"""
    if request.method == 'POST':
        paciente = Paciente(
            nombre=request.form.get('nombre'),
            apellido=request.form.get('apellido'),
            cedula=request.form.get('cedula'),
            ruc=request.form.get('ruc'),
            razon_social=request.form.get('razon_social'),
            fecha_nacimiento=datetime.strptime(request.form.get('fecha_nacimiento'), '%Y-%m-%d').date(),
            sexo=request.form.get('sexo'),
            telefono=request.form.get('telefono'),
            email=request.form.get('email'),
            direccion=request.form.get('direccion'),
            ciudad=request.form.get('ciudad'),
            alergias=request.form.get('alergias'),
            tipo_sangre=request.form.get('tipo_sangre')
        )
        
        db.session.add(paciente)
        db.session.commit()
        
        flash('Paciente registrado exitosamente', 'success')
        return redirect(url_for('agendamiento.listar_pacientes'))
    
    return render_template('agendamiento/nuevo_paciente.html')

@bp.route('/pacientes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    """Editar paciente existente"""
    paciente = Paciente.query.get_or_404(id)
    
    if request.method == 'POST':
        paciente.nombre = request.form.get('nombre')
        paciente.apellido = request.form.get('apellido')
        paciente.cedula = request.form.get('cedula')
        paciente.ruc = request.form.get('ruc')
        paciente.razon_social = request.form.get('razon_social')
        paciente.fecha_nacimiento = datetime.strptime(request.form.get('fecha_nacimiento'), '%Y-%m-%d').date()
        paciente.sexo = request.form.get('sexo')
        paciente.telefono = request.form.get('telefono')
        paciente.email = request.form.get('email')
        paciente.direccion = request.form.get('direccion')
        paciente.ciudad = request.form.get('ciudad')
        paciente.alergias = request.form.get('alergias')
        paciente.tipo_sangre = request.form.get('tipo_sangre')

        db.session.commit()

        flash('Paciente actualizado exitosamente', 'success')
        return redirect(url_for('agendamiento.listar_pacientes'))
    
    return render_template('agendamiento/editar_paciente.html', paciente=paciente)
