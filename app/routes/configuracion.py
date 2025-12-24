from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import ConfiguracionConsultorio
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
