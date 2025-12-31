from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.usuario import Usuario, Medico, Especialidad, MedicoEspecialidad
from datetime import datetime

bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')


def require_admin():
    if current_user.rol != 'admin':
        flash('Acceso restringido a administradores', 'danger')
        return False
    return True


@bp.route('/')
@login_required
def listar_usuarios():
    if not require_admin():
        return redirect(url_for('main.index'))

    rol = request.args.get('rol')
    estado = request.args.get('estado')  # activo|inactivo|todos

    query = Usuario.query
    if rol and rol != 'todos':
        query = query.filter_by(rol=rol)
    if estado == 'activo':
        query = query.filter_by(activo=True)
    elif estado == 'inactivo':
        query = query.filter_by(activo=False)

    usuarios = query.order_by(Usuario.username).all()
    return render_template('usuarios/listar_usuarios.html', usuarios=usuarios, rol=rol or 'todos', estado=estado or 'todos')


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    if not require_admin():
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        rol = request.form.get('rol')
        password = request.form.get('password')

        if not username or not email or not password or not rol:
            flash('Completa todos los campos obligatorios', 'warning')
            return redirect(url_for('usuarios.nuevo_usuario'))

        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('usuarios.nuevo_usuario'))
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está en uso', 'danger')
            return redirect(url_for('usuarios.nuevo_usuario'))

        # Crear usuario
        u = Usuario(username=username, email=email, rol=rol, activo=True)
        u.set_password(password)
        db.session.add(u)
        db.session.flush()  # Obtener u.id antes de commit

        # Si es médico, crear registro en tabla medicos
        if rol == 'medico':
            nombre = request.form.get('nombre', '').strip()
            apellido = request.form.get('apellido', '').strip()
            cedula = request.form.get('cedula', '').strip()
            registro_profesional = request.form.get('registro_profesional', '').strip()
            fecha_ingreso_str = request.form.get('fecha_ingreso', '')

            # Validar campos obligatorios de médico
            if not nombre or not apellido or not cedula or not registro_profesional or not fecha_ingreso_str:
                db.session.rollback()
                flash('Para crear un usuario médico, completa todos los datos profesionales', 'warning')
                return redirect(url_for('usuarios.nuevo_usuario'))

            # Validar unicidad de cédula y registro profesional
            if Medico.query.filter_by(cedula=cedula).first():
                db.session.rollback()
                flash('Ya existe un médico con esa cédula', 'danger')
                return redirect(url_for('usuarios.nuevo_usuario'))
            if Medico.query.filter_by(registro_profesional=registro_profesional).first():
                db.session.rollback()
                flash('Ya existe un médico con ese registro profesional', 'danger')
                return redirect(url_for('usuarios.nuevo_usuario'))

            medico = Medico(
                usuario_id=u.id,
                nombre=nombre,
                apellido=apellido,
                cedula=cedula,
                registro_profesional=registro_profesional,
                telefono=request.form.get('telefono', ''),
                email=request.form.get('email_medico', email),  # Usar email del usuario si no se provee
                fecha_ingreso=datetime.strptime(fecha_ingreso_str, '%Y-%m-%d').date(),
                activo=True
            )
            db.session.add(medico)
            db.session.flush()  # Obtener medico.id

            # Asignar especialidades
            especialidades_ids = request.form.getlist('especialidades')
            for esp_id in especialidades_ids:
                me = MedicoEspecialidad(
                    medico_id=medico.id,
                    especialidad_id=int(esp_id)
                )
                db.session.add(me)

        db.session.commit()
        if rol == 'medico':
            flash('Usuario y perfil médico creados correctamente', 'success')
        else:
            flash('Usuario creado correctamente', 'success')
        return redirect(url_for('usuarios.listar_usuarios'))

    # GET - pasar especialidades para el formulario
    especialidades = Especialidad.query.filter_by(activo=True).all()
    return render_template('usuarios/nuevo_usuario.html', especialidades=especialidades)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if not require_admin():
        return redirect(url_for('main.index'))

    u = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        rol = request.form.get('rol')
        password = request.form.get('password')  # opcional

        # Validar unicidad (excluyendo el propio usuario)
        existe_username = Usuario.query.filter(Usuario.username == username, Usuario.id != u.id).first()
        if existe_username:
            flash('El nombre de usuario ya está en uso', 'danger')
            return redirect(url_for('usuarios.editar_usuario', id=u.id))
        existe_email = Usuario.query.filter(Usuario.email == email, Usuario.id != u.id).first()
        if existe_email:
            flash('El email ya está en uso', 'danger')
            return redirect(url_for('usuarios.editar_usuario', id=u.id))

        u.username = username
        u.email = email
        u.rol = rol
        if password:
            u.set_password(password)
        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('usuarios.listar_usuarios'))

    return render_template('usuarios/editar_usuario.html', u=u)


@bp.route('/<int:id>/toggle-activo', methods=['POST'])
@login_required
def toggle_activo(id):
    if not require_admin():
        return redirect(url_for('main.index'))

    u = Usuario.query.get_or_404(id)
    u.activo = not u.activo
    db.session.commit()
    estado = 'habilitado' if u.activo else 'inhabilitado'
    flash(f'Usuario {estado} correctamente', 'info')
    return redirect(url_for('usuarios.listar_usuarios'))
