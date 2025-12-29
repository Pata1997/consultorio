from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, abort, current_app
from flask_login import login_required, current_user
from app import db
from app.models import (Consulta, Cita, Paciente, Insumo, Procedimiento, Receta, 
                        ConsultaInsumo, ConsultaProcedimiento, OrdenEstudio,
                        InsumoEspecialidad, MovimientoInsumo,
                        ProcedimientoPrecio, Medico, Especialidad, MedicoEspecialidad)
from datetime import datetime
from decimal import Decimal, InvalidOperation
import io
import os

# ReportLab for PDF generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

bp = Blueprint('consultorio', __name__, url_prefix='/consultorio')


def _resolver_precio_procedimiento(procedimiento_id, medico_id=None, especialidad_id=None):
    """
    Resuelve el precio de un procedimiento según la regla de prioridad:
    1) Precio específico para (procedimiento_id, medico_id)
    2) Precio para (procedimiento_id, especialidad_id)
    3) procedimiento.precio (valor por defecto)
    
    Args:
        procedimiento_id: ID del procedimiento
        medico_id: ID del médico (opcional)
        especialidad_id: ID de la especialidad (opcional)
        
    Returns:
        Decimal: Precio resuelto del procedimiento
    """
    # Prioridad 1: Precio específico para médico
    if medico_id:
        precio_medico = ProcedimientoPrecio.query.filter_by(
            procedimiento_id=procedimiento_id,
            medico_id=medico_id
        ).first()
        if precio_medico:
            return precio_medico.precio
    
    # Prioridad 2: Precio para especialidad
    if especialidad_id:
        precio_especialidad = ProcedimientoPrecio.query.filter_by(
            procedimiento_id=procedimiento_id,
            especialidad_id=especialidad_id
        ).first()
        if precio_especialidad:
            return precio_especialidad.precio
    
    # Prioridad 3: Precio base del procedimiento
    procedimiento = Procedimiento.query.get(procedimiento_id)
    if procedimiento:
        return procedimiento.precio
    
    return Decimal('0')


def _resolve_logo_path(config):
    """Try several locations for the clinic logo and return a valid filesystem path or None."""
    # 1) If logo_path is set and exists, use it
    if getattr(config, 'logo_path', None):
        p = config.logo_path
        if os.path.isabs(p) and os.path.exists(p):
            return p
        # maybe it's relative to app root
        abs_p = os.path.join(current_app.root_path, p)
        if os.path.exists(abs_p):
            return abs_p

    # 2) If logo_filename is provided, look in static/uploads
    if getattr(config, 'logo_filename', None):
        filename = config.logo_filename
        # common locations: package static uploads, package static root, project-level uploads, project root
        candidates = [
            os.path.join(current_app.root_path, 'static', 'uploads', filename),
            os.path.join(current_app.root_path, 'static', filename),
        ]
        # project root (one level above package)
        project_root = os.path.abspath(os.path.join(current_app.root_path, '..'))
        candidates.extend([
            os.path.join(project_root, 'uploads', filename),
            os.path.join(project_root, filename),
        ])

        for p in candidates:
            if os.path.exists(p):
                return p

    # 3) Fallback: None
    return None


def _build_membrete_table(config, styles, max_logo_w=50*mm, max_logo_h=30*mm):
    """Return a (header_table, on_page_callback) tuple to render a branded header and footer.
    header_table is a Platypus Table ready to be appended to the story.
    on_page_callback(canvas, doc) will draw the footer (clinic name and page number).
    """
    clinic_name = getattr(config, 'nombre', 'Consultorio Médico')
    clinic_dir = getattr(config, 'direccion', '')
    clinic_tel = getattr(config, 'telefono', '')
    clinic_ruc = getattr(config, 'ruc', '')

    styles_local = styles
    clinic_html = f"<b>{clinic_name}</b><br/><font size=9>{clinic_dir}<br/>Tel: {clinic_tel} &nbsp;&nbsp; RUC: {clinic_ruc}</font>"
    clinic_para = Paragraph(clinic_html, ParagraphStyle('Clinic', parent=styles_local['Normal'], fontSize=10, leading=12, textColor=colors.white))

    logo_path = _resolve_logo_path(config)
    logo_elem = None
    if logo_path:
        try:
            img_reader = ImageReader(logo_path)
            iw, ih = img_reader.getSize()
            ratio = min((max_logo_w) / float(iw), (max_logo_h) / float(ih))
            if ratio <= 0 or ratio > 10:
                ratio = min(max_logo_w / float(iw if iw else 1), max_logo_h / float(ih if ih else 1))
            w = iw * ratio
            h = ih * ratio
            logo_elem = RLImage(logo_path, width=w, height=h)
        except Exception:
            logo_elem = None

    if logo_elem:
        header_table = Table([[logo_elem, clinic_para]], colWidths=[(max_logo_w + 6), None])
    else:
        header_table = Table([[clinic_para]], colWidths=[None])

    # Modern palette: softer primary blue and roomy paddings
    primary_color = colors.HexColor('#1e88e5')
    light_band = colors.HexColor('#eaf5ff')
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    if logo_elem:
        header_table.setStyle(TableStyle([('TEXTCOLOR', (1,0), (1,0), colors.white)]))

    def _on_page(canvas_obj, doc_obj):
        # Draw subtle watermark (centered clinic logo) and footer band
        canvas_obj.saveState()
        page_w, page_h = doc_obj.pagesize

        # Watermark: centered, very low opacity
        if logo_elem and logo_path:
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                # target width approx 120mm
                tgt_w = 120 * mm
                ratio = min(tgt_w / float(iw), (page_h * 0.5) / float(ih))
                w = iw * ratio
                h = ih * ratio
                x = (page_w - w) / 2.0
                y = (page_h - h) / 2.0
                # Try to set transparency if available
                try:
                    canvas_obj.setFillAlpha(0.06)
                except Exception:
                    pass
                try:
                    canvas_obj.drawImage(img, x, y, width=w, height=h, mask='auto')
                except Exception:
                    # fallback: ignore watermark if drawing fails
                    pass
                try:
                    canvas_obj.setFillAlpha(1.0)
                except Exception:
                    pass
            except Exception:
                # ignore watermark errors
                pass

        # Decorative bottom band (light) and footer text
        band_h = 14 * mm
        try:
            canvas_obj.setFillColor(light_band)
            canvas_obj.rect(0, 0, page_w, band_h, stroke=0, fill=1)
        except Exception:
            pass

        # Footer text and page number above the band
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.grey)
        footer_text = clinic_name
        canvas_obj.drawString(doc_obj.leftMargin, band_h - 6*mm, footer_text)
        canvas_obj.drawRightString(page_w - doc_obj.rightMargin, band_h - 6*mm, f'Página {canvas_obj.getPageNumber()}')
        canvas_obj.restoreState()

    return header_table, _on_page


