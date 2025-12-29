"""
Script para crear ventas de prueba para demostrar la funcionalidad de cajera
"""
from app import create_app, db
from app.models import (
    Venta, VentaDetalle, Paciente, Consulta, Especialidad,
    ConsultaProcedimiento, Procedimiento
)
from datetime import datetime
from decimal import Decimal

app = create_app()

with app.app_context():
    print("=" * 80)
    print("CREANDO VENTAS DE PRUEBA")
    print("=" * 80)
    
    # Obtener consultas existentes
    consultas = Consulta.query.all()
    
    if not consultas:
        print("❌ No hay consultas en la base de datos")
        print("Por favor, crea una consulta con procedimientos primero")
        exit(1)
    
    ventas_creadas = 0
    
    for consulta in consultas:
        # Verificar si ya tiene venta
        venta_existente = Venta.query.filter_by(consulta_id=consulta.id).first()
        if venta_existente:
            print(f"⚠️  Consulta {consulta.id} ya tiene venta asociada")
            continue
        
        # Obtener datos
        paciente = consulta.paciente
        especialidad = consulta.especialidad
        
        # Calcular precio de consulta
        precio_consulta = float(especialidad.precio_consulta) if especialidad else 0
        
        # Obtener procedimientos
        procedimientos = ConsultaProcedimiento.query.filter_by(consulta_id=consulta.id).all()
        total_procedimientos = sum(float(p.precio) for p in procedimientos)
        
        # Si no tiene ni consulta ni procedimientos, agregar un procedimiento de ejemplo
        if precio_consulta == 0 and total_procedimientos == 0:
            # Obtener un procedimiento cualquiera para hacer la venta válida
            proc_ejemplo = Procedimiento.query.filter_by(activo=True).first()
            if proc_ejemplo:
                total_procedimientos = float(proc_ejemplo.precio)
                procedimientos = []  # Vamos a crear el detalle manualmente
                print(f"   → Agregando procedimiento de ejemplo: {proc_ejemplo.nombre}")
        
        # Calcular totales (IVA incluido)
        total = precio_consulta + total_procedimientos
        if total == 0:
            print(f"⚠️  Consulta {consulta.id} no tiene monto, se omite")
            continue
        
        iva = total / 11
        subtotal = total - iva
        
        # Crear venta pendiente
        numero_provisional = f"PEND-{consulta.id}-{int(datetime.now().timestamp())}"
        
        venta = Venta(
            numero_factura=numero_provisional,
            timbrado=None,
            ruc_factura=paciente.ruc or paciente.cedula or '',
            nombre_factura=paciente.razon_social or paciente.nombre_completo,
            direccion_facturacion=paciente.direccion_facturacion or paciente.direccion or '',
            caja_id=None,
            consulta_id=consulta.id,
            paciente_id=consulta.paciente_id,
            fecha=datetime.now(),
            subtotal=Decimal(str(round(subtotal, 2))),
            iva=Decimal(str(round(iva, 2))),
            total=Decimal(str(round(total, 2))),
            estado='pendiente',
            usuario_registro_id=7,  # Usuario admin (norma.benitez)
            observaciones='Venta de prueba generada por script'
        )
        db.session.add(venta)
        db.session.flush()
        
        # Agregar detalle de consulta si tiene precio
        if precio_consulta > 0:
            detalle = VentaDetalle(
                venta_id=venta.id,
                concepto=f"Consulta - {especialidad.nombre if especialidad else 'General'}",
                descripcion=f"Médico: {consulta.medico.nombre_completo if consulta.medico else 'N/A'}",
                cantidad=1,
                precio_unitario=Decimal(str(precio_consulta)),
                subtotal=Decimal(str(precio_consulta)),
                tipo_item='consulta'
            )
            db.session.add(detalle)
        
        # Agregar detalles de procedimientos
        if procedimientos:
            for proc in procedimientos:
                detalle = VentaDetalle(
                    venta_id=venta.id,
                    concepto=proc.procedimiento_rel.nombre,
                    descripcion=proc.observaciones or '',
                    cantidad=1,
                    precio_unitario=Decimal(str(float(proc.precio))),
                    subtotal=Decimal(str(float(proc.precio))),
                    tipo_item='procedimiento',
                    item_id=proc.procedimiento_id
                )
                db.session.add(detalle)
        elif total_procedimientos > 0:
            # Agregar el procedimiento de ejemplo
            detalle = VentaDetalle(
                venta_id=venta.id,
                concepto=proc_ejemplo.nombre,
                descripcion='Procedimiento de ejemplo',
                cantidad=1,
                precio_unitario=Decimal(str(total_procedimientos)),
                subtotal=Decimal(str(total_procedimientos)),
                tipo_item='procedimiento',
                item_id=proc_ejemplo.id
            )
            db.session.add(detalle)
        
        db.session.commit()
        ventas_creadas += 1
        
        print(f"✅ Venta creada para Consulta {consulta.id}")
        print(f"   Paciente: {paciente.nombre_completo}")
        print(f"   Total: {total:,.0f} Gs")
    
    print()
    print("=" * 80)
    print(f"✅ {ventas_creadas} ventas pendientes creadas exitosamente")
    print("=" * 80)
    print()
    print("Ahora puedes:")
    print("1. Ir a http://127.0.0.1:5000/facturacion/ventas/pendientes")
    print("2. Procesar las ventas pendientes como cajera")
