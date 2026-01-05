from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import (Caja, Venta, VentaDetalle, Pago, FormaPago, Consulta,
                        ConsultaInsumo, ConsultaProcedimiento, Especialidad,
                        ConfiguracionConsultorio)
from app.utils.auditoria import audit
from datetime import datetime, date
import traceback
from sqlalchemy import func
from app.utils.number_utils import parse_decimal_from_form
from app.utils.pdf_generator import ArqueoCajaPDF
from app.utils.ticket_generator import generar_ticket_pdf
import os
import json
import io

"""
IMPORTANTE: IVA INCLUIDO - SISTEMA PARAGUAYO

En Paraguay, todos los precios incluyen IVA (10%).
El cálculo correcto es:
- TOTAL = suma de todos los precios (lo que ve y paga el cliente)
- IVA = TOTAL / 11  (equivalente a TOTAL × 10/110)
- GRAVADAS = TOTAL - IVA  (equivalente a TOTAL × 100/110)

Ejemplo:
- Consulta: 350.000 Gs
- Procedimiento: 80.000 Gs
- TOTAL: 430.000 Gs ← el cliente paga esto
- IVA 10%: 39.091 Gs (430.000 ÷ 11)
- Gravadas: 390.909 Gs (430.000 - 39.091)

NUNCA sumar IVA al final (eso sería IVA agregado, incorrecto para Paraguay).
"""

bp = Blueprint('facturacion', __name__, url_prefix='/facturacion')

@bp.route('/caja')
@login_required
def estado_caja():
    """Ver estado de la caja"""
    # Buscar caja abierta del usuario
    caja_abierta = Caja.query.filter_by(
        estado='abierta',
        usuario_apertura_id=current_user.id
    ).first()
    
    # Estadísticas si hay caja abierta
    from decimal import Decimal
    total_vendido = Decimal('0')
    ventas = []
    if caja_abierta:
        ventas = Venta.query.filter_by(caja_id=caja_abierta.id, estado='pagada').order_by(Venta.fecha.desc()).all()
        total_vendido = sum((v.total for v in ventas), Decimal('0'))
    
    return render_template('facturacion/estado_caja.html',
                         caja=caja_abierta,
                         total_vendido=total_vendido,
                         ventas=ventas)

@bp.route('/caja/abrir', methods=['POST'])
@login_required
def abrir_caja():
    """Abrir caja"""
    # Verificar que no haya caja abierta
    caja_existente = Caja.query.filter_by(
        estado='abierta',
        usuario_apertura_id=current_user.id
    ).first()
    
    if caja_existente:
        flash('Ya tiene una caja abierta', 'warning')
        return redirect(url_for('facturacion.estado_caja'))
    
    from decimal import Decimal
    monto_inicial_raw = request.form.get('monto_inicial', '0')
    current_app.logger.debug(f"[abrir_caja] monto_inicial_raw recibido: '{monto_inicial_raw}'")
    monto_inicial = parse_decimal_from_form(monto_inicial_raw)
    current_app.logger.debug(f"[abrir_caja] monto_inicial parseado: {monto_inicial}")
    if monto_inicial is None:
        monto_inicial = Decimal('0')
    
    caja = Caja(
        monto_inicial=monto_inicial,
        usuario_apertura_id=current_user.id
    )
    
    db.session.add(caja)
    db.session.commit()
    
    # Auditar apertura de caja
    audit('crear', 'cajas', caja.id, descripcion=f'Caja abierta - Monto inicial: {monto_inicial}')
    
    flash('Caja abierta exitosamente', 'success')
    return redirect(url_for('facturacion.estado_caja'))

