"""
Script para resetear la base de datos del Consultorio Odontológico "Norma Benítez"

PRESERVA:
- alembic_version (migraciones)
- configuracion_consultorio (datos de la empresa)
- formas_pago (efectivo, tarjetas, etc.)

LIMPIA Y RECREA:
- Usuarios, médicos, especialidades, procedimientos, insumos
- Pacientes, citas, consultas, ventas, cajas
- Horarios de atención

ESTRUCTURA NUEVA:
- 4 Especialidades odontológicas
- 4 Médicos (uno por especialidad)
- ~30 Procedimientos con precios IVA incluido
- ~20 Insumos con stock inicial
- 5 Pacientes variados
- Precios personalizados por médico
"""

from app import create_app, db
from app.models import (
    Usuario, Medico, MedicoEspecialidad, Especialidad, HorarioAtencion,
    Procedimiento, ProcedimientoPrecio, Insumo, InsumoEspecialidad,
    Paciente, Cita, Consulta, ConsultaProcedimiento, ConsultaInsumo,
    Receta, OrdenEstudio, MovimientoInsumo,
    Caja, Venta, VentaDetalle, Pago,
    Vacacion, Permiso, Asistencia
)
from datetime import date, time
from decimal import Decimal
from sqlalchemy import text

def limpiar_base_datos():
    """Eliminar todos los datos excepto configuración y formas de pago"""
    print("=" * 80)
    print("LIMPIANDO BASE DE DATOS")
    print("=" * 80)
    print()
    
    # Primero, anular la referencia en configuracion_consultorio para poder limpiar usuarios
    print("→ Anulando referencia de actualizado_por en configuracion_consultorio...")
    db.session.execute(text("UPDATE configuracion_consultorio SET actualizado_por_id = NULL"))
    db.session.commit()
    print("✓ Referencia anulada")
    print()
    
    # Orden de eliminación respetando foreign keys
    tablas = [
        (Pago, "Pagos"),
        (VentaDetalle, "Detalles de ventas"),
        (Venta, "Ventas"),
        (Caja, "Cajas"),
        (Asistencia, "Asistencias"),
        (Permiso, "Permisos"),
        (Vacacion, "Vacaciones"),
        (OrdenEstudio, "Órdenes de estudio"),
        (Receta, "Recetas"),
        (ConsultaInsumo, "Insumos usados en consultas"),
        (ConsultaProcedimiento, "Procedimientos en consultas"),
        (Consulta, "Consultas"),
        (Cita, "Citas"),
        (MovimientoInsumo, "Movimientos de insumos"),
        (InsumoEspecialidad, "Relación insumos-especialidades"),
        (Insumo, "Insumos"),
        (ProcedimientoPrecio, "Precios personalizados de procedimientos"),
        (Procedimiento, "Procedimientos"),
        (HorarioAtencion, "Horarios de atención"),
        (MedicoEspecialidad, "Relación médicos-especialidades"),
        (Medico, "Médicos"),
        (Paciente, "Pacientes"),
        (Especialidad, "Especialidades"),
        (Usuario, "Usuarios"),
    ]
    
    for modelo, nombre in tablas:
        count = db.session.query(modelo).count()
        db.session.query(modelo).delete()
        print(f"✓ {nombre}: {count} registros eliminados")
    
    db.session.commit()
    print()
    print("✓ Base de datos limpiada exitosamente")
    print()

