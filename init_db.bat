@echo off
REM Script para inicializar la base de datos con encoding correcto

REM Configurar variables de entorno ANTES de ejecutar Python
set PYTHONUTF8=1
set PGCLIENTENCODING=UTF8

REM Ejecutar el script de inicialización
python init_db.py

pause
