import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-cambiar-en-produccion'
    
    # URL de base de datos - IMPORTANTE: usar postgresql+pg8000://
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql+pg8000://postgres:123456@localhost:5432/consultorio_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Opciones de SQLAlchemy igual al proyecto funcional
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,      # Recicla conexiones cada 5 minutos
        'pool_pre_ping': True,    # Verifica conexiones antes de usarlas
    }
    
    # Configuración de sesión
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuración de uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # Configuración de reportes
    REPORTS_FOLDER = os.path.join(basedir, 'reports')

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
