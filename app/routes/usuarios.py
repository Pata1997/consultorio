from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.usuario import Usuario

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

        u = Usuario(username=username, email=email, rol=rol, activo=True)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('usuarios.listar_usuarios'))

    return render_template('usuarios/nuevo_usuario.html')


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
