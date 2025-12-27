from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import (Caja, Venta, VentaDetalle, Pago, FormaPago, Consulta,
                        ConsultaInsumo, ConsultaProcedimiento, Especialidad,
                        ConfiguracionConsultorio)
from datetime import datetime, date
import traceback
from sqlalchemy import func
from app.utils.number_utils import parse_decimal_from_form
import json

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
    total_vendido = 0
    if caja_abierta:
        ventas = Venta.query.filter_by(caja_id=caja_abierta.id, estado='pagada').all()
        total_vendido = sum(float(v.total) for v in ventas)
    
    return render_template('facturacion/estado_caja.html',
                         caja=caja_abierta,
                         total_vendido=total_vendido)

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
    
    monto_inicial = parse_decimal_from_form(request.form.get('monto_inicial', '0')) or 0
    try:
        monto_inicial = float(monto_inicial)
    except Exception:
        monto_inicial = 0
    
    caja = Caja(
        monto_inicial=monto_inicial,
        usuario_apertura_id=current_user.id
    )
    
    db.session.add(caja)
    db.session.commit()
    
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
    
    monto_final = parse_decimal_from_form(request.form.get('monto_final', '0')) or 0
    try:
        monto_final = float(monto_final)
    except Exception:
        monto_final = 0

    caja.monto_final = monto_final
    caja.fecha_cierre = datetime.utcnow()
    caja.usuario_cierre_id = current_user.id
    caja.estado = 'cerrada'
    caja.observaciones = request.form.get('observaciones', '')
    
    db.session.commit()
    
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
    
    total_esperado = sum(float(v.total) for v in ventas if v.estado == 'pagada')
    diferencia = float(caja.monto_final or 0) - (float(caja.monto_inicial) + total_esperado)
    
    return render_template('facturacion/arqueo_caja.html',
                         caja=caja,
                         ventas=ventas,
                         formas_pago=formas_pago,
                         total_esperado=total_esperado,
                         diferencia=diferencia)

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
    iva = subtotal * 0.10  # IVA 10% Paraguay
    total = subtotal + iva
    
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
        iva = subtotal * 0.10
        total = subtotal + iva
        
        # Verificar que el pago cubra el total
        total_pagado = monto_efectivo + monto_debito + monto_credito
        if total_pagado < total:
            flash('El monto recibido no cubre el total de la factura', 'error')
            return redirect(url_for('facturacion.nueva_venta_desde_consulta', consulta_id=consulta_id))
        
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
            return redirect(url_for('facturacion.ver_factura', id=venta.id))
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
    """Reporte de ventas"""
    fecha_desde = request.args.get('desde', date.today().isoformat())
    fecha_hasta = request.args.get('hasta', date.today().isoformat())
    
    ventas = Venta.query.filter(
        Venta.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d'),
        Venta.fecha <= datetime.strptime(fecha_hasta, '%Y-%m-%d').replace(hour=23, minute=59)
    ).all()
    
    total_vendido = sum(float(v.total) for v in ventas if v.estado == 'pagada')
    
    return render_template('facturacion/reporte_ventas.html',
                         ventas=ventas,
                         total_vendido=total_vendido,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)