def crear_usuarios_y_medicos():
    """Crear usuarios del sistema y médicos"""
    print("=" * 80)
    print("CREANDO USUARIOS Y MÉDICOS")
    print("=" * 80)
    print()
    
    usuarios_data = [
        {
            'username': 'norma.benitez',
            'email': 'norma@consultoriobenitez.com',
            'rol': 'admin',
            'password': '123456',
            'nombre': 'Norma',
            'apellido': 'Benítez',
            'es_medico': False
        },
        {
            'username': 'recepcion',
            'email': 'recepcion@consultoriobenitez.com',
            'rol': 'recepcionista',
            'password': '123456',
            'nombre': 'María',
            'apellido': 'González',
            'es_medico': False
        },
        {
            'username': 'caja',
            'email': 'caja@consultoriobenitez.com',
            'rol': 'cajera',
            'password': '123456',
            'nombre': 'Sandra',
            'apellido': 'Ramírez',
            'es_medico': False
        },
        {
            'username': 'dr.perez',
            'email': 'perez@consultoriobenitez.com',
            'rol': 'medico',
            'password': '123456',
            'nombre': 'Carlos',
            'apellido': 'Pérez',
            'es_medico': True,
            'cedula': '1234567',
            'registro_profesional': 'REG-OG-001',
            'especialidad': 'Odontología General'
        },
        {
            'username': 'dra.silva',
            'email': 'silva@consultoriobenitez.com',
            'rol': 'medico',
            'password': '123456',
            'nombre': 'Ana',
            'apellido': 'Silva',
            'es_medico': True,
            'cedula': '2345678',
            'registro_profesional': 'REG-ORT-002',
            'especialidad': 'Ortodoncia'
        },
        {
            'username': 'dr.caceres',
            'email': 'caceres@consultoriobenitez.com',
            'rol': 'medico',
            'password': '123456',
            'nombre': 'Roberto',
            'apellido': 'Cáceres',
            'es_medico': True,
            'cedula': '3456789',
            'registro_profesional': 'REG-END-003',
            'especialidad': 'Endodoncia'
        },
        {
            'username': 'dra.torres',
            'email': 'torres@consultoriobenitez.com',
            'rol': 'medico',
            'password': '123456',
            'nombre': 'Patricia',
            'apellido': 'Torres',
            'es_medico': True,
            'cedula': '4567890',
            'registro_profesional': 'REG-PED-004',
            'especialidad': 'Odontopediatría'
        },
    ]
    
    medicos_creados = {}
    
    for data in usuarios_data:
        usuario = Usuario(
            username=data['username'],
            email=data['email'],
            rol=data['rol'],
            activo=True
        )
        usuario.set_password(data['password'])
        db.session.add(usuario)
        db.session.flush()
        
        print(f"✓ Usuario creado: {data['username']} (rol: {data['rol']})")
        
        if data['es_medico']:
            medico = Medico(
                usuario_id=usuario.id,
                nombre=data['nombre'],
                apellido=data['apellido'],
                cedula=data['cedula'],
                registro_profesional=data['registro_profesional'],
                telefono='0981-123456',
                email=data['email'],
                fecha_ingreso=date(2024, 1, 1),
                activo=True
            )
            db.session.add(medico)
            db.session.flush()
            
            medicos_creados[data['especialidad']] = medico
            print(f"  → Médico: Dr(a). {data['apellido']} - {data['especialidad']}")
    
    db.session.commit()
    print()
    print(f"✓ {len(usuarios_data)} usuarios creados")
    print(f"✓ {len(medicos_creados)} médicos creados")
    print()
    
    return medicos_creados

def crear_especialidades():
    """Crear especialidades odontológicas con precios"""
    print("=" * 80)
    print("CREANDO ESPECIALIDADES")
    print("=" * 80)
    print()
    
    especialidades_data = [
        {
            'nombre': 'Odontología General',
            'descripcion': 'Tratamientos dentales generales, limpiezas, obturaciones, extracciones',
            'precio_consulta': Decimal('150000.00')
        },
        {
            'nombre': 'Ortodoncia',
            'descripcion': 'Corrección de malposiciones dentarias, brackets, alineadores',
            'precio_consulta': Decimal('200000.00')
        },
        {
            'nombre': 'Endodoncia',
            'descripcion': 'Tratamientos de conducto, endodoncias, apicectomías',
            'precio_consulta': Decimal('180000.00')
        },
        {
            'nombre': 'Odontopediatría',
            'descripcion': 'Odontología especializada en niños y adolescentes',
            'precio_consulta': Decimal('160000.00')
        },
    ]
    
    especialidades_creadas = {}
    
    for data in especialidades_data:
        esp = Especialidad(**data)
        db.session.add(esp)
        db.session.flush()
        especialidades_creadas[data['nombre']] = esp
        print(f"✓ {data['nombre']}: {data['precio_consulta']:,.0f} Gs (IVA incluido)")
    
    db.session.commit()
    print()
    print(f"✓ {len(especialidades_data)} especialidades creadas")
    print()
    
    return especialidades_creadas