@bp.route('/caja/cerrar', methods=['POST'])
@login_required
def cerrar_caja():
    """Cerrar caja y generar arqueo"""
    caja = Caja.query.filter_by(
        estado='abierta',
        usuario_apertura_id=current_user.id
    ).first()
    
    if not caja:
        flash('No hay caja abierta', 'warning')
        return redirect(url_for('facturacion.estado_caja'))
    
    from decimal import Decimal
    monto_final = parse_decimal_from_form(request.form.get('monto_final', '0'))
    if monto_final is None:
        monto_final = Decimal('0')

    caja.monto_final = monto_final
    caja.fecha_cierre = datetime.utcnow()
    caja.usuario_cierre_id = current_user.id
    caja.estado = 'cerrada'
    caja.observaciones = request.form.get('observaciones', '')
    
    db.session.commit()
    
    # Auditar cierre de caja
    audit('editar', 'cajas', caja.id, descripcion=f'Caja cerrada - Monto final: {monto_final}')
    
    flash('Caja cerrada exitosamente', 'success')
    return redirect(url_for('facturacion.arqueo_caja', id=caja.id))

@bp.route('/caja/<int:id>/arqueo')
@login_required
def arqueo_caja(id):
    """Ver arqueo de caja"""
    caja = Caja.query.get_or_404(id)
    
    # Obtener ventas de la caja
    ventas = Venta.query.filter_by(caja_id=id).all()
    
    # Calcular totales por forma de pago
    formas_pago = db.session.query(
        FormaPago.nombre,
        func.sum(Pago.monto).label('total')
    ).join(Pago).join(Venta).filter(
        Venta.caja_id == id,
        Pago.estado == 'confirmado'
    ).group_by(FormaPago.nombre).all()
    
    from decimal import Decimal
    total_esperado = sum((v.total for v in ventas if v.estado == 'pagada'), Decimal('0'))
    monto_final = caja.monto_final if caja.monto_final else Decimal('0')
    diferencia = monto_final - (caja.monto_inicial + total_esperado)
    
    return render_template('facturacion/arqueo_caja.html',
                         caja=caja,
                         ventas=ventas,
                         formas_pago=formas_pago,
                         total_esperado=total_esperado,
                         diferencia=diferencia)

@bp.route('/caja/<int:id>/arqueo/pdf')
@login_required
def descargar_arqueo_pdf(id):
    """Generar y descargar PDF del arqueo de caja"""
    caja = Caja.query.get_or_404(id)
    
    # Obtener ventas de la caja
    ventas = Venta.query.filter_by(caja_id=id).all()
    
    # Calcular totales por forma de pago
    formas_pago = db.session.query(
        FormaPago.nombre,
        func.sum(Pago.monto).label('total')
    ).join(Pago).join(Venta).filter(
        Venta.caja_id == id,
        Pago.estado == 'confirmado'
    ).group_by(FormaPago.nombre).all()
    
    # Obtener configuración
    config = ConfiguracionConsultorio.query.first()
    
    # Generar nombre del archivo
    fecha_str = caja.fecha_cierre.strftime('%Y%m%d_%H%M') if caja.fecha_cierre else datetime.now().strftime('%Y%m%d_%H%M')
    filename = f'Arqueo_Caja_{id}_{fecha_str}.pdf'
    
    # Crear ruta absoluta a la carpeta reports en la raíz del proyecto
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    reports_dir = os.path.join(project_root, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, filename)
    
    # Generar PDF
    pdf = ArqueoCajaPDF(filepath, caja, ventas, formas_pago, config)
    pdf.generar()
    
    # Enviar archivo
    return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')

@bp.route('/ventas')
@login_required
def listar_ventas():
    """Listar ventas"""
    fecha_filtro = request.args.get('fecha', date.today().isoformat())
    
    if fecha_filtro:
        fecha_inicio = datetime.strptime(fecha_filtro, '%Y-%m-%d')
        fecha_fin = fecha_inicio.replace(hour=23, minute=59, second=59)
        ventas = Venta.query.filter(
            Venta.fecha >= fecha_inicio,
            Venta.fecha <= fecha_fin
        ).order_by(Venta.fecha.desc()).all()
    else:
        ventas = Venta.query.order_by(Venta.fecha.desc()).limit(50).all()
    
    return render_template('facturacion/listar_ventas.html',
                         ventas=ventas,
                         fecha_filtro=fecha_filtro)


