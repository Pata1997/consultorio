# -*- coding: latin-1 -*-
"""
Monkey patch para psycopg2 que soluciona problemas de encoding en Windows
"""
import sys
import os

def patch_psycopg2():
    """
    Aplica un patch a psycopg2 para manejar archivos con encoding CP1252
    """
    # Forzar que Python use CP1252 para leer archivos del sistema
    import codecs
    
    # Registrar un handler de errores personalizado
    def ignore_errors(exception):
        return ('', exception.end)
    
    codecs.register_error('psycopg2_ignore', ignore_errors)
    
    # Configurar variables de entorno críticas
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PGCLIENTENCODING'] = 'UTF8'
    os.environ['PGSYSCONFDIR'] = ''
    os.environ['PGSERVICEFILE'] = ''
    
    # Patch al método de conexión de psycopg2
    import psycopg2
    import psycopg2.extensions
    
    _original_connect = psycopg2.connect
    
    def patched_connect(*args, **kwargs):
        # Asegurar que usamos UTF8
        if 'client_encoding' not in kwargs:
            kwargs['client_encoding'] = 'UTF8'
        
        # Intentar múltiples estrategias
        try:
            return _original_connect(*args, **kwargs)
        except UnicodeDecodeError as e:
            # Si falla, intentar con locale C
            import locale
            old_locale = locale.getlocale()
            try:
                locale.setlocale(locale.LC_ALL, 'C')
                return _original_connect(*args, **kwargs)
            finally:
                try:
                    locale.setlocale(locale.LC_ALL, old_locale)
                except:
                    pass
    
    psycopg2.connect = patched_connect
    
    print("✓ Patch de psycopg2 aplicado")

if __name__ == '__main__':
    patch_psycopg2()
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgresql',
            password='123456',
            database='consultorio_db'
        )
        print("✅ Conexión exitosa con patch aplicado")
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