def asignar_especialidades_a_medicos(medicos, especialidades):
    """Asignar cada médico a su especialidad"""
    print("=" * 80)
    print("ASIGNANDO ESPECIALIDADES A MÉDICOS")
    print("=" * 80)
    print()
    
    for esp_nombre, medico in medicos.items():
        especialidad = especialidades[esp_nombre]
        
        me = MedicoEspecialidad(
            medico_id=medico.id,
            especialidad_id=especialidad.id
        )
        db.session.add(me)
        print(f"✓ Dr(a). {medico.apellido} → {esp_nombre}")
    
    db.session.commit()
    print()

def crear_procedimientos(especialidades):
    """Crear procedimientos odontológicos por especialidad"""
    print("=" * 80)
    print("CREANDO PROCEDIMIENTOS")
    print("=" * 80)
    print()
    
    procedimientos_data = [
        # Odontología General
        ('Odontología General', 'Limpieza dental (profilaxis)', 'Eliminación de placa y sarro', Decimal('100000.00')),
        ('Odontología General', 'Obturación simple (amalgama)', 'Restauración con amalgama', Decimal('200000.00')),
        ('Odontología General', 'Obturación estética (resina)', 'Restauración con resina compuesta', Decimal('250000.00')),
        ('Odontología General', 'Extracción simple', 'Extracción dental simple', Decimal('180000.00')),
        ('Odontología General', 'Extracción compleja', 'Extracción dental quirúrgica', Decimal('300000.00')),
        ('Odontología General', 'Curetaje periodontal', 'Limpieza profunda de encías', Decimal('150000.00')),
        ('Odontología General', 'Aplicación de flúor', 'Fluorización dental', Decimal('80000.00')),
        ('Odontología General', 'Radiografía periapical', 'Rx individual', Decimal('50000.00')),
        
        # Ortodoncia
        ('Ortodoncia', 'Estudio ortodóntico completo', 'Análisis cefalométrico, modelos, fotografías', Decimal('250000.00')),
        ('Ortodoncia', 'Colocación de brackets metálicos', 'Instalación completa de aparato', Decimal('3500000.00')),
        ('Ortodoncia', 'Colocación de brackets estéticos', 'Brackets de cerámica o zafiro', Decimal('4500000.00')),
        ('Ortodoncia', 'Control mensual', 'Ajuste y revisión mensual', Decimal('150000.00')),
        ('Ortodoncia', 'Retirada de brackets', 'Remoción de aparato y pulido', Decimal('300000.00')),
        ('Ortodoncia', 'Retención fija', 'Alambre de contención permanente', Decimal('400000.00')),
        ('Ortodoncia', 'Placa de contención', 'Aparato removible de retención', Decimal('350000.00')),
        ('Ortodoncia', 'Cambio de arco', 'Reemplazo de alambre ortodóntico', Decimal('80000.00')),
        
        # Endodoncia
        ('Endodoncia', 'Endodoncia unirradicular', 'Tratamiento de conducto 1 raíz', Decimal('600000.00')),
        ('Endodoncia', 'Endodoncia birradicular', 'Tratamiento de conducto 2 raíces', Decimal('800000.00')),
        ('Endodoncia', 'Endodoncia multirradicular', 'Tratamiento de conducto 3+ raíces', Decimal('1000000.00')),
        ('Endodoncia', 'Retratamiento endodóntico', 'Retratamiento de conducto previo', Decimal('900000.00')),
        ('Endodoncia', 'Apicectomía', 'Cirugía del ápice radicular', Decimal('700000.00')),
        ('Endodoncia', 'Poste de fibra de vidrio', 'Reconstrucción con poste', Decimal('350000.00')),
        ('Endodoncia', 'Corona provisional', 'Coronilla temporal', Decimal('150000.00')),
        
        # Odontopediatría
        ('Odontopediatría', 'Limpieza infantil', 'Profilaxis para niños', Decimal('90000.00')),
        ('Odontopediatría', 'Obturación temporal', 'Restauración provisional', Decimal('150000.00')),
        ('Odontopediatría', 'Sellado de fosas y fisuras', 'Prevención de caries', Decimal('120000.00')),
        ('Odontopediatría', 'Pulpotomía', 'Tratamiento pulpar en diente temporal', Decimal('250000.00')),
        ('Odontopediatría', 'Pulpectomía', 'Tratamiento de conducto en temporal', Decimal('300000.00')),
        ('Odontopediatría', 'Aplicación de flúor infantil', 'Fluorización pediátrica', Decimal('70000.00')),
        ('Odontopediatría', 'Mantenedor de espacio', 'Aparato para mantener espacio', Decimal('400000.00')),
        ('Odontopediatría', 'Extracción dental infantil', 'Extracción en diente temporal', Decimal('120000.00')),
    ]
    
    procedimientos_creados = {}
    
    for esp_nombre, nombre, descripcion, precio in procedimientos_data:
        especialidad = especialidades[esp_nombre]
        
        proc = Procedimiento(
            especialidad_id=especialidad.id,
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            activo=True
        )
        db.session.add(proc)
        db.session.flush()
        
        if esp_nombre not in procedimientos_creados:
            procedimientos_creados[esp_nombre] = []
        procedimientos_creados[esp_nombre].append(proc)
        
        print(f"✓ {nombre}: {precio:,.0f} Gs")
    
    db.session.commit()
    print()
    print(f"✓ {len(procedimientos_data)} procedimientos creados")
    print()
    
    return procedimientos_creados