@bp.route('/ventas/pendientes')
@login_required
def ventas_pendientes():
    """Listar ventas pendientes (estado == 'pendiente') para que la cajera las procese"""
    ventas = Venta.query.filter_by(estado='pendiente').order_by(Venta.fecha.desc()).all()
    
    # Debug: verificar cuántas ventas hay y sus estados
    total_ventas = Venta.query.count()
    ventas_por_estado = db.session.query(Venta.estado, db.func.count(Venta.id)).group_by(Venta.estado).all()
    current_app.logger.debug(f"[ventas_pendientes] Total ventas en BD: {total_ventas}")
    current_app.logger.debug(f"[ventas_pendientes] Ventas por estado: {ventas_por_estado}")
    current_app.logger.debug(f"[ventas_pendientes] Ventas pendientes encontradas: {len(ventas)}")
    
    return render_template('facturacion/ventas_pendientes.html', ventas=ventas)

@bp.route('/ventas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_venta():
    """Crear venta manual o buscar consultas pendientes"""
    from app.models import Paciente
    
    # Verificar caja abierta
    caja = Caja.query.filter_by(
        estado='abierta',
        usuario_apertura_id=current_user.id
    ).first()
    
    if not caja:
        flash('Debe abrir su caja antes de realizar ventas', 'warning')
        return redirect(url_for('facturacion.estado_caja'))
    
    # Buscar consultas pendientes de pago
    consultas_pendientes = Consulta.query.filter(
        ~Consulta.id.in_(
            db.session.query(Venta.consulta_id).filter(Venta.consulta_id.isnot(None))
        )
    ).order_by(Consulta.fecha.desc()).limit(20).all()
    
    return render_template('facturacion/nueva_venta.html',
                         caja=caja,
                         consultas_pendientes=consultas_pendientes)

@bp.route('/ventas/nueva/<int:consulta_id>')
@login_required
def nueva_venta_desde_consulta(consulta_id):
    """Vista para facturar una consulta - muestra detalle y permite registrar pago"""
    from app.models import Paciente, Procedimiento
    from app.models.consultorio import ConsultaProcedimiento, ConsultaInsumo
    
    consulta = Consulta.query.get_or_404(consulta_id)
    
    # Verificar existencia de venta vinculada
    venta_existente = Venta.query.filter_by(consulta_id=consulta_id).first()
    # Si existe y ya fue pagada, impedir volver a facturar
    if venta_existente and venta_existente.estado == 'pagada':
        flash('Esta consulta ya fue facturada', 'warning')
        return redirect(url_for('facturacion.nueva_venta'))
    # Si existe y está pendiente, permitir continuar para facturar/editar la venta pendiente
    
    # Verificar caja abierta
    caja = Caja.query.filter_by(
        estado='abierta',
        usuario_apertura_id=current_user.id
    ).first()
    
    if not caja:
        flash('Debe abrir su caja antes de realizar ventas', 'warning')
        return redirect(url_for('facturacion.estado_caja'))
    
    # Obtener datos del paciente
    paciente = consulta.paciente
    especialidad = Especialidad.query.get(consulta.especialidad_id)
    
    # Calcular totales
    precio_consulta = float(especialidad.precio_consulta) if especialidad.precio_consulta else 0
    
    # Obtener procedimientos realizados
    procedimientos = ConsultaProcedimiento.query.filter_by(consulta_id=consulta.id).all()
    total_procedimientos = sum(float(p.precio) for p in procedimientos)
    
    # Obtener insumos usados
    insumos = ConsultaInsumo.query.filter_by(consulta_id=consulta.id).all()
    total_insumos = sum(float(i.subtotal) for i in insumos)
    
    # Calcular totales
    subtotal = precio_consulta + total_procedimientos + total_insumos
    # IVA incluido (Paraguay): el total es la suma de precios, IVA = total/11
    total = subtotal
    iva = total / 11
    subtotal = total - iva  # Gravadas (base imponible)
    
    # Obtener formas de pago disponibles
    formas_pago = FormaPago.query.filter_by(activo=True).all()
    
    return render_template('facturacion/detalle_facturacion.html',
                         consulta=consulta,
                         paciente=paciente,
                         especialidad=especialidad,
                         procedimientos=procedimientos,
                         insumos=insumos,
                         precio_consulta=precio_consulta,
                         total_procedimientos=total_procedimientos,
                         total_insumos=total_insumos,
                         subtotal=subtotal,
                         iva=iva,
                         total=total,
                         caja=caja,
                         formas_pago=formas_pago)
@bp.route('/ventas/facturar/<int:consulta_id>', methods=['POST'])
@login_required
def procesar_factura(consulta_id):
    """Procesar factura de consulta con pagos múltiples"""
    from app.models.consultorio import ConsultaProcedimiento, ConsultaInsumo, MovimientoInsumo
    from app.models import ConfiguracionConsultorio
    from app.models import Insumo
    
    consulta = Consulta.query.get_or_404(consulta_id)
    
    # Verificar si ya existe una venta vinculada a la consulta (preferir la pendiente)
    venta_existente = Venta.query.filter_by(consulta_id=consulta_id, estado='pendiente').first()
    # Log venta existente para trazabilidad
    try:
        if venta_existente:
            current_app.logger.debug(f"[procesar_factura] venta_existente found id={venta_existente.id} estado={venta_existente.estado} consulta_id={consulta_id}")
        else:
            current_app.logger.debug(f"[procesar_factura] no venta_existente for consulta_id={consulta_id}")
    except Exception:
        pass
    if venta_existente and venta_existente.estado == 'pagada':
        flash('Esta consulta ya fue facturada', 'error')
        return redirect(url_for('facturacion.nueva_venta'))
    
    # Verificar caja abierta
    caja = Caja.query.filter_by(
        estado='abierta',
        usuario_apertura_id=current_user.id
    ).first()
    
    if not caja:
        flash('Su caja no está abierta', 'error')
        return redirect(url_for('facturacion.estado_caja'))
    
    try:
        # Obtener datos del formulario
        monto_efectivo = float(request.form.get('monto_efectivo', 0))
        monto_debito = float(request.form.get('monto_debito', 0))
        monto_credito = float(request.form.get('monto_credito', 0))
        referencia_debito = request.form.get('referencia_debito', '')
        referencia_credito = request.form.get('referencia_credito', '')
        observaciones = request.form.get('observaciones', '')
        
        # Datos de facturación (si el cajero no los provee, rellenar desde paciente)
        ruc_factura = request.form.get('ruc_factura', '')
        nombre_factura = request.form.get('nombre_factura', '')
        direccion_factura = request.form.get('direccion_factura', '')

        # Si no se envió ruc, tomar el RUC del paciente; si tampoco existe, usar la cédula
        if not ruc_factura:
            ruc_factura = (consulta.paciente.ruc or consulta.paciente.cedula or '').strip()

        # Nombre para la factura: preferir razón social, sino nombre completo
        if not nombre_factura:
            nombre_factura = (consulta.paciente.razon_social or consulta.paciente.nombre_completo)

        # Dirección: preferir dirección de facturación del paciente, sino su dirección
        if not direccion_factura:
            direccion_factura = (consulta.paciente.direccion_facturacion or consulta.paciente.direccion or '')
        
        # Calcular totales
        paciente = consulta.paciente
        especialidad = Especialidad.query.get(consulta.especialidad_id)
        precio_consulta = float(especialidad.precio_consulta) if especialidad.precio_consulta else 0
        
        procedimientos = ConsultaProcedimiento.query.filter_by(consulta_id=consulta.id).all()
        total_procedimientos = sum(float(p.precio) for p in procedimientos)
        
        insumos = ConsultaInsumo.query.filter_by(consulta_id=consulta.id).all()
        total_insumos = sum(float(i.subtotal) for i in insumos)
        
        subtotal = precio_consulta + total_procedimientos + total_insumos
        # IVA incluido (Paraguay): el total es la suma de precios, IVA = total/11
        total = subtotal
        iva = total / 11
        subtotal = total - iva  # Gravadas (base imponible)
        
        # Generar número de factura
        config = ConfiguracionConsultorio.get_configuracion()
        numero_factura = config.generar_numero_factura()
        timbrado = config.timbrado if hasattr(config, 'timbrado') else None
        
        # Si existe una venta pendiente, la usamos y la actualizamos; si no, creamos una nueva
        if venta_existente and venta_existente.estado == 'pendiente':
            venta = venta_existente
            # Asignar número de factura real ahora
            venta.numero_factura = numero_factura
            venta.timbrado = timbrado
            venta.ruc_factura = ruc_factura
            venta.nombre_factura = nombre_factura
            venta.direccion_factura = direccion_factura
            venta.caja_id = caja.id
            venta.paciente_id = consulta.paciente_id
            venta.subtotal = subtotal
            venta.iva = iva
            venta.total = total
            venta.estado = 'pagada'
            venta.usuario_registro_id = current_user.id
            venta.observaciones = observaciones
            # eliminar detalles anteriores (si los tuvo) para re-generar
            VentaDetalle.query.filter_by(venta_id=venta.id).delete()
            db.session.flush()
            try:
                current_app.logger.debug(f"[procesar_factura] Prepared venta (existing) id={venta.id} estado={venta.estado} numero_factura={venta.numero_factura}")
            except Exception:
                pass
        else:
            # Crear venta nueva
            venta = Venta(
                numero_factura=numero_factura,
                timbrado=timbrado,
                ruc_factura=ruc_factura,
                nombre_factura=nombre_factura,
                direccion_factura=direccion_factura,
                caja_id=caja.id,
                consulta_id=consulta.id,
                paciente_id=consulta.paciente_id,
                subtotal=subtotal,
                iva=iva,
                total=total,
                estado='pagada',  # Ya está pagada
                usuario_registro_id=current_user.id,
                observaciones=observaciones
            )
            db.session.add(venta)
            db.session.flush()
        
        # Agregar detalle de consulta
        detalle = VentaDetalle(
            venta_id=venta.id,
            concepto=f"Consulta - {especialidad.nombre}",
            descripcion=f"Médico: {consulta.medico.nombre_completo if consulta.medico else ''}",
            cantidad=1,
            precio_unitario=precio_consulta,
            subtotal=precio_consulta,
            tipo_item='consulta'
        )
        db.session.add(detalle)
        
        # Agregar detalles de procedimientos
        for proc in procedimientos:
            detalle = VentaDetalle(
                venta_id=venta.id,
                concepto=proc.procedimiento_rel.nombre,
                descripcion=proc.observaciones,
                cantidad=1,
                precio_unitario=float(proc.precio),
                subtotal=float(proc.precio),
                tipo_item='procedimiento',
                item_id=proc.procedimiento_id
            )
            db.session.add(detalle)
        
        # Agregar detalles de insumos y actualizar stock
        for insumo_usado in insumos:
            detalle = VentaDetalle(
                venta_id=venta.id,
                concepto=insumo_usado.insumo_rel.nombre,
                descripcion=f"{insumo_usado.insumo_rel.unidad_medida}",
                cantidad=insumo_usado.cantidad,
                precio_unitario=float(insumo_usado.precio_unitario),
                subtotal=float(insumo_usado.subtotal),
                tipo_item='insumo',
                item_id=insumo_usado.insumo_id
            )
            db.session.add(detalle)
            
            # Actualizar stock
            insumo = Insumo.query.get(insumo_usado.insumo_id)
            if insumo:
                insumo.cantidad_actual -= insumo_usado.cantidad
                
                # Registrar movimiento
                movimiento = MovimientoInsumo(
                    insumo_id=insumo.id,
                    tipo='salida',
                    cantidad=insumo_usado.cantidad,
                    motivo=f"Venta #{numero_factura} - Consulta",
                    usuario_id=current_user.id,
                    fecha=datetime.utcnow()
                )
                db.session.add(movimiento)
        
        # Registrar pagos
        # Backwards-compatible: accept pagos via JSON (pagos_json) or the older fixed fields
        pagos_json = request.form.get('pagos_json')
        pagos_list = []

        if pagos_json:
            try:
                pagos_list = json.loads(pagos_json)
            except Exception:
                pagos_list = []

        # If no pagos_json provided, fall back to the three fields (efectivo/debito/credito)
        if not pagos_list:
            if monto_efectivo > 0:
                forma_efectivo = FormaPago.query.filter_by(nombre='efectivo').first()
                if forma_efectivo:
                    pagos_list.append({
                        'forma_pago_id': forma_efectivo.id,
                        'monto': monto_efectivo,
                        'referencia': ''
                    })

            if monto_debito > 0:
                forma_debito = FormaPago.query.filter_by(nombre='tarjeta_debito').first()
                if forma_debito:
                    pagos_list.append({
                        'forma_pago_id': forma_debito.id,
                        'monto': monto_debito,
                        'referencia': referencia_debito or ''
                    })

            if monto_credito > 0:
                forma_credito = FormaPago.query.filter_by(nombre='tarjeta_credito').first()
                if forma_credito:
                    pagos_list.append({
                        'forma_pago_id': forma_credito.id,
                        'monto': monto_credito,
                        'referencia': referencia_credito or ''
                    })

        # Now persist each pago in pagos_list
        # Primero calcular el total pagado y validar
        total_pagado = sum(float(p.get('monto', 0)) for p in pagos_list)
        
        if total_pagado < total:
            flash('El monto recibido no cubre el total de la factura', 'error')
            return redirect(url_for('facturacion.nueva_venta_desde_consulta', consulta_id=consulta_id))
        
        # Ahora sí persistir los pagos
        for pago_item in pagos_list:
            try:
                forma_id = int(pago_item.get('forma_pago_id')) if pago_item.get('forma_pago_id') else None
                monto = float(pago_item.get('monto') or 0)
                referencia = pago_item.get('referencia', '')
            except Exception:
                continue

            if monto <= 0 or not forma_id:
                continue

            pago = Pago(
                venta_id=venta.id,
                forma_pago_id=forma_id,
                monto=monto,
                referencia=referencia,
                estado='confirmado',
                usuario_registro_id=current_user.id
            )
            db.session.add(pago)
        
    # Nota: no usamos un campo persistente `total_vendido` en la tabla `cajas`.
    # El total vendido se calcula cuando se consulta el estado de la caja sumando las ventas pagadas.
    # (Evitar asignar atributo no persistente en el objeto `caja`.)
        
        try:
            try:
                current_app.logger.debug(f"[procesar_factura] About to commit venta id={venta.id if 'venta' in locals() else 'n/a'} pagos_count={len(pagos_list) if 'pagos_list' in locals() else 'n/a'} total={total if 'total' in locals() else 'n/a'}")
            except Exception:
                pass

            db.session.commit()
            
            # Auditar creación/actualización de venta
            audit('crear', 'ventas', venta.id, descripcion=f'Venta #{venta.numero_factura} - Total: {venta.total}')

            try:
                current_app.logger.debug(f"[procesar_factura] Commit successful for venta id={venta.id}")
            except Exception:
                pass

            # Post-commit verification: read fresh from DB and log state
            try:
                venta_after = Venta.query.get(venta.id)
                current_app.logger.debug(f"[procesar_factura] After commit venta id={getattr(venta_after, 'id', 'n/a')} estado={getattr(venta_after, 'estado', 'n/a')} numero_factura={getattr(venta_after, 'numero_factura', 'n/a')}")
                print(f"[procesar_factura] After commit venta id={getattr(venta_after, 'id', 'n/a')} estado={getattr(venta_after, 'estado', 'n/a')} numero_factura={getattr(venta_after, 'numero_factura', 'n/a')}")
            except Exception as e_read:
                try:
                    current_app.logger.error(f"[procesar_factura] Error reading venta after commit: {e_read}")
                except Exception:
                    pass
                print(f"[procesar_factura] Error reading venta after commit: {e_read}")

            flash(f'Factura #{numero_factura} generada exitosamente', 'success')
            # Retornar JSON con el ID de la venta para descarga automática del ticket
            return jsonify({
                'success': True,
                'venta_id': venta.id,
                'numero_factura': numero_factura,
                'message': 'Factura generada exitosamente'
            }), 200
        except Exception as e_commit:
            # Log commit exception with traceback and print so it's visible in console
            try:
                tb_commit = traceback.format_exc()
                current_app.logger.error(f"[procesar_factura] Commit exception: {e_commit}\n{tb_commit}")
            except Exception:
                pass
            print(f"[procesar_factura] Commit exception: {e_commit}")
            try:
                print(traceback.format_exc())
            except Exception:
                pass
            db.session.rollback()
            flash(f'Error al procesar la factura: {str(e_commit)}', 'error')
            return redirect(url_for('facturacion.nueva_venta_desde_consulta', consulta_id=consulta_id))
        
    except Exception as e:
        # Log exception with traceback to help debugging why commit/updates may be rolled back
        try:
            tb = traceback.format_exc()
            current_app.logger.error(f"[procesar_factura] Exception: {e}\n{tb}")
        except Exception:
            pass
        db.session.rollback()
        flash(f'Error al procesar la factura: {str(e)}', 'error')
        return redirect(url_for('facturacion.nueva_venta_desde_consulta', consulta_id=consulta_id))

@bp.route('/ventas/<int:id>/pagar', methods=['GET', 'POST'])
@login_required
def procesar_pago(id):
    """Procesar pago de venta"""
    venta = Venta.query.get_or_404(id)
    
    if request.method == 'POST':
        forma_pago_id = request.form.get('forma_pago_id')
        monto = float(request.form.get('monto'))
        referencia = request.form.get('referencia', '')
        
        # Registrar pago
        pago = Pago(
            venta_id=venta.id,
            forma_pago_id=forma_pago_id,
            monto=monto,
            referencia=referencia,
            usuario_registro_id=current_user.id
        )
        
        db.session.add(pago)
        
        # Si el pago cubre el total, marcar venta como pagada
        total_pagado = sum(float(p.monto) for p in venta.pagos) + monto
        if total_pagado >= float(venta.total):
            venta.estado = 'pagada'
        
        db.session.commit()
        
        flash('Pago registrado exitosamente', 'success')
        return redirect(url_for('facturacion.ver_venta', id=venta.id))
    
    # GET
    formas_pago = FormaPago.query.filter_by(activo=True).all()
    
    return render_template('facturacion/procesar_pago.html',
                         venta=venta,
                         formas_pago=formas_pago)

@bp.route('/ventas/<int:id>')
@login_required
def ver_venta(id):
    """Ver detalle de venta/factura"""
    venta = Venta.query.get_or_404(id)
    return render_template('facturacion/ver_venta.html', venta=venta)

# Alias para compatibilidad
ver_factura = ver_venta

@bp.route('/reportes/ventas')
@login_required
def reporte_ventas():
    """Reporte de ventas con listado de arqueos de cajas cerradas"""
    fecha_desde = request.args.get('desde', date.today().isoformat())
    fecha_hasta = request.args.get('hasta', date.today().isoformat())
    
    # Convertir fechas
    fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
    fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    
    # Consultar ventas
    ventas = Venta.query.filter(
        Venta.fecha >= fecha_desde_dt,
        Venta.fecha <= fecha_hasta_dt
    ).all()
    
    # Consultar cajas cerradas en el rango de fechas
    cajas_cerradas = Caja.query.filter(
        Caja.estado == 'cerrada',
        Caja.fecha_cierre >= fecha_desde_dt,
        Caja.fecha_cierre <= fecha_hasta_dt
    ).order_by(Caja.fecha_cierre.desc()).all()
    
    total_vendido = sum(float(v.total) for v in ventas if v.estado == 'pagada')
    
    return render_template('facturacion/reporte_ventas.html',
                         ventas=ventas,
                         cajas_cerradas=cajas_cerradas,
                         total_vendido=total_vendido,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)


@bp.route('/ventas/<int:id>/ticket')
@login_required
def descargar_ticket(id):
    """Generar y descargar ticket térmico en PDF"""
    print(f"\n{'='*60}")
    print(f"[TICKET] Iniciando generación de ticket para venta ID: {id}")
    print(f"{'='*60}")
    
    try:
        venta = Venta.query.get_or_404(id)
        print(f"[TICKET] Venta encontrada: {venta.numero_factura}")
        print(f"[TICKET] Estado: {venta.estado}")
        print(f"[TICKET] Total: {venta.total}")
        print(f"[TICKET] Detalles: {len(venta.detalles)} items")
        print(f"[TICKET] Pagos: {len(venta.pagos)} formas de pago")
        
        config = ConfiguracionConsultorio.get_configuracion()
        print(f"[TICKET] Configuración obtenida: {config.nombre}")
        print(f"[TICKET] RUC: {config.ruc}")
        print(f"[TICKET] Timbrado: {config.timbrado}")
        print(f"[TICKET] Logo path: {config.logo_path}")
        
        # Crear buffer para el PDF
        buffer = io.BytesIO()
        print(f"[TICKET] Buffer creado")
        
        # Generar ticket
        print(f"[TICKET] Llamando a generar_ticket_pdf...")
        generar_ticket_pdf(venta, config, buffer)
        print(f"[TICKET] Ticket generado exitosamente!")
        
        # Verificar tamaño del buffer (debería estar en posición 0 después de seek)
        buffer_size = len(buffer.getvalue())
        print(f"[TICKET] Tamaño del buffer: {buffer_size} bytes")
        
        if buffer_size == 0:
            raise Exception("El buffer está vacío, no se generó el PDF correctamente")
        
        # Nombre del archivo
        filename = f'Ticket_{venta.numero_factura.replace("/", "-")}.pdf' if venta.numero_factura else f'Ticket_{id}.pdf'
        print(f"[TICKET] Nombre del archivo: {filename}")
        
        print(f"[TICKET] Enviando archivo al cliente como descarga...")
        print(f"{'='*60}\n")
        
        # Enviar como descarga automática
        response = send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
        # Headers para forzar descarga y evitar caché
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f'[TICKET] PDF enviado como descarga: {filename}')
        return response
        return response
    except Exception as e:
        print(f"\n{'!'*60}")
        print(f"[TICKET ERROR] Error generando ticket: {str(e)}")
        print(f"[TICKET ERROR] Tipo: {type(e).__name__}")
        import traceback
        print(f"[TICKET ERROR] Traceback:")
        traceback.print_exc()
        print(f"{'!'*60}\n")
        flash(f'Error al generar ticket: {str(e)}', 'error')
        return redirect(url_for('facturacion.ver_venta', id=id))


@bp.route('/ventas/<int:id>/confirmar_descarga')
@login_required
def confirmar_y_descargar(id):
    """Página intermedia que descarga el ticket automáticamente y redirige"""
    print(f"\n{'='*60}")
    print(f"[CONFIRMAR] Página de confirmación para venta ID: {id}")
    print(f"[CONFIRMAR] Renderizando confirmar_descarga.html")
    print(f"{'='*60}\n")
    
    venta = Venta.query.get_or_404(id)
    return render_template('facturacion/confirmar_descarga.html', venta=venta)
