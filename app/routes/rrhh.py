from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Vacacion, Permiso, Asistencia, Medico, HorarioAtencion, Usuario, Especialidad, MedicoEspecialidad
from datetime import datetime, date, time

bp = Blueprint('rrhh', __name__, url_prefix='/rrhh')

@bp.route('/vacaciones')
@login_required
def listar_vacaciones():
    """Listar vacaciones"""
    if current_user.rol in ['medico', 'recepcionista', 'cajero', 'cajera']:
        vacaciones = Vacacion.query.filter_by(usuario_id=current_user.id) \
            .order_by(Vacacion.fecha_solicitud.desc()).all()
    else:
        vacaciones = Vacacion.query.order_by(Vacacion.fecha_solicitud.desc()).all()
    
    return render_template('rrhh/listar_vacaciones.html', vacaciones=vacaciones)

@bp.route('/vacaciones/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_vacacion():
    """Solicitar vacaciones"""
    if current_user.rol not in ['medico', 'recepcionista', 'cajero', 'cajera']:
        flash('No tiene permisos para solicitar vacaciones', 'warning')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        fecha_inicio = datetime.strptime(request.form.get('fecha_inicio'), '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(request.form.get('fecha_fin'), '%Y-%m-%d').date()
        
        if fecha_fin < fecha_inicio:
            flash('La fecha de fin debe ser posterior a la fecha de inicio', 'danger')
            return redirect(url_for('rrhh.solicitar_vacacion'))
        
        vacacion = Vacacion(
            usuario_id=current_user.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo=request.form.get('tipo', 'anual'),
            motivo=request.form.get('motivo', '')
        )
        
        db.session.add(vacacion)
        db.session.commit()
        
        flash('Solicitud de vacaciones enviada', 'success')
        return redirect(url_for('rrhh.listar_vacaciones'))
    
    return render_template('rrhh/solicitar_vacacion.html')

@bp.route('/vacaciones/<int:id>/aprobar', methods=['POST'])
@login_required
def aprobar_vacacion(id):
    """Aprobar solicitud de vacaciones"""
    if current_user.rol not in ['admin']:
        flash('No tiene permisos para aprobar vacaciones', 'danger')
        return redirect(url_for('rrhh.listar_vacaciones'))
    
    vacacion = Vacacion.query.get_or_404(id)
    vacacion.estado = 'aprobada'
    vacacion.aprobado_por_id = current_user.id
    vacacion.fecha_aprobacion = datetime.utcnow()
    
    db.session.commit()
    
    flash('Vacación aprobada', 'success')
    return redirect(url_for('rrhh.listar_vacaciones'))

@bp.route('/vacaciones/<int:id>/rechazar', methods=['POST'])
@login_required
def rechazar_vacacion(id):
    """Rechazar solicitud de vacaciones"""
    if current_user.rol not in ['admin']:
        flash('No tiene permisos para rechazar vacaciones', 'danger')
        return redirect(url_for('rrhh.listar_vacaciones'))
    
    vacacion = Vacacion.query.get_or_404(id)
    vacacion.estado = 'rechazada'
    vacacion.aprobado_por_id = current_user.id
    vacacion.fecha_aprobacion = datetime.utcnow()
    vacacion.observaciones = request.form.get('motivo', '')
    
    db.session.commit()
    
    flash('Vacación rechazada', 'info')
    return redirect(url_for('rrhh.listar_vacaciones'))

@bp.route('/permisos')
@login_required
def listar_permisos():
    """Listar permisos"""
    if current_user.rol in ['medico', 'recepcionista', 'cajero', 'cajera']:
        permisos = Permiso.query.filter_by(usuario_id=current_user.id) \
            .order_by(Permiso.fecha_solicitud.desc()).all()
    else:
        permisos = Permiso.query.order_by(Permiso.fecha_solicitud.desc()).all()
    
    return render_template('rrhh/listar_permisos.html', permisos=permisos)

@bp.route('/permisos/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_permiso():
    """Solicitar permiso"""
    if current_user.rol not in ['medico', 'recepcionista', 'cajero', 'cajera']:
        flash('No tiene permisos para solicitar permisos', 'warning')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        fecha = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
        hora_inicio_str = request.form.get('hora_inicio')
        hora_fin_str = request.form.get('hora_fin')
        
        permiso = Permiso(
            usuario_id=current_user.id,
            fecha=fecha,
            hora_inicio=datetime.strptime(hora_inicio_str, '%H:%M').time() if hora_inicio_str else None,
            hora_fin=datetime.strptime(hora_fin_str, '%H:%M').time() if hora_fin_str else None,
            tipo=request.form.get('tipo'),
            motivo=request.form.get('motivo')
        )
        
        db.session.add(permiso)
        db.session.commit()
        
        flash('Solicitud de permiso enviada', 'success')
        return redirect(url_for('rrhh.listar_permisos'))
    
    return render_template('rrhh/solicitar_permiso.html')

@bp.route('/permisos/<int:id>/aprobar', methods=['POST'])
@login_required
def aprobar_permiso(id):
    """Aprobar permiso"""
    if current_user.rol not in ['admin']:
        flash('No tiene permisos para aprobar permisos', 'danger')
        return redirect(url_for('rrhh.listar_permisos'))
    
    permiso = Permiso.query.get_or_404(id)
    permiso.estado = 'aprobado'
    permiso.aprobado_por_id = current_user.id
    permiso.fecha_aprobacion = datetime.utcnow()
    
    db.session.commit()
    
    flash('Permiso aprobado', 'success')
    return redirect(url_for('rrhh.listar_permisos'))

@bp.route('/permisos/<int:id>/rechazar', methods=['POST'])
@login_required
def rechazar_permiso(id):
    """Rechazar permiso"""
    if current_user.rol not in ['admin']:
        flash('No tiene permisos para rechazar permisos', 'danger')
        return redirect(url_for('rrhh.listar_permisos'))
    
    permiso = Permiso.query.get_or_404(id)
    permiso.estado = 'rechazado'
    permiso.aprobado_por_id = current_user.id
    permiso.fecha_aprobacion = datetime.utcnow()
    
    # Guardar motivo de rechazo en observaciones
    motivo = request.form.get('motivo', '')
    if motivo:
        permiso.observaciones = f"Rechazado: {motivo}"
    
    db.session.commit()
    
    flash('Permiso rechazado', 'warning')
    return redirect(url_for('rrhh.listar_permisos'))

@bp.route('/asistencias')
@login_required
def listar_asistencias():
    """Listar asistencias"""
    fecha_filtro = request.args.get('fecha', date.today().isoformat())
    fecha = datetime.strptime(fecha_filtro, '%Y-%m-%d').date()
    
    if current_user.rol == 'admin':
        asistencias = Asistencia.query.filter_by(fecha=fecha).all()
        asistencia_hoy = None
    else:
        asistencias = Asistencia.query.filter_by(usuario_id=current_user.id, fecha=fecha).all()
        asistencia_hoy = Asistencia.query.filter_by(usuario_id=current_user.id, fecha=date.today()).first()
    
    return render_template('rrhh/listar_asistencias.html',
                         asistencias=asistencias,
                         fecha_filtro=fecha_filtro,
                         asistencia_hoy=asistencia_hoy)

@bp.route('/asistencias/marcar-entrada', methods=['POST'])
@login_required
def marcar_entrada():
    """Registrar hora de entrada para el usuario actual."""
    hoy = date.today()
    existente = Asistencia.query.filter_by(usuario_id=current_user.id, fecha=hoy).first()
    if existente and existente.hora_entrada:
        flash('La entrada ya fue registrada hoy.', 'info')
        return redirect(url_for('rrhh.listar_asistencias', fecha=hoy.isoformat()))
    
    ahora = datetime.now().time()
    if existente:
        existente.hora_entrada = ahora
    else:
        registro = Asistencia(usuario_id=current_user.id, fecha=hoy, hora_entrada=ahora, estado='presente')
        db.session.add(registro)
    db.session.commit()
    flash('Entrada registrada correctamente.', 'success')
    return redirect(url_for('rrhh.listar_asistencias', fecha=hoy.isoformat()))

@bp.route('/asistencias/marcar-salida', methods=['POST'])
@login_required
def marcar_salida():
    """Registrar hora de salida para el usuario actual."""
    hoy = date.today()
    registro = Asistencia.query.filter_by(usuario_id=current_user.id, fecha=hoy).first()
    if not registro or not registro.hora_entrada:
        flash('Debe registrar primero la entrada.', 'warning')
        return redirect(url_for('rrhh.listar_asistencias', fecha=hoy.isoformat()))
    if registro.hora_salida:
        flash('La salida ya fue registrada hoy.', 'info')
        return redirect(url_for('rrhh.listar_asistencias', fecha=hoy.isoformat()))
    registro.hora_salida = datetime.now().time()
    db.session.commit()
    flash('Salida registrada correctamente.', 'success')
    return redirect(url_for('rrhh.listar_asistencias', fecha=hoy.isoformat()))

@bp.route('/medicos')
@login_required
def listar_medicos():
    """Listar médicos"""
    medicos = Medico.query.filter_by(activo=True).all()
    return render_template('rrhh/listar_medicos.html', medicos=medicos)

@bp.route('/medicos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_medico():
    """Crear nuevo médico vinculado a usuario existente"""
    if request.method == 'POST':
        usuario_id = request.form.get('usuario_id')
        
        # Validar que el usuario existe y no tiene médico asignado
        if usuario_id:
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                flash('Usuario no encontrado', 'danger')
                return redirect(url_for('rrhh.nuevo_medico'))
            if usuario.rol != 'medico':
                flash('El usuario seleccionado no tiene rol de médico', 'warning')
                return redirect(url_for('rrhh.nuevo_medico'))
            if usuario.medico:
                flash('Este usuario ya tiene un perfil médico asignado', 'warning')
                return redirect(url_for('rrhh.nuevo_medico'))
        else:
            # Si no se selecciona usuario, crear uno nuevo (modo legacy)
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not username or not email or not password:
                flash('Completa los datos del usuario', 'warning')
                return redirect(url_for('rrhh.nuevo_medico'))
            
            usuario = Usuario(
                username=username,
                email=email,
                rol='medico',
                activo=True
            )
            usuario.set_password(password)
            db.session.add(usuario)
            db.session.flush()  # Para obtener el ID del usuario
        
        # Validar unicidad de cédula y registro
        cedula = request.form.get('cedula')
        registro_profesional = request.form.get('registro_profesional')
        
        if Medico.query.filter_by(cedula=cedula).first():
            db.session.rollback()
            flash('Ya existe un médico con esa cédula', 'danger')
            return redirect(url_for('rrhh.nuevo_medico'))
        if Medico.query.filter_by(registro_profesional=registro_profesional).first():
            db.session.rollback()
            flash('Ya existe un médico con ese registro profesional', 'danger')
            return redirect(url_for('rrhh.nuevo_medico'))
        
        # Crear el médico
        medico = Medico(
            usuario_id=usuario.id,
            nombre=request.form.get('nombre'),
            apellido=request.form.get('apellido'),
            cedula=cedula,
            registro_profesional=registro_profesional,
            telefono=request.form.get('telefono'),
            email=request.form.get('email_medico'),
            fecha_ingreso=datetime.strptime(request.form.get('fecha_ingreso'), '%Y-%m-%d').date(),
            activo=True
        )
        db.session.add(medico)
        db.session.flush()
        
        # Asignar especialidades
        especialidades_ids = request.form.getlist('especialidades')
        for esp_id in especialidades_ids:
            me = MedicoEspecialidad(
                medico_id=medico.id,
                especialidad_id=int(esp_id)
            )
            db.session.add(me)
        
        db.session.commit()
        flash('Médico registrado exitosamente', 'success')
        return redirect(url_for('rrhh.listar_medicos'))
    
    # GET - mostrar formulario
    especialidades = Especialidad.query.filter_by(activo=True).all()
    # Obtener usuarios con rol médico que NO tienen perfil médico asignado
    usuarios_sin_medico = Usuario.query.filter(
        Usuario.rol == 'medico',
        ~Usuario.id.in_(db.session.query(Medico.usuario_id))
    ).all()
    return render_template('rrhh/nuevo_medico.html', 
                         especialidades=especialidades,
                         usuarios_sin_medico=usuarios_sin_medico)

@bp.route('/medicos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_medico(id):
    """Editar médico existente"""
    medico = Medico.query.get_or_404(id)
    
    if request.method == 'POST':
        medico.nombre = request.form.get('nombre')
        medico.apellido = request.form.get('apellido')
        medico.cedula = request.form.get('cedula')
        medico.registro_profesional = request.form.get('registro_profesional')
        medico.telefono = request.form.get('telefono')
        medico.email = request.form.get('email_medico')
        medico.fecha_ingreso = datetime.strptime(request.form.get('fecha_ingreso'), '%Y-%m-%d').date()
        
        # Actualizar especialidades
        # Eliminar especialidades anteriores
        MedicoEspecialidad.query.filter_by(medico_id=medico.id).delete()
        
        # Agregar nuevas especialidades
        especialidades_ids = request.form.getlist('especialidades')
        for esp_id in especialidades_ids:
            me = MedicoEspecialidad(
                medico_id=medico.id,
                especialidad_id=int(esp_id)
            )
            db.session.add(me)
        
        db.session.commit()
        flash('Médico actualizado exitosamente', 'success')
        return redirect(url_for('rrhh.listar_medicos'))
    
    # GET - mostrar formulario
    especialidades = Especialidad.query.filter_by(activo=True).all()
    especialidades_medico = [me.especialidad_id for me in medico.especialidades]
    return render_template('rrhh/editar_medico.html', 
                         medico=medico,
                         especialidades=especialidades,
                         especialidades_medico=especialidades_medico)

# ===== HORARIOS DE ATENCIÓN =====

@bp.route('/horarios')
@login_required
def listar_horarios():
    """Listar horarios de atención por médico"""
    medico_id = request.args.get('medico_id', type=int)
    
    if medico_id:
        medico = Medico.query.get_or_404(medico_id)
        horarios = HorarioAtencion.query.filter_by(medico_id=medico_id)\
            .order_by(HorarioAtencion.dia_semana).all()
    else:
        medico = None
        horarios = []
    
    medicos = Medico.query.filter_by(activo=True).all()
    
    return render_template('rrhh/listar_horarios.html',
                         horarios=horarios,
                         medico=medico,
                         medicos=medicos)

@bp.route('/horarios/crear/<int:medico_id>', methods=['GET', 'POST'])
@login_required
def crear_horario(medico_id):
    """Crear horario de atención para un médico"""
    medico = Medico.query.get_or_404(medico_id)
    
    if request.method == 'POST':
        # Convertir día de la semana a número
        dia_semana = int(request.form.get('dia_semana'))
        
        hora_inicio = datetime.strptime(request.form.get('hora_inicio'), '%H:%M').time()
        hora_fin = datetime.strptime(request.form.get('hora_fin'), '%H:%M').time()
        
        if hora_fin <= hora_inicio:
            flash('La hora de fin debe ser posterior a la hora de inicio', 'danger')
            return redirect(url_for('rrhh.crear_horario', medico_id=medico_id))
        
        horario = HorarioAtencion(
            medico_id=medico_id,
            dia_semana=dia_semana,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            activo=True
        )
        
        db.session.add(horario)
        db.session.commit()
        
        dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        flash(f'Horario para {dias_nombres[dia_semana]} creado exitosamente', 'success')
        return redirect(url_for('rrhh.listar_horarios', medico_id=medico_id))
    
    dias_semana = [
        {'valor': 0, 'nombre': 'Lunes'},
        {'valor': 1, 'nombre': 'Martes'},
        {'valor': 2, 'nombre': 'Miércoles'},
        {'valor': 3, 'nombre': 'Jueves'},
        {'valor': 4, 'nombre': 'Viernes'},
        {'valor': 5, 'nombre': 'Sábado'},
        {'valor': 6, 'nombre': 'Domingo'}
    ]
    return render_template('rrhh/crear_horario.html', medico=medico, dias_semana=dias_semana)

@bp.route('/horarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_horario(id):
    """Editar horario de atención"""
    horario = HorarioAtencion.query.get_or_404(id)
    
    if request.method == 'POST':
        hora_inicio = datetime.strptime(request.form.get('hora_inicio'), '%H:%M').time()
        hora_fin = datetime.strptime(request.form.get('hora_fin'), '%H:%M').time()
        
        if hora_fin <= hora_inicio:
            flash('La hora de fin debe ser posterior a la hora de inicio', 'danger')
            return redirect(url_for('rrhh.editar_horario', id=id))
        
        horario.hora_inicio = hora_inicio
        horario.hora_fin = hora_fin
        horario.activo = request.form.get('activo') == 'true'
        
        db.session.commit()
        
        flash('Horario actualizado exitosamente', 'success')
        return redirect(url_for('rrhh.listar_horarios', medico_id=horario.medico_id))
    
    return render_template('rrhh/editar_horario.html', horario=horario)

@bp.route('/horarios/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_horario(id):
    """Eliminar horario de atención"""
    horario = HorarioAtencion.query.get_or_404(id)
    medico_id = horario.medico_id
    
    db.session.delete(horario)
    db.session.commit()
    
    flash('Horario eliminado exitosamente', 'success')
    return redirect(url_for('rrhh.listar_horarios', medico_id=medico_id))