def crear_precios_personalizados(medicos, procedimientos):
    """Crear precios personalizados para cada médico"""
    print("=" * 80)
    print("CREANDO PRECIOS PERSONALIZADOS POR MÉDICO")
    print("=" * 80)
    print()
    
    # Cada médico cobra diferente
    variaciones = {
        'Odontología General': [
            ('Limpieza dental (profilaxis)', Decimal('110000.00')),
            ('Obturación simple (amalgama)', Decimal('190000.00')),
            ('Extracción simple', Decimal('200000.00')),
        ],
        'Ortodoncia': [
            ('Control mensual', Decimal('160000.00')),
            ('Colocación de brackets metálicos', Decimal('3400000.00')),
            ('Placa de contención', Decimal('380000.00')),
        ],
        'Endodoncia': [
            ('Endodoncia unirradicular', Decimal('650000.00')),
            ('Endodoncia birradicular', Decimal('850000.00')),
            ('Retratamiento endodóntico', Decimal('950000.00')),
        ],
        'Odontopediatría': [
            ('Limpieza infantil', Decimal('100000.00')),
            ('Sellado de fosas y fisuras', Decimal('130000.00')),
            ('Pulpotomía', Decimal('270000.00')),
        ],
    }
    
    count = 0
    for esp_nombre, medico in medicos.items():
        if esp_nombre in variaciones:
            print(f"\nDr(a). {medico.apellido} ({esp_nombre}):")
            
            for proc_nombre, precio_custom in variaciones[esp_nombre]:
                # Buscar el procedimiento
                proc = None
                for p in procedimientos.get(esp_nombre, []):
                    if p.nombre == proc_nombre:
                        proc = p
                        break
                
                if proc:
                    pp = ProcedimientoPrecio(
                        procedimiento_id=proc.id,
                        medico_id=medico.id,
                        especialidad_id=None,
                        precio=precio_custom
                    )
                    db.session.add(pp)
                    count += 1
                    print(f"  ✓ {proc_nombre}: {precio_custom:,.0f} Gs (base: {proc.precio:,.0f} Gs)")
    
    db.session.commit()
    print()
    print(f"✓ {count} precios personalizados creados")
    print()

