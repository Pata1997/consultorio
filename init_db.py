"""
Script para inicializar la base de datos con datos de ejemplo
"""
from app import create_app, db
from app.models import *
from datetime import date, time, datetime, timedelta

def init_database():
    """Inicializar base de datos con datos de ejemplo"""
    app = create_app()
    
    with app.app_context():
        print("Creando tablas...")
        db.create_all()
        
        print("\nCreando datos iniciales...")
        
        # 1. Crear usuario administrador
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                email='admin@consultorio.com',
                rol='admin',
                activo=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("✓ Usuario admin creado (usuario: admin, password: admin123)")
        
        # 2. Crear especialidades
        especialidades_data = [
            {'nombre': 'Medicina General', 'descripcion': 'Consultas generales', 'precio_consulta': 250000},
            {'nombre': 'Odontología', 'descripcion': 'Salud dental', 'precio_consulta': 350000},
            {'nombre': 'Pediatría', 'descripcion': 'Atención de niños y adolescentes', 'precio_consulta': 280000},
            {'nombre': 'Dermatología', 'descripcion': 'Enfermedades de la piel', 'precio_consulta': 300000},
            {'nombre': 'Cardiología', 'descripcion': 'Enfermedades del corazón', 'precio_consulta': 400000},
        ]
        
        especialidades = {}
        for esp_data in especialidades_data:
            if not Especialidad.query.filter_by(nombre=esp_data['nombre']).first():
                esp = Especialidad(**esp_data)
                db.session.add(esp)
                especialidades[esp_data['nombre']] = esp
                print(f"✓ Especialidad {esp_data['nombre']} creada")
        
        db.session.flush()
        
        # 3. Crear médicos de ejemplo
        medicos_data = [
            {
                'nombre': 'Juan', 'apellido': 'López', 'cedula': '1234567',
                'registro_profesional': 'MP-12345', 'telefono': '0981-111111',
                'email': 'jlopez@consultorio.com', 'especialidades': ['Odontología'],
                'username': 'jlopez', 'password': 'medico123'
            },
            {
                'nombre': 'Ana', 'apellido': 'Martínez', 'cedula': '2345678',
                'registro_profesional': 'MP-23456', 'telefono': '0981-222222',
                'email': 'amartinez@consultorio.com', 'especialidades': ['Medicina General'],
                'username': 'amartinez', 'password': 'medico123'
            },
            {
                'nombre': 'Carlos', 'apellido': 'Rodríguez', 'cedula': '3456789',
                'registro_profesional': 'MP-34567', 'telefono': '0981-333333',
                'email': 'crodriguez@consultorio.com', 'especialidades': ['Pediatría'],
                'username': 'crodriguez', 'password': 'medico123'
            }
        ]
        
        for med_data in medicos_data:
            if not Usuario.query.filter_by(username=med_data['username']).first():
                # Crear usuario
                usuario = Usuario(
                    username=med_data['username'],
                    email=med_data['email'],
                    rol='medico',
                    activo=True
                )
                usuario.set_password(med_data['password'])
                db.session.add(usuario)
                db.session.flush()
                
                # Crear médico
                medico = Medico(
                    usuario_id=usuario.id,
                    nombre=med_data['nombre'],
                    apellido=med_data['apellido'],
                    cedula=med_data['cedula'],
                    registro_profesional=med_data['registro_profesional'],
                    telefono=med_data['telefono'],
                    email=med_data['email'],
                    fecha_ingreso=date.today(),
                    activo=True
                )
                db.session.add(medico)
                db.session.flush()
                
                # Asignar especialidades
                for esp_nombre in med_data['especialidades']:
                    esp = Especialidad.query.filter_by(nombre=esp_nombre).first()
                    if esp:
                        med_esp = MedicoEspecialidad(
                            medico_id=medico.id,
                            especialidad_id=esp.id
                        )
                        db.session.add(med_esp)
                
                # Crear horario de atención (Lunes a Viernes, 8:00-12:00 y 14:00-18:00)
                for dia in range(5):  # Lunes a Viernes
                    # Mañana
                    horario_manana = HorarioAtencion(
                        medico_id=medico.id,
                        dia_semana=dia,
                        hora_inicio=time(8, 0),
                        hora_fin=time(12, 0),
                        duracion_consulta=30
                    )
                    db.session.add(horario_manana)
                    
                    # Tarde
                    horario_tarde = HorarioAtencion(
                        medico_id=medico.id,
                        dia_semana=dia,
                        hora_inicio=time(14, 0),
                        hora_fin=time(18, 0),
                        duracion_consulta=30
                    )
                    db.session.add(horario_tarde)
                
                print(f"✓ Médico Dr. {med_data['nombre']} {med_data['apellido']} creado")
        
        # 4. Crear usuario recepcionista
        if not Usuario.query.filter_by(username='recepcion').first():
            recepcionista = Usuario(
                username='recepcion',
                email='recepcion@consultorio.com',
                rol='recepcionista',
                activo=True
            )
            recepcionista.set_password('recepcion123')
            db.session.add(recepcionista)
            print("✓ Usuario recepcionista creado (usuario: recepcion, password: recepcion123)")
        
        # 5. Crear formas de pago
        formas_pago_data = [
            {'nombre': 'efectivo', 'descripcion': 'Pago en efectivo', 'requiere_referencia': False},
            {'nombre': 'tarjeta_debito', 'descripcion': 'Tarjeta de débito', 'requiere_referencia': True},
            {'nombre': 'tarjeta_credito', 'descripcion': 'Tarjeta de crédito', 'requiere_referencia': True},
            {'nombre': 'cheque', 'descripcion': 'Cheque', 'requiere_referencia': True},
            {'nombre': 'transferencia', 'descripcion': 'Transferencia bancaria', 'requiere_referencia': True},
        ]
        
        for fp_data in formas_pago_data:
            if not FormaPago.query.filter_by(nombre=fp_data['nombre']).first():
                fp = FormaPago(**fp_data)
                db.session.add(fp)
                print(f"✓ Forma de pago {fp_data['nombre']} creada")
        
        # 6. Crear insumos de ejemplo
        insumos_data = [
            {'nombre': 'Anestesia dental', 'precio_unitario': 50000, 'cantidad_actual': 20, 
             'stock_minimo': 10, 'especialidades': ['Odontología']},
            {'nombre': 'Amalgama dental', 'precio_unitario': 80000, 'cantidad_actual': 15,
             'stock_minimo': 10, 'especialidades': ['Odontología']},
            {'nombre': 'Guantes látex (caja 100)', 'precio_unitario': 50000, 'cantidad_actual': 10,
             'stock_minimo': 5, 'especialidades': ['Odontología', 'Medicina General', 'Pediatría']},
            {'nombre': 'Jeringas descartables (paquete 10)', 'precio_unitario': 30000, 'cantidad_actual': 8,
             'stock_minimo': 5, 'especialidades': ['Medicina General', 'Pediatría']},
            {'nombre': 'Gasas esterilizadas', 'precio_unitario': 15000, 'cantidad_actual': 25,
             'stock_minimo': 15, 'especialidades': ['Odontología', 'Medicina General']},
        ]
        
        for ins_data in insumos_data:
            especialidades_insumo = ins_data.pop('especialidades')
            if not Insumo.query.filter_by(nombre=ins_data['nombre']).first():
                insumo = Insumo(**ins_data)
                db.session.add(insumo)
                db.session.flush()
                
                # Asignar a especialidades
                for esp_nombre in especialidades_insumo:
                    esp = Especialidad.query.filter_by(nombre=esp_nombre).first()
                    if esp:
                        ins_esp = InsumoEspecialidad(
                            insumo_id=insumo.id,
                            especialidad_id=esp.id
                        )
                        db.session.add(ins_esp)
                
                print(f"✓ Insumo {ins_data['nombre']} creado")
        
        # 7. Crear procedimientos
        procedimientos_data = [
            {'nombre': 'Obturación dental', 'precio': 120000, 'especialidad': 'Odontología'},
            {'nombre': 'Extracción dental', 'precio': 150000, 'especialidad': 'Odontología'},
            {'nombre': 'Limpieza dental', 'precio': 80000, 'especialidad': 'Odontología'},
            {'nombre': 'Endodoncia', 'precio': 300000, 'especialidad': 'Odontología'},
            {'nombre': 'Sutura', 'precio': 50000, 'especialidad': 'Medicina General'},
            {'nombre': 'Curación', 'precio': 30000, 'especialidad': 'Medicina General'},
            {'nombre': 'Nebulización', 'precio': 40000, 'especialidad': 'Pediatría'},
        ]
        
        for proc_data in procedimientos_data:
            esp_nombre = proc_data.pop('especialidad')
            esp = Especialidad.query.filter_by(nombre=esp_nombre).first()
            if esp and not Procedimiento.query.filter_by(nombre=proc_data['nombre'], especialidad_id=esp.id).first():
                procedimiento = Procedimiento(
                    especialidad_id=esp.id,
                    **proc_data
                )
                db.session.add(procedimiento)
                print(f"✓ Procedimiento {proc_data['nombre']} creado")
        
        # 8. Crear pacientes de ejemplo
        pacientes_data = [
            {'nombre': 'Pedro', 'apellido': 'González', 'cedula': '4567890', 
             'fecha_nacimiento': date(1985, 5, 15), 'sexo': 'M', 'telefono': '0981-444444',
             'email': 'pgonzalez@email.com', 'tipo_sangre': 'O+'},
            {'nombre': 'María', 'apellido': 'Silva', 'cedula': '5678901',
             'fecha_nacimiento': date(1990, 8, 20), 'sexo': 'F', 'telefono': '0981-555555',
             'email': 'msilva@email.com', 'tipo_sangre': 'A+'},
            {'nombre': 'Luis', 'apellido': 'Ramírez', 'cedula': '6789012',
             'fecha_nacimiento': date(1978, 3, 10), 'sexo': 'M', 'telefono': '0981-666666',
             'tipo_sangre': 'B+'},
        ]
        
        for pac_data in pacientes_data:
            if not Paciente.query.filter_by(cedula=pac_data['cedula']).first():
                paciente = Paciente(**pac_data)
                db.session.add(paciente)
                print(f"✓ Paciente {pac_data['nombre']} {pac_data['apellido']} creado")
        
        db.session.commit()
        
        # 8. Crear configuración del consultorio
        if not ConfiguracionConsultorio.query.first():
            config = ConfiguracionConsultorio(
                nombre='Consultorio Médico San Rafael',
                razon_social='Consultorio Médico San Rafael S.R.L.',
                ruc='80012345-6',
                direccion='Av. San Martín 1234, Asunción, Paraguay',
                telefono='(021) 123-4567',
                email='info@consultoriosanrafael.com',
                sitio_web='www.consultoriosanrafael.com',
                slogan='Tu salud es nuestra prioridad',
                horario_atencion='Lunes a Viernes: 8:00 - 18:00 | Sábados: 8:00 - 12:00',
                punto_expedicion='001-001',
                timbrado='12345678',
                fecha_inicio_timbrado=date(2025, 1, 1),
                fecha_fin_timbrado=date(2025, 12, 31),
                numero_factura_actual=1
            )
            db.session.add(config)
            print("✓ Configuración del consultorio creada")
        
        db.session.commit()
        
        print("\n✅ Base de datos inicializada correctamente!")
        print("\n=== CREDENCIALES DE ACCESO ===")
        print("Administrador:")
        print("  Usuario: admin")
        print("  Password: admin123")
        print("\nRecepcionista:")
        print("  Usuario: recepcion")
        print("  Password: recepcion123")
        print("\nMédicos:")
        print("  Usuario: jlopez (Dr. López - Odontología)")
        print("  Usuario: amartinez (Dra. Martínez - Medicina General)")
        print("  Usuario: crodriguez (Dr. Rodríguez - Pediatría)")
        print("  Password para todos: medico123")
        print("===============================\n")

if __name__ == '__main__':
    init_database()