@bp.route('/consultas')
@login_required
def listar_consultas():
    """Listar consultas con filtros"""
    from datetime import datetime
    
    # Query base según rol
    if current_user.rol == 'medico' and current_user.medico:
        query = Consulta.query.filter_by(medico_id=current_user.medico.id)
    else:
        query = Consulta.query
    
    # Obtener parámetros de búsqueda
    paciente_buscar = request.args.get('paciente', '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()
    
    # Filtro por paciente (búsqueda aproximada por nombre o cédula)
    if paciente_buscar:
        query = query.join(Paciente).filter(
            db.or_(
                Paciente.nombre.ilike(f'%{paciente_buscar}%'),
                Paciente.apellido.ilike(f'%{paciente_buscar}%'),
                Paciente.cedula.ilike(f'%{paciente_buscar}%')
            )
        )
    
    # Filtro por rango de fechas
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d')
            query = query.filter(Consulta.fecha >= fecha_desde_obj)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            # Agregar 1 día para incluir todo el día hasta
            from datetime import timedelta
            fecha_hasta_obj = fecha_hasta_obj + timedelta(days=1)
            query = query.filter(Consulta.fecha < fecha_hasta_obj)
        except ValueError:
            pass
    
    # Ordenar y limitar resultados
    if paciente_buscar or fecha_desde or fecha_hasta:
        # Si hay filtros, no limitar resultados
        consultas = query.order_by(Consulta.fecha.desc()).all()
    else:
        # Sin filtros, mostrar solo las últimas 50
        consultas = query.order_by(Consulta.fecha.desc()).limit(50).all()
    
    return render_template('consultorio/listar_consultas.html', 
                         consultas=consultas,
                         paciente_buscar=paciente_buscar,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

@bp.route('/consultas/nueva/<int:cita_id>', methods=['GET', 'POST'])
@login_required
def nueva_consulta(cita_id):
    """Crear nueva consulta desde una cita"""
    cita = Cita.query.get_or_404(cita_id)
    
    # Verificar que sea el médico de la cita
    if current_user.rol == 'medico' and current_user.medico:
        if cita.medico_id != current_user.medico.id:
            flash('No tiene permiso para atender esta cita', 'danger')
            return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Helpers para parsear campos numéricos opcionales ('' -> None)
        def _get_optional_decimal(key):
            raw = request.form.get(key, '')
            if raw is None:
                return None
            raw = str(raw).strip()
            if raw == '':
                return None
            # Normalizar usando helper para aceptar separadores de miles y coma decimal
            from app.utils.number_utils import parse_decimal_from_form
            return parse_decimal_from_form(raw)

        def _get_optional_int(key):
            raw = request.form.get(key, '')
            if raw is None:
                return None
            raw = str(raw).strip()
            if raw == '':
                return None
            try:
                return int(raw)
            except ValueError:
                return None

        # Crear consulta (convertir valores vacíos a None para campos numéricos)
        consulta = Consulta(
            cita_id=cita.id,
            paciente_id=cita.paciente_id,
            medico_id=cita.medico_id,
            especialidad_id=cita.especialidad_id,
            motivo=request.form.get('motivo'),
            diagnostico=request.form.get('diagnostico'),
            observaciones=request.form.get('observaciones'),
            presion_arterial=request.form.get('presion_arterial'),
            temperatura=_get_optional_decimal('temperatura'),
            pulso=_get_optional_int('pulso'),
            peso=_get_optional_decimal('peso'),
            altura=_get_optional_decimal('altura')
        )
        
        db.session.add(consulta)
        db.session.flush()  # Para obtener el ID de la consulta
        
        # Procesar receta (texto libre)
        receta_texto = request.form.get('receta_texto', '').strip()
        if receta_texto:
            receta = Receta(
                consulta_id=consulta.id,
                medicamento='Receta Médica Completa',
                dosis='Ver indicaciones',
                frecuencia='Ver indicaciones',
                duracion='Ver indicaciones',
                indicaciones=receta_texto
            )
            db.session.add(receta)
        
        # Procesar orden de estudios (texto libre)
        orden_texto = request.form.get('orden_texto', '').strip()
        if orden_texto:
            orden = OrdenEstudio(
                consulta_id=consulta.id,
                tipo='estudios',
                descripcion=orden_texto
            )
            db.session.add(orden)
        
        # Procesar insumos utilizados
        insumo_ids = request.form.getlist('insumo_id[]')
        cantidades = request.form.getlist('insumo_cantidad[]')
        
        for i in range(len(insumo_ids)):
            if not insumo_ids[i]:
                continue
            try:
                insumo_id = int(insumo_ids[i])
            except (ValueError, TypeError):
                continue
            insumo = Insumo.query.get(insumo_id)
            if not insumo:
                continue
            # validar cantidad
            try:
                cantidad = int(cantidades[i])
            except (ValueError, TypeError):
                # si la cantidad está vacía o inválida, saltar
                continue
            
            # Registrar uso de insumo
            consulta_insumo = ConsultaInsumo(
                consulta_id=consulta.id,
                insumo_id=insumo.id,
                cantidad=cantidad,
                precio_unitario=insumo.precio_unitario,
                subtotal=insumo.precio_unitario * cantidad
            )
            db.session.add(consulta_insumo)
            
            # Actualizar stock
            insumo.cantidad_actual -= cantidad
            
            # Registrar movimiento
            movimiento = MovimientoInsumo(
                insumo_id=insumo.id,
                tipo='salida',
                cantidad=-cantidad,
                motivo='Uso en consulta',
                consulta_id=consulta.id,
                usuario_id=current_user.id
            )
            db.session.add(movimiento)
        
        # Procesar procedimientos
        procedimiento_ids = request.form.getlist('procedimientos[]')
        
        for proc_id in procedimiento_ids:
            if proc_id:
                procedimiento = Procedimiento.query.get(int(proc_id))
                if procedimiento:
                    # Resolver precio según regla de prioridad: médico > especialidad > base
                    precio_resuelto = _resolver_precio_procedimiento(
                        procedimiento_id=procedimiento.id,
                        medico_id=consulta.medico_id,
                        especialidad_id=consulta.especialidad_id
                    )
                    
                    consulta_proc = ConsultaProcedimiento(
                        consulta_id=consulta.id,
                        procedimiento_id=procedimiento.id,
                        precio=precio_resuelto
                    )
                    db.session.add(consulta_proc)
        
        # Actualizar estado de la cita a atendida
        cita.estado = 'atendida'
        
        db.session.commit()

        # Crear/actualizar venta pendiente para que la cajera la facture
        try:
            # ConsultaProcedimiento y ConsultaInsumo ya están importados al inicio del módulo
            # Solo importar los modelos que no están importados aún
            from app.models import Caja, Venta, VentaDetalle, ConfiguracionConsultorio

            # Crear una venta pendiente para que la cajera la facture.
            # Si ya existe una venta vinculada a esta consulta, no crear otra.
            venta_existente_check = Venta.query.filter_by(consulta_id=consulta.id).first()
            if not venta_existente_check:
                # Buscar una caja abierta (cualquiera) — si existe, la asociamos, sino queda sin caja
                caja = Caja.query.filter_by(estado='abierta').first()
                paciente = cita.paciente

                # Calcular totales (sin impuestos aún)
                especialidad = consulta.especialidad if consulta.especialidad else None
                precio_consulta = float(especialidad.precio_consulta) if especialidad and especialidad.precio_consulta else 0

                procedimientos = ConsultaProcedimiento.query.filter_by(consulta_id=consulta.id).all()
                total_procedimientos = sum(float(p.precio) for p in procedimientos)

                insumos = ConsultaInsumo.query.filter_by(consulta_id=consulta.id).all()
                total_insumos = sum(float(i.subtotal) for i in insumos)

                subtotal = precio_consulta + total_procedimientos + total_insumos
                # IVA incluido (Paraguay): total es la suma de precios, IVA = total/11
                total = subtotal
                iva = total / 11
                subtotal = total - iva  # Gravadas (base imponible)

                # Generar número provisional único para la venta pendiente
                import time
                numero_provisional = f"PEND-{consulta.id}-{int(time.time())}"

                venta = Venta(
                    numero_factura=numero_provisional,
                    timbrado=None,
                    # Usar RUC si existe para facturación, sino usar cédula
                    ruc_factura=paciente.ruc or paciente.cedula or '',
                    # Si tiene razón social usarla, sino nombre completo
                    nombre_factura=paciente.razon_social or paciente.nombre_completo,
                    direccion_facturacion=paciente.direccion_facturacion or paciente.direccion or '',
                    caja_id=(caja.id if caja else None),
                    consulta_id=consulta.id,
                    paciente_id=consulta.paciente_id,
                    fecha=datetime.utcnow(),
                    subtotal=subtotal,
                    iva=iva,
                    total=total,
                    estado='pendiente',
                    usuario_registro_id=current_user.id,
                    observaciones='Venta generada automáticamente desde consulta'
                )
                db.session.add(venta)
                db.session.flush()

                # Agregar detalle de consulta
                detalle = VentaDetalle(
                    venta_id=venta.id,
                    concepto=f"Consulta - {especialidad.nombre if especialidad else ''}",
                    descripcion=f"Médico: {consulta.medico.nombre_completo if consulta.medico else ''}",
                    cantidad=1,
                    precio_unitario=precio_consulta,
                    subtotal=precio_consulta,
                    tipo_item='consulta'
                )
                db.session.add(detalle)

                # Detalles por procedimientos
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

                # Detalles por insumos (no descontar stock aquí, ya se descontó en la consulta)
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

                db.session.commit()
        except Exception as e:
            # No bloquear el flujo si falla la creación de la venta pendiente
            current_app.logger.error(f"[nueva_consulta] Error al crear venta pendiente: {str(e)}")
            current_app.logger.exception(e)
            db.session.rollback()

        flash('Consulta registrada exitosamente', 'success')
        return redirect(url_for('consultorio.ver_consulta', id=consulta.id))
    
    # GET - cargar datos para el formulario
    paciente = cita.paciente
    
    # Obtener historial del paciente (TODAS las consultas previas de TODOS los doctores)
    consultas_previas = Consulta.query.filter_by(paciente_id=paciente.id)\
        .order_by(Consulta.fecha.desc()).limit(5).all()
    
    # Obtener TODOS los insumos activos con stock disponible
    # (no solo los de la especialidad, para mayor flexibilidad)
    insumos_disponibles = Insumo.query.filter_by(activo=True)\
        .filter(Insumo.cantidad_actual > 0)\
        .order_by(Insumo.nombre).all()
    
    # Obtener procedimientos de la especialidad
    procedimientos_disponibles = Procedimiento.query.filter_by(
        especialidad_id=cita.especialidad_id,
        activo=True
    ).all()
    
    return render_template('consultorio/nueva_consulta.html',
                         cita=cita,
                         consultas_previas=consultas_previas,
                         insumos_disponibles=insumos_disponibles,
                         procedimientos_disponibles=procedimientos_disponibles)

@bp.route('/consultas/<int:id>')
@login_required
def ver_consulta(id):
    """Ver detalle de consulta"""
    consulta = Consulta.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'medico' and current_user.medico:
        if consulta.medico_id != current_user.medico.id:
            flash('No tiene permiso para ver esta consulta', 'danger')
            return redirect(url_for('main.index'))
    
    return render_template('consultorio/ver_consulta.html', consulta=consulta)


@bp.route('/consultas/<int:consulta_id>/receta_pdf/<int:receta_id>')
@login_required
def receta_pdf(consulta_id, receta_id):
    """Generar PDF de la Receta Médica usando ReportLab"""
    consulta = Consulta.query.get_or_404(consulta_id)
    # permisos
    if current_user.rol == 'medico' and current_user.medico:
        if consulta.medico_id != current_user.medico.id:
            abort(403)

    receta = Receta.query.filter_by(id=receta_id, consulta_id=consulta_id).first_or_404()

    # Obtener configuración/membrete
    from app.models import ConfiguracionConsultorio
    config = ConfiguracionConsultorio.get_configuracion()

    # Generar PDF en memoria usando Platypus para un layout más pulido
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=25*mm, rightMargin=25*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.leading = 14
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=16, leading=18)
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, leading=12)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=14)

    story = []

    # Timestamp para usar en la tabla
    timestamp = consulta.fecha.strftime('%d/%m/%Y')

    # Membrete compacto (igual que arqueo)
    logo_path = _resolve_logo_path(config)
    logo_elem = None
    if logo_path:
        try:
            logo_elem = RLImage(logo_path, width=0.6*inch, height=0.6*inch)
        except Exception:
            logo_elem = None

    # Info consultorio compacta
    clinic_html = f"<b><font size=10>{config.nombre or 'Consultorio Médico'}</font></b><br/><font size=7>{config.direccion or ''}<br/>Tel: {config.telefono or 'N/A'} | Email: {config.email or 'N/A'}<br/>RUC: {config.ruc or ''}</font>"
    clinic_para = Paragraph(clinic_html, ParagraphStyle('Clinic', parent=styles['Normal'], fontSize=10, leading=10))

    # Tabla membrete
    if logo_elem:
        header_table = Table([[logo_elem, clinic_para]], colWidths=[0.8*inch, 5*inch])
    else:
        header_table = Table([[clinic_para]], colWidths=[6.5*inch])

    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (1,0), (1,0), 'LEFT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))

    # Título compacto
    story.append(Paragraph('RECETA MÉDICA', ParagraphStyle('TituloCompacto', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=4)))
    story.append(Spacer(1, 0.1*inch))
    
    # Línea separadora
    line_table = Table([['_' * 100]], colWidths=[6.5*inch])
    story.append(line_table)
    story.append(Spacer(1, 0.1*inch))

    # Patient / doctor info (tabla compacta)
    try:
        paciente_nombre = consulta.paciente.nombre_completo
        paciente_cedula = consulta.paciente.cedula or ''
    except Exception:
        paciente_nombre = ''
        paciente_cedula = ''
    medico_nombre = consulta.medico.nombre_completo if consulta.medico else ''
    reg_prof = consulta.medico.registro_profesional if consulta.medico else ''
    
    info_table = Table([
        [Paragraph('<b>Médico:</b>', header_style), Paragraph(medico_nombre, body_style), 
         Paragraph('<b>Reg. Prof.:</b>', header_style), Paragraph(reg_prof, body_style)],
        [Paragraph('<b>Paciente:</b>', header_style), Paragraph(paciente_nombre, body_style),
         Paragraph('<b>Fecha:</b>', header_style), Paragraph(timestamp, body_style)],
    ], colWidths=[1*inch, 2.5*inch, 1*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTNAME', (3,0), (3,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.15*inch))

    # Body
    text = receta.indicaciones or ''
    # Convert plain newlines to <br/> for Paragraph
    safe_text = '<br/>'.join([line for line in text.splitlines()])
    story.append(Paragraph(safe_text, body_style))
    story.append(Spacer(1, 18))

    # Signature area on the right
    sig_table = Table([
        ['', '______________________________'],
        ['', f'{medico_nombre}']
    ], colWidths=[None, 70*mm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    # Date above signature
    story.append(Paragraph(f"Fecha: {consulta.fecha.strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('date', parent=styles['Normal'], fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 8))
    story.append(sig_table)

    # Footer with page number and small text
    def _on_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.grey)
        footer_text = config.nombre or ''
        canvas_obj.drawString(doc_obj.leftMargin, 10*mm, footer_text)
        # page number on right
        canvas_obj.drawRightString(doc_obj.pagesize[0] - doc_obj.rightMargin, 10*mm, f'Página {canvas_obj.getPageNumber()}')
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f'Receta_{consulta.id}.pdf')


@bp.route('/consultas/<int:consulta_id>/orden_pdf/<int:orden_id>')
@login_required
def orden_pdf(consulta_id, orden_id):
    """Generar PDF de la Orden de Estudios usando ReportLab"""
    consulta = Consulta.query.get_or_404(consulta_id)
    if current_user.rol == 'medico' and current_user.medico:
        if consulta.medico_id != current_user.medico.id:
            abort(403)

    orden = OrdenEstudio.query.filter_by(id=orden_id, consulta_id=consulta_id).first_or_404()

    from app.models import ConfiguracionConsultorio
    config = ConfiguracionConsultorio.get_configuracion()

    # Generar PDF con Platypus para un diseño consistente con la receta
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=25*mm, rightMargin=25*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.leading = 14
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=16, leading=18)
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, leading=12)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=14)

    story = []

    # Timestamp (small)
    timestamp = consulta.fecha.strftime('%d/%m/%Y, %H:%M')
    story.append(Paragraph(f'<font size=8 color="#444444">{timestamp}</font>', ParagraphStyle('ts', parent=styles['Normal'], alignment=TA_LEFT)))
    story.append(Spacer(1, 6))

    # Clinic header (re-use same styling as receta)
    logo_path = _resolve_logo_path(config)
    logo_elem = None
    max_logo_w = 50 * mm
    max_logo_h = 30 * mm
    if logo_path:
        try:
            img_reader = ImageReader(logo_path)
            iw, ih = img_reader.getSize()
            ratio = min((max_logo_w) / float(iw), (max_logo_h) / float(ih))
            if ratio <= 0 or ratio > 10:
                ratio = min(max_logo_w / float(iw if iw else 1), max_logo_h / float(ih if ih else 1))
            w = iw * ratio
            h = ih * ratio
            logo_elem = RLImage(logo_path, width=w, height=h)
        except Exception:
            logo_elem = None

    clinic_html = f"<b>{config.nombre or 'Consultorio Médico'}</b><br/><font size=9>{(config.direccion or '')}<br/>Tel: {config.telefono or ''} &nbsp;&nbsp; RUC: {config.ruc or ''}</font>"
    clinic_para = Paragraph(clinic_html, ParagraphStyle('Clinic', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.white))

    if logo_elem:
        header_table = Table([[logo_elem, clinic_para]], colWidths=[(max_logo_w + 6), None])
    else:
        header_table = Table([[clinic_para]], colWidths=[None])

    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0b5ed7')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    if logo_elem:
        header_table.setStyle(TableStyle([('TEXTCOLOR', (1,0), (1,0), colors.white)]))

    story.append(header_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph('ORDEN DE ESTUDIOS', ParagraphStyle('TitleCenter', parent=styles['Heading2'], alignment=TA_CENTER, fontSize=20, leading=22, spaceAfter=6)))
    story.append(Spacer(1, 6))

    try:
        paciente_nombre = consulta.paciente.nombre_completo
        paciente_cedula = consulta.paciente.cedula or ''
    except Exception:
        paciente_nombre = ''
        paciente_cedula = ''
    medico_nombre = consulta.medico.nombre_completo if consulta.medico else ''
    especialidad = consulta.especialidad.nombre if consulta.especialidad else ''

    info_table = Table([
        [Paragraph('<b>Paciente:</b>', header_style), Paragraph(paciente_nombre, body_style)],
        [Paragraph('<b>Cédula:</b>', header_style), Paragraph(paciente_cedula, body_style)],
        [Paragraph('<b>Médico:</b>', header_style), Paragraph(medico_nombre, body_style)],
        [Paragraph('<b>Especialidad:</b>', header_style), Paragraph(especialidad, body_style)]
    ], colWidths=[30*mm, None])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    text = orden.descripcion or ''
    safe_text = '<br/>'.join([line for line in text.splitlines()])
    story.append(Paragraph(safe_text, body_style))
    story.append(Spacer(1, 18))

    # Signature similar to receta
    sig_table = Table([
        ['', '______________________________'],
        ['', f'{medico_nombre}']
    ], colWidths=[None, 70*mm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    story.append(Paragraph(f"Fecha: {consulta.fecha.strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('date', parent=styles['Normal'], fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 8))
    story.append(sig_table)

    def _on_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.grey)
        footer_text = config.nombre or ''
        canvas_obj.drawString(doc_obj.leftMargin, 10*mm, footer_text)
        canvas_obj.drawRightString(doc_obj.pagesize[0] - doc_obj.rightMargin, 10*mm, f'Página {canvas_obj.getPageNumber()}')
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f'Orden_{consulta.id}.pdf')


@bp.route('/consultas/receta_preview_pdf', methods=['POST'])
@login_required
def receta_preview_pdf():
    """Delegar en la implementación centralizada de `app.pdf_receta.receta_preview_pdf`.
    Esto permite mantener el endpoint en `consultorio` pero usar el módulo independiente.
    """
    try:
        from app.pdf_receta import receta_preview_pdf as _receta_fn
    except Exception:
        # Fallback: informar error de import
        return ('Implementación de PDF no disponible', 500)
    return _receta_fn()


@bp.route('/consultas/orden_preview_pdf', methods=['POST'])
@login_required
def orden_preview_pdf():
    """Delegar en la implementación centralizada de `app.pdf_receta.orden_preview_pdf`.
    Esto mantiene un único diseño compartido con la Receta Médica.
    """
    try:
        from app.pdf_receta import orden_preview_pdf as _orden_fn
    except Exception:
        return ('Implementación de PDF no disponible', 500)
    return _orden_fn()

@bp.route('/pacientes/<int:id>/historial')
@login_required
def historial_paciente(id):
    """Ver historial médico completo del paciente"""
    paciente = Paciente.query.get_or_404(id)
    consultas = Consulta.query.filter_by(paciente_id=id)\
        .order_by(Consulta.fecha.desc()).all()
    
    return render_template('consultorio/historial_paciente.html',
                         paciente=paciente,
                         consultas=consultas)

@bp.route('/insumos')
@login_required
def listar_insumos():
    """Listar insumos y control de stock"""
    # Parámetros de búsqueda
    busqueda = request.args.get('busqueda', '').strip()

    base_q = Insumo.query.filter_by(activo=True)

    if busqueda:
        term = f"%{busqueda}%"
        # Buscar aproximado en código, nombre o categoría
        base_q = base_q.filter(
            db.or_(
                Insumo.codigo.ilike(term),
                Insumo.nombre.ilike(term),
                Insumo.categoria.ilike(term)
            )
        )

    insumos = base_q.order_by(Insumo.nombre).all()

    # Identificar insumos que requieren reposición
    alertas = [i for i in insumos if i.requiere_reposicion]

    return render_template('consultorio/listar_insumos.html',
                         insumos=insumos,
                         alertas=alertas,
                         busqueda=busqueda)


@bp.route('/procedimiento-precios', methods=['GET', 'POST'])
@login_required
def gestionar_precios():
    """Listar y crear precios por procedimiento (admin)"""
    if current_user.rol != 'admin':
        flash('No tiene permiso para acceder a esta sección', 'danger')
        return redirect(url_for('main.index'))

    # Parámetros de búsqueda
    q = request.args.get('q', '').strip()

    # Datos auxiliares
    procedimientos = Procedimiento.query.order_by(Procedimiento.nombre).all()
    medicos = Medico.query.filter_by(activo=True).order_by(Medico.nombre).all()
    especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()

    if request.method == 'POST':
        try:
            procedimiento_id = int(request.form.get('procedimiento_id'))
        except Exception:
            procedimiento_id = None

        medico_id = request.form.get('medico_id')
        especialidad_id = request.form.get('especialidad_id')

        # Normalizar entrada de precio (aceptar separador de miles '.' y decimal ',')
        from app.utils.number_utils import parse_decimal_from_form
        precio_raw = request.form.get('precio', '')
        precio = parse_decimal_from_form(precio_raw)

        if medico_id == '':
            medico_id = None
        else:
            try:
                medico_id = int(medico_id)
            except Exception:
                medico_id = None

        if especialidad_id == '':
            especialidad_id = None
        else:
            try:
                especialidad_id = int(especialidad_id)
            except Exception:
                especialidad_id = None

        # precio ya se normalizó arriba; si falla, precio será None

        if not procedimiento_id or precio is None:
            flash('Debe seleccionar un procedimiento y un precio válido', 'danger')
            return redirect(url_for('consultorio.gestionar_precios'))

        # Si viene precio_id, editar ese registro directamente
        precio_id = request.form.get('precio_id')
        if precio_id:
            try:
                precio_id_int = int(precio_id)
            except Exception:
                precio_id_int = None

            if precio_id_int:
                pp = ProcedimientoPrecio.query.get(precio_id_int)
                if pp:
                    pp.procedimiento_id = procedimiento_id
                    pp.medico_id = medico_id
                    pp.especialidad_id = especialidad_id
                    pp.precio = precio
                    db.session.commit()
                    flash('Precio actualizado correctamente', 'success')
                    return redirect(url_for('consultorio.gestionar_precios'))
                else:
                    flash('Registro de precio no encontrado', 'danger')
                    return redirect(url_for('consultorio.gestionar_precios'))

        # Evitar duplicados exactos (mismo procedimiento + medico/especialidad)
        existing = ProcedimientoPrecio.query.filter_by(
            procedimiento_id=procedimiento_id,
            medico_id=medico_id,
            especialidad_id=especialidad_id
        ).first()

        if existing:
            existing.precio = precio
            db.session.commit()
            flash('Precio actualizado correctamente', 'success')
        else:
            pp = ProcedimientoPrecio(
                procedimiento_id=procedimiento_id,
                medico_id=medico_id,
                especialidad_id=especialidad_id,
                precio=precio
            )
            db.session.add(pp)
            db.session.commit()
            flash('Precio agregado correctamente', 'success')

        return redirect(url_for('consultorio.gestionar_precios'))

    # GET: listar precios existentes (posible filtro por q)
    precios_q = ProcedimientoPrecio.query
    if q:
        term = f"%{q}%"
        # join para buscar por nombres de procedimiento, medico o especialidad
        precios_q = precios_q.join(Procedimiento, Procedimiento.id == ProcedimientoPrecio.procedimiento_id)
        precios_q = precios_q.outerjoin(Medico, Medico.id == ProcedimientoPrecio.medico_id)
        precios_q = precios_q.outerjoin(Especialidad, Especialidad.id == ProcedimientoPrecio.especialidad_id)
        precios_q = precios_q.filter(
            db.or_(
                Procedimiento.nombre.ilike(term),
                Medico.nombre.ilike(term),
                Medico.apellido.ilike(term),
                Especialidad.nombre.ilike(term)
            )
        )

    precios = precios_q.order_by(ProcedimientoPrecio.id.desc()).all()

    return render_template('consultorio/gestionar_precios_procedimientos.html',
                         procedimientos=procedimientos,
                         medicos=medicos,
                         especialidades=especialidades,
                         precios=precios)


@bp.route('/procedimiento-precios/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_precio(id):
    if current_user.rol != 'admin':
        flash('No tiene permiso', 'danger')
        return redirect(url_for('consultorio.gestionar_precios'))

    pp = ProcedimientoPrecio.query.get_or_404(id)
    db.session.delete(pp)
    db.session.commit()
    flash('Precio eliminado', 'success')
    return redirect(url_for('consultorio.gestionar_precios'))

@bp.route('/insumos/<int:id>/movimientos')
@login_required
def movimientos_insumo(id):
    """Ver movimientos de un insumo"""
    insumo = Insumo.query.get_or_404(id)
    movimientos = MovimientoInsumo.query.filter_by(insumo_id=id)\
        .order_by(MovimientoInsumo.fecha.desc()).limit(50).all()
    
    return render_template('consultorio/movimientos_insumo.html',
                         insumo=insumo,
                         movimientos=movimientos)


@bp.route('/insumos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_insumo():
    """Crear un nuevo insumo (solo admin)"""
    if current_user.rol != 'admin':
        flash('No tiene permiso para crear insumos', 'danger')
        return redirect(url_for('consultorio.listar_insumos'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        from app.utils.number_utils import parse_decimal_from_form
        precio_compra = parse_decimal_from_form(request.form.get('precio_compra', '0') or '0') or Decimal('0')
        precio_venta = parse_decimal_from_form(request.form.get('precio_venta', '0') or '0') or Decimal('0')
        try:
            cantidad_actual = int(request.form.get('cantidad_actual', '0') or 0)
        except Exception:
            cantidad_actual = 0
        try:
            stock_minimo = int(request.form.get('stock_minimo', '10') or 10)
        except Exception:
            stock_minimo = 10
        unidad_medida = request.form.get('unidad_medida', 'unidad')
        activo = True if request.form.get('activo') == 'on' else False

        insumo = Insumo(
            nombre=nombre,
            descripcion=descripcion,
            precio_compra=precio_compra,
            precio_venta=precio_venta,
            cantidad_actual=cantidad_actual,
            stock_minimo=stock_minimo,
            unidad_medida=unidad_medida,
            activo=activo
        )
        db.session.add(insumo)
        db.session.commit()
        flash('Insumo creado correctamente', 'success')
        return redirect(url_for('consultorio.listar_insumos'))

    return render_template('consultorio/nuevo_insumo.html')


@bp.route('/insumos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_insumo(id):
    """Editar insumo existente (solo admin)"""
    if current_user.rol != 'admin':
        flash('No tiene permiso para editar insumos', 'danger')
        return redirect(url_for('consultorio.listar_insumos'))

    insumo = Insumo.query.get_or_404(id)

    if request.method == 'POST':
        insumo.nombre = request.form.get('nombre', insumo.nombre).strip()
        insumo.descripcion = request.form.get('descripcion', insumo.descripcion).strip()
        try:
            from app.utils.number_utils import parse_decimal_from_form
            insumo.precio_compra = parse_decimal_from_form(request.form.get('precio_compra', str(insumo.precio_compra)) or str(insumo.precio_compra)) or insumo.precio_compra
        except Exception:
            pass
        try:
            insumo.precio_venta = parse_decimal_from_form(request.form.get('precio_venta', str(insumo.precio_venta)) or str(insumo.precio_venta)) or insumo.precio_venta
        except Exception:
            pass
        try:
            insumo.cantidad_actual = int(request.form.get('cantidad_actual', insumo.cantidad_actual) or insumo.cantidad_actual)
        except Exception:
            pass
        try:
            insumo.stock_minimo = int(request.form.get('stock_minimo', insumo.stock_minimo) or insumo.stock_minimo)
        except Exception:
            pass
        insumo.unidad_medida = request.form.get('unidad_medida', insumo.unidad_medida)
        insumo.activo = True if request.form.get('activo') == 'on' else False

        db.session.commit()
        flash('Insumo actualizado correctamente', 'success')
        return redirect(url_for('consultorio.listar_insumos'))

    return render_template('consultorio/editar_insumo.html', insumo=insumo)


@bp.route('/insumos/<int:id>/ajustar', methods=['GET', 'POST'])
@login_required
def ajustar_stock(id):
    """Ajustar stock de un insumo (solo admin)"""
    if current_user.rol != 'admin':
        flash('No tiene permiso para ajustar stock', 'danger')
        return redirect(url_for('consultorio.listar_insumos'))

    insumo = Insumo.query.get_or_404(id)

    if request.method == 'POST':
        # acción: 'sumar' o 'restar' o 'set'
        accion = request.form.get('accion')
        try:
            cantidad = int(request.form.get('cantidad', '0') or 0)
        except Exception:
            cantidad = 0

        if accion == 'sumar':
            insumo.cantidad_actual += cantidad
        elif accion == 'restar':
            insumo.cantidad_actual = max(0, insumo.cantidad_actual - cantidad)
        elif accion == 'set':
            insumo.cantidad_actual = max(0, cantidad)

        db.session.commit()
        flash('Stock ajustado correctamente', 'success')
        return redirect(url_for('consultorio.listar_insumos'))

    return render_template('consultorio/ajustar_stock.html', insumo=insumo)


@bp.route('/api/especialidad/<int:especialidad_id>/medicos')
@login_required
def api_medicos_por_especialidad(especialidad_id):
    """Devuelve JSON con médicos asociados a una especialidad (solo admin)."""
    if current_user.rol != 'admin':
        return jsonify({'error': 'no autorizado'}), 403

    # Los médicos están relacionados a especialidades mediante la tabla
    # MedicoEspecialidad (muchos a muchos). Buscamos los médicos activos
    medicos = db.session.query(Medico).join(
        MedicoEspecialidad, Medico.id == MedicoEspecialidad.medico_id
    ).filter(
        MedicoEspecialidad.especialidad_id == especialidad_id,
        Medico.activo == True
    ).order_by(Medico.nombre).all()

    data = [{'id': m.id, 'nombre': f"{m.nombre} {m.apellido}"} for m in medicos]
    return jsonify(data)


@bp.route('/api/medico/<int:medico_id>/procedimientos')
@login_required
def api_procedimientos_por_medico(medico_id):
    """Devuelve JSON con procedimientos asociados al médico (por su especialidad).

    Nota: los procedimientos suelen estar ligados a una especialidad. Esta
    función busca la especialidad del médico y devuelve los procedimientos
    activos de esa especialidad.
    """
    if current_user.rol != 'admin':
        return jsonify({'error': 'no autorizado'}), 403

    medico = Medico.query.get_or_404(medico_id)
    # Obtener las especialidades asignadas al médico
    especialidad_ids = [me.especialidad_id for me in medico.especialidades]
    if not especialidad_ids:
        return jsonify([])

    procedimientos = Procedimiento.query.filter(
        Procedimiento.especialidad_id.in_(especialidad_ids),
        Procedimiento.activo == True
    ).order_by(Procedimiento.nombre).all()

    data = [{'id': p.id, 'nombre': p.nombre} for p in procedimientos]
    return jsonify(data)

@bp.route('/mis-citas-hoy')
@login_required
def mis_citas_hoy():
    """Ver mis citas de hoy (solo médicos)"""
    if current_user.rol != 'medico' or not current_user.medico:
        flash('No tiene permiso para acceder a esta sección', 'danger')
        return redirect(url_for('main.index'))
    
    from datetime import date
    hoy = date.today()
    
    citas = Cita.query.filter_by(
        medico_id=current_user.medico.id,
        fecha=hoy
    ).order_by(Cita.hora).all()
    
    return render_template('consultorio/mis_citas_hoy.html', citas=citas, fecha=hoy)

@bp.route('/mis-consultas')
@login_required
def mis_consultas():
    """Ver todas mis consultas (solo médicos)"""
    if current_user.rol != 'medico' or not current_user.medico:
        flash('No tiene permiso para acceder a esta sección', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    consultas = Consulta.query.filter_by(medico_id=current_user.medico.id)\
        .order_by(Consulta.fecha.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('consultorio/mis_consultas.html', consultas=consultas)