def crear_horarios(medicos):
    """Crear horarios de atención para cada médico"""
    print("=" * 80)
    print("CREANDO HORARIOS DE ATENCIÓN")
    print("=" * 80)
    print()
    
    # Dr. Pérez - Odontología General
    medico = medicos['Odontología General']
    horarios = [
        # Lunes a Viernes mañana
        (0, time(8, 0), time(12, 0), 30),  # Lunes
        (1, time(8, 0), time(12, 0), 30),  # Martes
        (2, time(8, 0), time(12, 0), 30),  # Miércoles
        (3, time(8, 0), time(12, 0), 30),  # Jueves
        (4, time(8, 0), time(12, 0), 30),  # Viernes
        # Martes y Jueves tarde
        (1, time(14, 0), time(18, 0), 30),  # Martes
        (3, time(14, 0), time(18, 0), 30),  # Jueves
    ]
    for dia, inicio, fin, duracion in horarios:
        h = HorarioAtencion(
            medico_id=medico.id,
            dia_semana=dia,
            hora_inicio=inicio,
            hora_fin=fin,
            duracion_consulta=duracion,
            activo=True
        )
        db.session.add(h)
    print(f"✓ Dr. Pérez: Lun-Vie 8-12h, Mar-Jue 14-18h (30 min)")
    
    # Dra. Silva - Ortodoncia
    medico = medicos['Ortodoncia']
    horarios = [
        (0, time(14, 0), time(19, 0), 45),  # Lunes tarde
        (2, time(14, 0), time(19, 0), 45),  # Miércoles tarde
        (4, time(14, 0), time(19, 0), 45),  # Viernes tarde
        (5, time(8, 0), time(13, 0), 45),   # Sábado mañana
    ]
    for dia, inicio, fin, duracion in horarios:
        h = HorarioAtencion(
            medico_id=medico.id,
            dia_semana=dia,
            hora_inicio=inicio,
            hora_fin=fin,
            duracion_consulta=duracion,
            activo=True
        )
        db.session.add(h)
    print(f"✓ Dra. Silva: Lun-Mié-Vie 14-19h, Sáb 8-13h (45 min)")
    
    # Dr. Cáceres - Endodoncia
    medico = medicos['Endodoncia']
    horarios = [
        (0, time(8, 0), time(12, 0), 60),  # Lunes
        (1, time(8, 0), time(12, 0), 60),  # Martes
        (2, time(8, 0), time(12, 0), 60),  # Miércoles
        (3, time(8, 0), time(12, 0), 60),  # Jueves
        (4, time(8, 0), time(12, 0), 60),  # Viernes
    ]
    for dia, inicio, fin, duracion in horarios:
        h = HorarioAtencion(
            medico_id=medico.id,
            dia_semana=dia,
            hora_inicio=inicio,
            hora_fin=fin,
            duracion_consulta=duracion,
            activo=True
        )
        db.session.add(h)
    print(f"✓ Dr. Cáceres: Lun-Vie 8-12h (60 min)")
    
    # Dra. Torres - Odontopediatría
    medico = medicos['Odontopediatría']
    horarios = [
        (0, time(14, 0), time(18, 0), 30),  # Lunes
        (1, time(14, 0), time(18, 0), 30),  # Martes
        (2, time(14, 0), time(18, 0), 30),  # Miércoles
        (3, time(14, 0), time(18, 0), 30),  # Jueves
        (4, time(14, 0), time(18, 0), 30),  # Viernes
        (5, time(8, 0), time(12, 0), 30),   # Sábado
    ]
    for dia, inicio, fin, duracion in horarios:
        h = HorarioAtencion(
            medico_id=medico.id,
            dia_semana=dia,
            hora_inicio=inicio,
            hora_fin=fin,
            duracion_consulta=duracion,
            activo=True
        )
        db.session.add(h)
    print(f"✓ Dra. Torres: Lun-Vie 14-18h, Sáb 8-12h (30 min)")
    
    db.session.commit()
    print()
    print("✓ Horarios de atención configurados")
    print()

