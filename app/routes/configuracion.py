from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import ConfiguracionConsultorio, Especialidad
from werkzeug.utils import secure_filename
import os
from datetime import datetime

bp = Blueprint('configuracion', __name__, url_prefix='/configuracion')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
@login_required
def ver_configuracion():
    """Ver configuración actual"""
    if current_user.rol not in ['admin']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('main.index'))
    
    config = ConfiguracionConsultorio.get_configuracion()
    return render_template('configuracion/ver_configuracion.html', config=config)

@bp.route('/editar', methods=['GET', 'POST'])
@login_required
def editar_configuracion():
    """Editar configuración del consultorio"""
    if current_user.rol not in ['admin']:
        flash('No tiene permisos para editar la configuración', 'danger')
        return redirect(url_for('main.index'))
    
    config = ConfiguracionConsultorio.get_configuracion()
    
    if request.method == 'POST':
        # Datos generales
        config.nombre = request.form.get('nombre')
        config.razon_social = request.form.get('razon_social')
        config.ruc = request.form.get('ruc')
        config.direccion = request.form.get('direccion')
        config.telefono = request.form.get('telefono')
        config.email = request.form.get('email')
        config.sitio_web = request.form.get('sitio_web')
        config.slogan = request.form.get('slogan')
        config.horario_atencion = request.form.get('horario_atencion')
        
        # Datos de facturación
        config.punto_expedicion = request.form.get('punto_expedicion')
        config.timbrado = request.form.get('timbrado')
        
        fecha_inicio = request.form.get('fecha_inicio_timbrado')
        if fecha_inicio:
            config.fecha_inicio_timbrado = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        
        fecha_fin = request.form.get('fecha_fin_timbrado')
        if fecha_fin:
            config.fecha_fin_timbrado = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        # Logo
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Agregar timestamp para evitar sobrescritura
                name, ext = os.path.splitext(filename)
                filename = f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                
                upload_folder = os.path.join('app', 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                
                config.logo_filename = filename
                config.logo_path = f"uploads/{filename}"
        
        config.actualizado_por_id = current_user.id
        
        db.session.commit()
        
        flash('Configuración actualizada exitosamente', 'success')
        return redirect(url_for('configuracion.ver_configuracion'))
    
    return render_template('configuracion/editar_configuracion.html', config=config)

@bp.route('/especialidades')
@login_required
def listar_especialidades():
    """Listar especialidades para gestionar precios"""
    if current_user.rol not in ['admin']:
        flash('No tienes permisos para acceder a esta sección', 'danger')
        return redirect(url_for('main.index'))
    
    especialidades = Especialidad.query.all()
    return render_template('configuracion/listar_especialidades.html', especialidades=especialidades)

@bp.route('/especialidades/crear', methods=['GET', 'POST'])
@login_required
def crear_especialidad():
    """Crear nueva especialidad"""
    if current_user.rol not in ['admin']:
        flash('No tienes permisos para acceder a esta sección', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            from app.utils.number_utils import parse_decimal_from_form
            
            # Crear nueva especialidad
            nueva_especialidad = Especialidad(
                nombre=request.form.get('nombre'),
                descripcion=request.form.get('descripcion'),
                precio_consulta=parse_decimal_from_form(request.form.get('precio_consulta')),
                activo=request.form.get('activo') == 'on'
            )
            
            db.session.add(nueva_especialidad)
            db.session.commit()
            flash('Especialidad creada exitosamente', 'success')
            return redirect(url_for('configuracion.listar_especialidades'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear especialidad: {str(e)}', 'danger')
    
    return render_template('configuracion/crear_especialidad.html')

@bp.route('/especialidades/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_especialidad(id):
    """Editar precio de especialidad"""
    if current_user.rol not in ['admin']:
        flash('No tienes permisos para acceder a esta sección', 'danger')
        return redirect(url_for('main.index'))
    
    especialidad = Especialidad.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            from app.utils.number_utils import parse_decimal_from_form
            
            # Actualizar datos
            especialidad.nombre = request.form.get('nombre')
            especialidad.descripcion = request.form.get('descripcion')
            especialidad.precio_consulta = parse_decimal_from_form(request.form.get('precio_consulta'))
            especialidad.activo = request.form.get('activo') == 'on'
            
            db.session.commit()
            flash('Especialidad actualizada exitosamente', 'success')
            return redirect(url_for('configuracion.listar_especialidades'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar especialidad: {str(e)}', 'danger')
    
    return render_template('configuracion/editar_especialidad.html', especialidad=especialidad)
