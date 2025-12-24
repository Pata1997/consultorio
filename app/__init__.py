import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_name='default'):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configuración de login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
    
    # Crear directorios necesarios
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)
    
    # Registrar blueprints
    from app.routes import auth, main, agendamiento, consultorio, facturacion, rrhh, configuracion
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(agendamiento.bp)
    app.register_blueprint(consultorio.bp)
    app.register_blueprint(facturacion.bp)
    app.register_blueprint(rrhh.bp)
    app.register_blueprint(configuracion.bp)
    
    # Context processor para menú dinámico
    @app.context_processor
    def inject_menu():
        from app.utils import get_menu_items
        from flask_login import current_user
        if current_user.is_authenticated:
            return {'menu_items': get_menu_items()}
        return {'menu_items': []}
    
    # Error handler para 403
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('errors/403.html'), 403

    # Filtro Jinja para formatear monedas/números con separador de miles
    try:
        from app.utils.number_utils import format_currency
        app.jinja_env.filters['format_currency'] = format_currency
    except Exception:
        # No bloquear la creación de la app si el filtro falla
        pass
    
    return app

from app import models