def crear_insumos(especialidades):
    """Crear insumos odontológicos con stock inicial"""
    print("=" * 80)
    print("CREANDO INSUMOS")
    print("=" * 80)
    print()
    
    insumos_data = [
        # Materiales de obturación
        ('Resina compuesta (jeringa)', 'MAT-001', 'material', Decimal('180000.00'), Decimal('250000.00'), 50, 10, 'unidad'),
        ('Amalgama (cápsula)', 'MAT-002', 'material', Decimal('15000.00'), Decimal('25000.00'), 50, 20, 'unidad'),
        ('Ionómero de vidrio', 'MAT-003', 'material', Decimal('120000.00'), Decimal('180000.00'), 50, 10, 'unidad'),
        ('Cemento temporal', 'MAT-004', 'material', Decimal('50000.00'), Decimal('80000.00'), 50, 15, 'unidad'),
        
        # Anestésicos
        ('Lidocaína 2% con epinefrina', 'ANES-001', 'medicamento', Decimal('8000.00'), Decimal('15000.00'), 50, 30, 'cartucho'),
        ('Articaína 4%', 'ANES-002', 'medicamento', Decimal('12000.00'), Decimal('20000.00'), 50, 30, 'cartucho'),
        ('Agujas desechables 27G', 'ANES-003', 'consumible', Decimal('45000.00'), Decimal('70000.00'), 50, 10, 'caja'),
        
        # Material descartable
        ('Guantes de látex talle M', 'DESC-001', 'consumible', Decimal('35000.00'), Decimal('50000.00'), 50, 20, 'caja'),
        ('Mascarillas descartables', 'DESC-002', 'consumible', Decimal('25000.00'), Decimal('40000.00'), 50, 20, 'caja'),
        ('Baberos desechables', 'DESC-003', 'consumible', Decimal('30000.00'), Decimal('45000.00'), 50, 15, 'paquete'),
        ('Eyectores de saliva', 'DESC-004', 'consumible', Decimal('20000.00'), Decimal('35000.00'), 50, 20, 'bolsa'),
        ('Vasos descartables', 'DESC-005', 'consumible', Decimal('15000.00'), Decimal('25000.00'), 50, 20, 'paquete'),
        
        # Instrumental rotatorio
        ('Fresas diamantadas (set x 5)', 'INST-001', 'material', Decimal('60000.00'), Decimal('90000.00'), 50, 10, 'set'),
        ('Discos de pulir (set x 10)', 'INST-002', 'material', Decimal('40000.00'), Decimal('65000.00'), 50, 10, 'set'),
        
        # Endodoncia
        ('Limas endodónticas (set)', 'ENDO-001', 'material', Decimal('80000.00'), Decimal('120000.00'), 50, 10, 'set'),
        ('Conos de gutapercha (caja)', 'ENDO-002', 'material', Decimal('50000.00'), Decimal('80000.00'), 50, 15, 'caja'),
        
        # Ortodoncia
        ('Brackets metálicos (set completo)', 'ORTO-001', 'material', Decimal('450000.00'), Decimal('650000.00'), 50, 5, 'set'),
        ('Arcos ortodónticos', 'ORTO-002', 'material', Decimal('25000.00'), Decimal('40000.00'), 50, 20, 'unidad'),
        ('Ligaduras elásticas', 'ORTO-003', 'consumible', Decimal('15000.00'), Decimal('25000.00'), 50, 20, 'bolsa'),
        
        # Higiene
        ('Cepillos dentales infantiles', 'HIG-001', 'consumible', Decimal('8000.00'), Decimal('15000.00'), 50, 30, 'unidad'),
    ]
    
    for nombre, codigo, categoria, compra, venta, stock, minimo, unidad in insumos_data:
        insumo = Insumo(
            nombre=nombre,
            codigo=codigo,
            categoria=categoria,
            precio_compra=compra,
            precio_venta=venta,
            cantidad_actual=stock,
            stock_minimo=minimo,
            unidad_medida=unidad,
            activo=True
        )
        db.session.add(insumo)
        margen = ((venta - compra) / compra * 100) if compra > 0 else 0
        print(f"✓ {nombre}: Stock {stock} {unidad} (Margen: {margen:.1f}%)")
    
    db.session.commit()
    print()
    print(f"✓ {len(insumos_data)} insumos creados")
    print()

