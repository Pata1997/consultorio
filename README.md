# Sistema de Consultorio Médico

Sistema completo de gestión para consultorios médicos desarrollado con Flask, PostgreSQL y ReportLab.

## Características

### Módulo de Agendamiento
- Registro de agenda médica por especialidad
- Gestión de citas (reservación, confirmación, cancelación)
- Registro de pacientes
- Avisos y recordatorios
- Búsqueda por especialidad y médico disponible

### Módulo de Consultorio
- Gestión de consultas médicas
- Registro de diagnósticos y tratamientos
- Control de procedimientos e insumos
- Generación de órdenes de estudios y análisis
- Registro de recetas e indicaciones
- Historial médico completo del paciente
- Control de stock de insumos
- Generación de fichas médicas y justificativos (PDF)

### Módulo de Facturación y Caja
- Apertura y cierre de caja
- Generación automática de ventas desde consultas
- Múltiples formas de pago (efectivo, tarjeta, cheque, transferencia)
- Gestión de cobranzas
- Arqueo de caja
- Notas de crédito y débito
- Reportes de ventas

### Módulo de RRHH
- Gestión de personal médico
- Control de vacaciones (solicitud, aprobación)
- Gestión de permisos
- Registro de asistencias
- Horarios de atención por médico

### Módulo de Configuración (Nuevo)
- Datos del consultorio (nombre, dirección, teléfono, email)
- Logo personalizado
- Datos de facturación (RUC, timbrado, punto de expedición)
- Configuración de membrete para reportes
- El logo aparece en login y todos los PDFs

## Tecnologías

- **Backend**: Flask 3.0
- **Base de Datos**: PostgreSQL
- **ORM**: SQLAlchemy
- **Autenticación**: Flask-Login
- **Formularios**: Flask-WTF
- **Migraciones**: Flask-Migrate (Alembic)
- **Reportes PDF**: ReportLab
- **Frontend**: Bootstrap 5, JavaScript

## Requisitos

- Python 3.8 o superior
- PostgreSQL 12 o superior

## Instalación

### 1. Clonar el repositorio

```bash
cd Consultorio
```

### 2. Crear entorno virtual

```bash
python -m venv venv
```

### 3. Activar entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar base de datos

1. Crear base de datos en PostgreSQL:
```sql
CREATE DATABASE consultorio_db;
```

2. Copiar archivo de configuración:
```bash
copy .env.example .env
```

3. Editar `.env` con tus credenciales de PostgreSQL:
```
DATABASE_URL=postgresql://tu_usuario:tu_password@localhost:5432/consultorio_db
SECRET_KEY=tu_clave_secreta_aqui
```

### 6. Inicializar base de datos

```bash
python init_db.py
```

Esto creará todas las tablas y datos de ejemplo.

### 7. Ejecutar la aplicación

```bash
python run.py
```

La aplicación estará disponible en: http://localhost:5000

## Credenciales por Defecto

### Administrador
- Usuario: `admin`
- Contraseña: `admin123`

### Recepcionista
- Usuario: `recepcion`
- Contraseña: `recepcion123`

### Médicos
- Usuario: `jlopez` (Dr. López - Odontología)
- Usuario: `amartinez` (Dra. Martínez - Medicina General)
- Usuario: `crodriguez` (Dr. Rodríguez - Pediatría)
- Contraseña para todos: `medico123`

## Estructura del Proyecto

```
Consultorio/
├── app/
│   ├── models/              # Modelos de base de datos
│   │   ├── usuario.py       # Usuarios, médicos, pacientes
│   │   ├── consultorio.py   # Citas, consultas, insumos
│   │   ├── facturacion.py   # Ventas, caja, pagos
│   │   └── rrhh.py          # Vacaciones, permisos
│   ├── routes/              # Rutas y controladores
│   │   ├── auth.py          # Autenticación
│   │   ├── main.py          # Dashboard
│   │   ├── agendamiento.py  # Gestión de citas
│   │   ├── consultorio.py   # Consultas médicas
│   │   ├── facturacion.py   # Ventas y caja
│   │   └── rrhh.py          # Recursos humanos
│   ├── templates/           # Plantillas HTML
│   ├── static/              # Archivos estáticos (CSS, JS)
│   ├── utils/               # Utilidades
│   │   └── pdf_generator.py # Generación de PDFs
│   └── __init__.py          # Inicialización de Flask
├── config.py                # Configuración
├── run.py                   # Punto de entrada
├── init_db.py              # Script de inicialización
└── requirements.txt         # Dependencias

```

## Roles y Permisos

### Administrador
- Acceso completo al sistema
- Gestión de usuarios y personal
- Aprobación de vacaciones y permisos
- Visualización de todos los reportes
- **Configuración del consultorio (logo, datos, facturación)**

### Recepcionista
- Gestión de citas y pacientes
- Confirmación de citas
- Facturación y cobros
- Apertura/cierre de caja

### Médico
- Visualización de sus citas
- Registro de consultas
- Generación de recetas y órdenes
- Solicitud de vacaciones y permisos
- Acceso al historial de sus pacientes

## Flujo de Trabajo

### 1. Agendar Cita
1. Recepcionista registra o busca paciente
2. Selecciona especialidad requerida
3. Sistema muestra médicos disponibles de esa especialidad
4. Selecciona fecha y horario disponible
5. Confirma la cita

### 2. Atención Médica
1. Médico visualiza citas confirmadas del día
2. Selecciona paciente y accede a su historial
3. Registra consulta con diagnóstico
4. Agrega recetas (medicamentos externos)
5. Selecciona insumos utilizados (se descuenta stock)
6. Selecciona procedimientos realizados
7. Finaliza consulta

### 3. Facturación
1. Sistema genera automáticamente venta desde la consulta
2. Incluye: consulta + procedimientos + insumos
3. Recepcionista procesa el pago
4. Imprime factura
5. Entrega receta al paciente

### 4. Cierre de Caja
1. Recepcionista cierra caja al final del día
2. Sistema genera arqueo automático
3. Muestra diferencias si existen
4. Genera reporte de recaudación

## Generación de Reportes PDF
 PDFs con **membrete personalizado** incluyendo logo:
- **Recetas médicas**: Con membrete del consultorio y datos del médico
- **Fichas médicas**: Historial completo de consulta con logo
- **Facturas**: Con logo, timbrado y datos fiscales del consultorio
- **Arqueo de caja**: Resumen de recaudación con membrete
- **Órdenes de estudios**: Para laboratorios externos

Todos los documentos incluyen el logo y datos configurados del consultorio.
- **Órdenes de estudios**: Para laboratorios externos

## Migraciones de Base de Datos

Para realizar cambios en el esquema de la base de datos:

```bash
# Crear migración
flask db migrate -m "Descripción del cambio"

# Aplicar migración
flask db upgrade
```
Configurar el Consultorio
1. Iniciar sesión como admin
2. Ir a **Configuración** en el menú
3. Editar datos del consultorio
4. Subir logo (PNG, JPG, GIF)
5. Configurar timbrado y punto de expedición
6. El logo aparecerá automáticamente en login y PDFs

### 
## Desarrollo

### Agregar nueva especialidad
1. Acceder como administrador
2. Ir a configuración (próximamente)
3. O agregar directamente en la base de datos

### Agregar nuevo médico
1. Crear usuario con rol "medico"
2. Crear registro en tabla médicos
3. Asignar especialidades
4. Configurar horarios de atención

## Soporte

Para reportar problemas o sugerencias, contactar al administrador del sistema.

## Licencia

Sistema propietario - Todos los derechos reservados

---

**Desarrollado con ❤️ para mejorar la atención médica**
