# -*- coding: utf-8 -*-
"""
Script para identificar y solucionar el problema de encoding con psycopg2
"""
import os
import sys

print("=== Diagnóstico del problema de encoding ===\n")

# 1. Verificar variables de entorno de PostgreSQL
print("1. Variables de entorno de PostgreSQL:")
pg_vars = ['PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE', 
           'PGSYSCONFDIR', 'PGSERVICEFILE', 'PGPASSFILE', 'PGHOSTADDR',
           'PGCLIENTENCODING']

found_vars = False
for var in pg_vars:
    value = os.environ.get(var)
    if value:
        print(f"  {var} = {value}")
        found_vars = True

if not found_vars:
    print("  (Ninguna variable de PostgreSQL configurada)")

# 2. Buscar archivos de configuración de PostgreSQL
print("\n2. Archivos de configuración de PostgreSQL:")
possible_locations = [
    os.path.expanduser('~/.pgpass'),
    os.path.expanduser('~/.pg_service.conf'),
    'C:\\Program Files\\PostgreSQL',
    'C:\\PostgreSQL',
    os.path.join(os.environ.get('APPDATA', ''), 'postgresql'),
]

for location in possible_locations:
    if os.path.exists(location):
        print(f"  ✓ Encontrado: {location}")
        if os.path.isfile(location):
            try:
                with open(location, 'rb') as f:
                    content = f.read(200)
                    print(f"    Primeros bytes: {content[:100]}")
            except:
                pass

# 3. Aplicar solución
print("\n3. Aplicando solución...")
print("  - Configurando variables de entorno para evitar archivos de config")

# Limpiar todas las variables de PostgreSQL que puedan causar problemas
for var in pg_vars:
    if var in os.environ:
        del os.environ[var]
        print(f"  ✓ Limpiada variable {var}")

# Configurar solo lo necesario
os.environ['PGCLIENTENCODING'] = 'UTF8'
os.environ['PYTHONUTF8'] = '1'

# Evitar que psycopg2 busque archivos de configuración
os.environ['PGSYSCONFDIR'] = ''  # Vacío para evitar búsqueda
os.environ['PGSERVICEFILE'] = ''  # Vacío para evitar búsqueda

print("\n4. Probando conexión con psycopg2...")
try:
    import psycopg2
    
    # Conectar sin usar archivos de configuración
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgresql',
        password='123456',
        database='consultorio_db'
    )
    
    print("✅ ¡CONEXIÓN EXITOSA!")
    
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"\nVersión de PostgreSQL:")
    print(version[0])
    
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print("SOLUCIÓN ENCONTRADA:")
    print("="*60)
    print("Agregar estas líneas AL INICIO de init_db.py y app/__init__.py:")
    print()
    print("import os")
    print("os.environ['PGSYSCONFDIR'] = ''")
    print("os.environ['PGSERVICEFILE'] = ''")
    print("os.environ['PGCLIENTENCODING'] = 'UTF8'")
    print("="*60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