def crear_pacientes():
    """Crear pacientes variados"""
    print("=" * 80)
    print("CREANDO PACIENTES")
    print("=" * 80)
    print()
    
    pacientes_data = [
        {
            'nombre': 'Ramón',
            'apellido': 'Giménez',
            'cedula': '1234567',
            'ruc': '1234567-8',
            'razon_social': 'Ramón Giménez',
            'condicion_tributaria': 'Contribuyente',
            'fecha_nacimiento': date(1980, 3, 15),
            'sexo': 'M',
            'telefono': '0981-111222',
            'email': 'ramon.gimenez@email.com',
            'direccion': 'Avda. Eusebio Ayala 1234',
            'direccion_facturacion': 'Avda. Eusebio Ayala 1234',
            'ciudad': 'Asunción',
            'tipo_sangre': 'O+',
        },
        {
            'nombre': 'Carolina',
            'apellido': 'Vera',
            'cedula': '2345678',
            'ruc': None,
            'razon_social': None,
            'condicion_tributaria': 'Consumidor Final',
            'fecha_nacimiento': date(1997, 7, 22),
            'sexo': 'F',
            'telefono': '0982-333444',
            'email': 'carolina.vera@email.com',
            'direccion': 'Calle Palma 567',
            'direccion_facturacion': 'Calle Palma 567',
            'ciudad': 'Asunción',
            'tipo_sangre': 'A+',
        },
        {
            'nombre': 'José Luis',
            'apellido': 'Benítez',
            'cedula': '3456789',
            'ruc': '3456789-0',
            'razon_social': 'Ferretería El Tornillo',
            'condicion_tributaria': 'Contribuyente',
            'fecha_nacimiento': date(1970, 11, 8),
            'sexo': 'M',
            'telefono': '0983-555666',
            'email': 'josebenitez@email.com',
            'direccion': 'Ruta 2 Km 15',
            'direccion_facturacion': 'Ruta 2 Km 15',
            'ciudad': 'Capiatá',
            'tipo_sangre': 'B+',
        },
        {
            'nombre': 'Sofía',
            'apellido': 'Martínez',
            'cedula': '4567890',
            'ruc': None,
            'razon_social': None,
            'condicion_tributaria': 'Consumidor Final',
            'fecha_nacimiento': date(2017, 4, 12),
            'sexo': 'F',
            'telefono': '0984-777888',
            'email': 'marta.lugo@email.com',  # Email de la madre
            'direccion': 'Barrio San Pablo, calle 3',
            'direccion_facturacion': 'Barrio San Pablo, calle 3',
            'ciudad': 'Luque',
            'alergias': 'Penicilina',
            'tipo_sangre': 'O+',
        },
        {
            'nombre': 'Emilia',
            'apellido': 'Rojas',
            'cedula': '5678901',
            'ruc': None,
            'razon_social': None,
            'condicion_tributaria': 'Consumidor Final',
            'fecha_nacimiento': date(1990, 9, 30),
            'sexo': 'F',
            'telefono': '0985-999000',
            'email': 'emilia.rojas@email.com',
            'direccion': 'Zeballos Cué 890',
            'direccion_facturacion': 'Zeballos Cué 890',
            'ciudad': 'Asunción',
            'tipo_sangre': 'AB+',
        },
    ]
    
    for data in pacientes_data:
        paciente = Paciente(**data)
        db.session.add(paciente)
        edad = paciente.edad
        print(f"✓ {paciente.nombre_completo} ({edad} años) - {data['ciudad']}")
    
    db.session.commit()
    print()
    print(f"✓ {len(pacientes_data)} pacientes creados")
    print()

def main():
    """Función principal"""
    print()
    print("*" * 80)
    print(" SCRIPT DE RESETEO - CONSULTORIO ODONTOLÓGICO NORMA BENÍTEZ")
    print("*" * 80)
    print()
    
    respuesta = input("⚠️  ADVERTENCIA: Esto eliminará TODOS los datos excepto configuración.\n¿Desea continuar? (escriba 'SI' para confirmar): ")
    
    if respuesta.strip().upper() != 'SI':
        print("\n✗ Operación cancelada por el usuario")
        return
    
    print()
    
    app = create_app()
    with app.app_context():
        try:
            # 1. Limpiar base de datos
            limpiar_base_datos()
            
            # 2. Crear usuarios y médicos
            medicos = crear_usuarios_y_medicos()
            
            # 3. Crear especialidades
            especialidades = crear_especialidades()
            
            # 4. Asignar especialidades a médicos
            asignar_especialidades_a_medicos(medicos, especialidades)
            
            # 5. Crear procedimientos
            procedimientos = crear_procedimientos(especialidades)
            
            # 6. Crear precios personalizados
            crear_precios_personalizados(medicos, procedimientos)
            
            # 7. Crear horarios
            crear_horarios(medicos)
            
            # 8. Crear insumos
            crear_insumos(especialidades)
            
            # 9. Crear pacientes
            crear_pacientes()
            
            print("=" * 80)
            print("✓ BASE DE DATOS RESETEADA EXITOSAMENTE")
            print("=" * 80)
            print()
            print("CREDENCIALES DE ACCESO:")
            print("-" * 80)
            print("Admin:         norma.benitez / 123456")
            print("Recepción:     recepcion / 123456")
            print("Caja:          caja / 123456")
            print("Médicos:       dr.perez, dra.silva, dr.caceres, dra.torres / 123456")
            print("-" * 80)
            print()
            print("✓ Sistema listo para usar")
            print()
            
        except Exception as e:
            print()
            print("=" * 80)
            print("✗ ERROR DURANTE EL RESETEO")
            print("=" * 80)
            print(f"Error: {str(e)}")
            print()
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    main()
