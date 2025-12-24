from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user

def require_roles(*roles):
    """Decorador para requerir roles específicos"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if current_user.rol not in roles:
                flash('No tienes permisos para acceder a esta sección', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorador para requerir rol de administrador"""
    return require_roles('admin')(f)

def medico_required(f):
    """Decorador para requerir rol de médico"""
    return require_roles('medico')(f)

def recepcionista_required(f):
    """Decorador para requerir rol de recepcionista"""
    return require_roles('recepcionista')(f)
