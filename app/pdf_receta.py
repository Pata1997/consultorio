import io
import os
from datetime import datetime
from flask import request, send_file, current_app
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader


def _resolve_logo_from_config(logo_path=None):
    """
    Resolve a logo path: prefer explicit logo_path, else try ConfiguracionConsultorio entries.
    Returns an absolute filesystem path or None.
    """
    if logo_path:
        if os.path.isabs(logo_path) and os.path.exists(logo_path):
            return logo_path
        alt = os.path.join(current_app.root_path, logo_path)
        if os.path.exists(alt):
            return alt

    try:
        from app.models import ConfiguracionConsultorio
        cfg = ConfiguracionConsultorio.get_configuracion()
        if getattr(cfg, 'logo_path', None):
            p = cfg.logo_path
            if os.path.isabs(p) and os.path.exists(p):
                return p
            alt = os.path.join(current_app.root_path, p)
            if os.path.exists(alt):
                return alt
        filename = getattr(cfg, 'logo_filename', None)
        if filename:
            candidates = [
                os.path.join(current_app.root_path, 'static', 'uploads', filename),
                os.path.join(current_app.root_path, 'static', filename),
            ]
            project_root = os.path.abspath(os.path.join(current_app.root_path, '..'))
            candidates.extend([
                os.path.join(project_root, 'uploads', filename),
                os.path.join(project_root, filename),
            ])
            for c in candidates:
                if os.path.exists(c):
                    return c
    except Exception:
        pass

    return None


def receta_preview_pdf():
    """
    Generate a modern-looking "Receta Médica" PDF preview.

    Accepts JSON or form data with keys:
      - texto (string) : contenido de la receta (multilínea)
      - paciente (string)
      - medico (string)
      - logo_path (optional absolute/relative)
      - watermark_path (optional)
      - contacto_tel, contacto_email, contacto_web (optional)

    Returns: Flask send_file of generated PDF (attachment)
    """
    # Read input
    data = None
    try:
        data = request.get_json(force=False, silent=True) or {}
    except Exception:
        data = {}
    if not data:
        data = request.form.to_dict()

    # Debug prints: show what the request delivered so we can trace missing fields
    try:
        print('\n[receta_preview_pdf] request.form keys:', getattr(request, 'form', None) and dict(request.form))
    except Exception:
        print('[receta_preview_pdf] could not read request.form')
    try:
        print('[receta_preview_pdf] parsed JSON:', data if isinstance(data, dict) else repr(data))
    except Exception:
        print('[receta_preview_pdf] could not print parsed JSON')

    texto = (data.get('texto') or '').strip()
    paciente = (data.get('paciente') or '').strip()
    medico = (data.get('medico') or '').strip()
    logo_path_input = data.get('logo_path')
    watermark_path_input = data.get('watermark_path')
    contacto_tel = data.get('contacto_tel', '')
    contacto_email = data.get('contacto_email', '')
    contacto_web = data.get('contacto_web', '')

    # Resolve assets
    logo_path = _resolve_logo_from_config(logo_path_input)
    watermark_path = None
    if watermark_path_input:
        if os.path.isabs(watermark_path_input) and os.path.exists(watermark_path_input):
            watermark_path = watermark_path_input
        else:
            alt = os.path.join(current_app.root_path, watermark_path_input)
            if os.path.exists(alt):
                watermark_path = alt
    if not watermark_path:
        watermark_path = logo_path

    # (DB enrichment moved below after we extracted fields from payload)

    # Prepare PDF
    buffer = io.BytesIO()
    left_margin = right_margin = 20 * mm
    top_margin = 40 * mm
    bottom_margin = 30 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin
    )

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=20, leading=22, textColor=colors.HexColor('#0b3358'))
    estilo_ts = ParagraphStyle('Timestamp', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#666666'))
    estilo_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=14)
    estilo_footer = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor('#666666'))

    story = []

    # Header (membrete): very light celeste background, clinic name left, logo right
    header_bg = colors.HexColor('#EAF4FB')  # celeste muy claro
    left_para = Paragraph('<b>Consultorio Médico San Rafael</b>', ParagraphStyle('MedicoHeader', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor('#0b3358')))
    right_logo = None
    if logo_path:
        try:
            img_reader = ImageReader(logo_path)
            iw, ih = img_reader.getSize()
            target_h = 20 * mm
            ratio = target_h / float(ih) if ih else 1.0
            w = iw * ratio
            h = ih * ratio
            right_logo = RLImage(logo_path, width=w, height=h)
        except Exception:
            right_logo = None

    if right_logo:
        header_table = Table([[left_para, right_logo]], colWidths=[None, 40*mm])
    else:
        header_table = Table([[left_para]], colWidths=[None])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), header_bg),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # timestamp + title
    timestamp = datetime.utcnow().strftime('%d/%m/%Y %H:%M')
    story.append(Paragraph(timestamp, estilo_ts))
    story.append(Spacer(1, 6))
    story.append(Paragraph('RECETA MÉDICA', estilo_titulo))
    story.append(Spacer(1, 12))

    # Patient block with light background and border
    block_bg = colors.HexColor('#EAF4FB')
    block_border = colors.HexColor('#D0E6F7')
    # helper to try several possible field names (case-insensitive)
    def _get_field(d, *names):
        for n in names:
            if n in d and d[n]:
                return d[n]
        # case-insensitive fallback
        for k, v in d.items():
            if not v:
                continue
            for n in names:
                if k.lower() == n.lower():
                    return v
        return ''

    direccion = _get_field(data, 'direccion', 'direccion_paciente', 'direccion_domicilio', 'direccion_fiscal') or ''
    edad = _get_field(data, 'edad', 'edad_paciente', 'edad_anios', 'age') or ''
    # If edad is missing but fecha_nacimiento is present, attempt to compute age
    if not edad:
        fn = _get_field(data, 'fecha_nacimiento', 'fecha_nac', 'nacimiento') or ''
        if fn:
            from datetime import datetime as _dt
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    bd = _dt.strptime(fn, fmt)
                    today = _dt.utcnow().date()
                    age_years = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
                    edad = str(age_years)
                    break
                except Exception:
                    continue

    motivo = _get_field(data, 'motivo', 'motivo_consulta', 'motivoConsulta', 'diagnostico', 'observaciones', 'motivo_cita', 'motivo_consulta_text') or ''

    # Debug prints: resolved fields and assets
    try:
        print(f"[receta_preview_pdf] paciente: '{paciente}', direccion: '{direccion}', edad: '{edad}', motivo: '{motivo}'")
        print(f"[receta_preview_pdf] logo_path resolved: {logo_path}, watermark_path: {watermark_path}")
    except Exception:
        print('[receta_preview_pdf] error printing resolved fields')

    # If fields are missing, try to enrich them from the database using the paciente string
    # Example paciente string: 'Angel Sanabria - 5233932' -> cedula '5233932'
    try:
        need_enrich = not (direccion or edad or motivo)
    except NameError:
        need_enrich = True

    if need_enrich and paciente:
        try:
            import re, traceback
            cedula = None
            m = re.search(r'-\s*(\d+)$', paciente)
            if m:
                cedula = m.group(1)
            else:
                m2 = re.search(r'\((\d+)\)', paciente)
                if m2:
                    cedula = m2.group(1)

            # Also respect explicit ids passed in data
            paciente_id = data.get('paciente_id') or data.get('pacienteId') or data.get('paciente_id')

            if cedula or paciente_id:
                from app.models import Paciente, Cita, Consulta
                p_obj = None
                if paciente_id:
                    p_obj = Paciente.query.filter_by(id=int(paciente_id)).first()
                elif cedula:
                    # tolerate dots and spaces in cedula
                    ced_clean = cedula.replace('.', '').replace(' ', '')
                    p_obj = Paciente.query.filter((Paciente.cedula == cedula) | (Paciente.cedula == ced_clean)).first()

                if p_obj:
                    # fill direccion if empty
                    if not direccion:
                        direccion = getattr(p_obj, 'direccion', None) or getattr(p_obj, 'direccion_facturacion', None) or ''
                    # fill edad if empty using fecha_nacimiento
                    if not edad:
                        bd = getattr(p_obj, 'fecha_nacimiento', None)
                        if bd:
                            try:
                                from datetime import date as _date
                                today = _date.today()
                                bd_date = bd if hasattr(bd, 'year') else None
                                if bd_date:
                                    age_years = today.year - bd_date.year - ((today.month, today.day) < (bd_date.month, bd_date.day))
                                    edad = str(age_years)
                            except Exception:
                                pass

                    # try to extract motivo from a cita (preferred) or last consulta if not provided
                    if not motivo:
                        cita_id = data.get('cita_id') or data.get('citaId')
                        # Prefer explicit cita id when provided
                        if cita_id:
                            try:
                                c = Cita.query.filter_by(id=int(cita_id)).first()
                                if c and getattr(c, 'motivo', None):
                                    motivo = c.motivo
                            except Exception:
                                pass

                        # If still missing, try latest Cita for this paciente
                        if not motivo:
                            try:
                                latest_cita = Cita.query.filter_by(paciente_id=p_obj.id).order_by(Cita.fecha.desc()).first()
                                if latest_cita and getattr(latest_cita, 'motivo', None):
                                    motivo = latest_cita.motivo
                                    print(f"[receta_preview_pdf] motivo taken from Cita id={getattr(latest_cita, 'id', None)}: {motivo}", flush=True)
                            except Exception:
                                print('[receta_preview_pdf] cita lookup failed:', traceback.format_exc(), flush=True)

                        # If still missing, fall back to last Consulta
                        if not motivo:
                            try:
                                cons = Consulta.query.filter_by(paciente_id=p_obj.id).order_by(Consulta.fecha.desc()).first()
                                if cons and getattr(cons, 'motivo', None):
                                    motivo = cons.motivo
                                elif cons and getattr(cons, 'diagnostico', None):
                                    motivo = cons.diagnostico
                            except Exception:
                                # print traceback for debugging
                                print('[receta_preview_pdf] consulta lookup failed:', traceback.format_exc(), flush=True)
                else:
                    print(f"[receta_preview_pdf] paciente with cedula/id not found: cedula={cedula} paciente_id={paciente_id}", flush=True)
        except Exception:
            import traceback
            print('[receta_preview_pdf] DB enrichment failed with exception:\n', traceback.format_exc(), flush=True)

    paciente_cell = Paragraph(
        f'<b>Paciente:</b> {paciente or ""}<br/>' +
        f'<b>Dirección:</b> {direccion}<br/>' +
        f'<b>Edad:</b> {edad}<br/>' +
        f'<b>Motivo de Consulta:</b> {motivo}',
        ParagraphStyle('PacienteBlock', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.HexColor('#0b3358'))
    )
    patient_table = Table([[paciente_cell]], colWidths=[doc.width])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), block_bg),
        ('BOX', (0,0), (-1,-1), 1, block_border),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 12))

    # Main area: receta text (single column)
    safe_text = '<br/>'.join([line.replace('<', '&lt;').replace('>', '&gt;') for line in texto.splitlines()]) if texto else '&nbsp;'
    receta_para = Paragraph(safe_text, estilo_body)
    col_table = Table([[receta_para]], colWidths=[doc.width])
    col_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(col_table)
    story.append(Spacer(1, 20))

    # Signature area
    firma_table = Table([['', Paragraph('______________________________<br/><i>Firma y sello</i>', ParagraphStyle('Firma', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT))]], colWidths=[doc.width-70*mm, 70*mm])
    firma_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(Spacer(1, 12))
    story.append(firma_table)
    story.append(Spacer(1, 6))

    # onPage callback: watermark and footer band
    def _on_page(canvas_obj, doc_obj):
        page_w, page_h = doc_obj.pagesize
        canvas_obj.saveState()

        # Watermark image or textual fallback
        if watermark_path:
            try:
                img = ImageReader(watermark_path)
                iw, ih = img.getSize()
                tgt_w = 120 * mm
                ratio = min(tgt_w / float(iw), (page_h * 0.5) / float(ih))
                w = iw * ratio
                h = ih * ratio
                x = (page_w - w) / 2.0
                y = (page_h - h) / 2.0
                try:
                    canvas_obj.setFillAlpha(0.06)
                except Exception:
                    pass
                try:
                    canvas_obj.drawImage(img, x, y, width=w, height=h, mask='auto')
                except Exception:
                    pass
                try:
                    canvas_obj.setFillAlpha(1.0)
                except Exception:
                    pass
            except Exception:
                try:
                    canvas_obj.setFont('Helvetica-Bold', 60)
                    canvas_obj.setFillColor(colors.HexColor('#E6EEF8'))
                    canvas_obj.drawCentredString(page_w/2.0, page_h/2.0, 'RECETA')
                except Exception:
                    pass
        else:
            try:
                canvas_obj.setFont('Helvetica-Bold', 60)
                canvas_obj.setFillColor(colors.HexColor('#E6EEF8'))
                canvas_obj.drawCentredString(page_w/2.0, page_h/2.0, 'RECETA')
            except Exception:
                pass

        # Bottom subtle band
        band_height = 14 * mm
        try:
            canvas_obj.setFillColor(colors.HexColor('#f1f7fb'))
            canvas_obj.rect(0, 0, page_w, band_height, stroke=0, fill=1)
        except Exception:
            pass

        # Contact text centered
        contact_text = '   '.join(filter(None, [contacto_tel, contacto_email, contacto_web]))
        try:
            canvas_obj.setFont('Helvetica', 9)
            canvas_obj.setFillColor(colors.HexColor('#4b4b4b'))
            canvas_obj.drawCentredString(page_w/2.0, band_height/2.0 - 2, contact_text)
        except Exception:
            pass

        canvas_obj.restoreState()

    # Build PDF
    try:
        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    except Exception:
        doc.build(story)

    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Receta_Preview.pdf')


def orden_preview_pdf():
    """
    Generate an "Órdenes de Estudios" PDF preview using the same visual design as receta_preview_pdf.
    Accepts the same JSON/form keys as receta_preview_pdf and returns an attachment named 'Orden_Preview.pdf'.
    """
    # Reuse the same parsing and enrichment logic as receta_preview_pdf
    # We'll duplicate minimal parts to keep the function self-contained.
    data = None
    try:
        data = request.get_json(force=False, silent=True) or {}
    except Exception:
        data = {}
    if not data:
        data = request.form.to_dict()

    try:
        print('\n[orden_preview_pdf] request.form keys:', getattr(request, 'form', None) and dict(request.form))
    except Exception:
        print('[orden_preview_pdf] could not read request.form')
    try:
        print('[orden_preview_pdf] parsed JSON:', data if isinstance(data, dict) else repr(data))
    except Exception:
        print('[orden_preview_pdf] could not print parsed JSON')

    texto = (data.get('texto') or '').strip()
    paciente = (data.get('paciente') or '').strip()
    medico = (data.get('medico') or '').strip()
    logo_path_input = data.get('logo_path')
    watermark_path_input = data.get('watermark_path')
    contacto_tel = data.get('contacto_tel', '')
    contacto_email = data.get('contacto_email', '')
    contacto_web = data.get('contacto_web', '')

    # Resolve assets
    logo_path = _resolve_logo_from_config(logo_path_input)
    watermark_path = None
    if watermark_path_input:
        if os.path.isabs(watermark_path_input) and os.path.exists(watermark_path_input):
            watermark_path = watermark_path_input
        else:
            alt = os.path.join(current_app.root_path, watermark_path_input)
            if os.path.exists(alt):
                watermark_path = alt
    if not watermark_path:
        watermark_path = logo_path

    # Field helpers
    def _get_field(d, *names):
        for n in names:
            if n in d and d[n]:
                return d[n]
        # case-insensitive fallback
        for k, v in d.items():
            if not v:
                continue
            for n in names:
                if k.lower() == n.lower():
                    return v
        return ''

    direccion = _get_field(data, 'direccion', 'direccion_paciente', 'direccion_domicilio', 'direccion_fiscal') or ''
    edad = _get_field(data, 'edad', 'edad_paciente', 'edad_anios', 'age') or ''
    if not edad:
        fn = _get_field(data, 'fecha_nacimiento', 'fecha_nac', 'nacimiento') or ''
        if fn:
            from datetime import datetime as _dt
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    bd = _dt.strptime(fn, fmt)
                    today = _dt.utcnow().date()
                    age_years = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
                    edad = str(age_years)
                    break
                except Exception:
                    continue

    motivo = _get_field(data, 'motivo', 'motivo_consulta', 'motivoConsulta', 'diagnostico', 'observaciones', 'motivo_cita', 'motivo_consulta_text') or ''

    # Enrich from DB if needed (same approach as receta)
    try:
        need_enrich = not (direccion or edad or motivo)
    except NameError:
        need_enrich = True

    if need_enrich and paciente:
        try:
            import re, traceback
            cedula = None
            m = re.search(r'-\s*(\d+)$', paciente)
            if m:
                cedula = m.group(1)
            else:
                m2 = re.search(r'\((\d+)\)', paciente)
                if m2:
                    cedula = m2.group(1)

            paciente_id = data.get('paciente_id') or data.get('pacienteId') or data.get('paciente_id')

            if cedula or paciente_id:
                from app.models import Paciente, Cita, Consulta
                p_obj = None
                if paciente_id:
                    p_obj = Paciente.query.filter_by(id=int(paciente_id)).first()
                elif cedula:
                    ced_clean = cedula.replace('.', '').replace(' ', '')
                    p_obj = Paciente.query.filter((Paciente.cedula == cedula) | (Paciente.cedula == ced_clean)).first()

                if p_obj:
                    if not direccion:
                        direccion = getattr(p_obj, 'direccion', None) or getattr(p_obj, 'direccion_facturacion', None) or ''
                    if not edad:
                        bd = getattr(p_obj, 'fecha_nacimiento', None)
                        if bd:
                            try:
                                from datetime import date as _date
                                today = _date.today()
                                bd_date = bd if hasattr(bd, 'year') else None
                                if bd_date:
                                    age_years = today.year - bd_date.year - ((today.month, today.day) < (bd_date.month, bd_date.day))
                                    edad = str(age_years)
                            except Exception:
                                pass
                    if not motivo:
                        cita_id = data.get('cita_id') or data.get('citaId')
                        if cita_id:
                            try:
                                c = Cita.query.filter_by(id=int(cita_id)).first()
                                if c and getattr(c, 'motivo', None):
                                    motivo = c.motivo
                            except Exception:
                                pass
                        if not motivo:
                            try:
                                latest = Cita.query.filter_by(paciente_id=p_obj.id).order_by(Cita.fecha.desc()).first()
                                if latest and getattr(latest, 'motivo', None):
                                    motivo = latest.motivo
                                else:
                                    cons = Consulta.query.filter_by(paciente_id=p_obj.id).order_by(Consulta.fecha.desc()).first()
                                    if cons and getattr(cons, 'motivo', None):
                                        motivo = cons.motivo
                                    elif cons and getattr(cons, 'diagnostico', None):
                                        motivo = cons.diagnostico
                            except Exception:
                                print('[orden_preview_pdf] consulta/cita lookup failed:', traceback.format_exc(), flush=True)
                else:
                    print(f"[orden_preview_pdf] paciente with cedula/id not found: cedula={cedula} paciente_id={paciente_id}", flush=True)
        except Exception:
            import traceback
            print('[orden_preview_pdf] DB enrichment failed with exception:\n', traceback.format_exc(), flush=True)

    # Prepare PDF (reuse same layout)
    buffer = io.BytesIO()
    left_margin = right_margin = 20 * mm
    top_margin = 40 * mm
    bottom_margin = 30 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin
    )

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=20, leading=22, textColor=colors.HexColor('#0b3358'))
    estilo_ts = ParagraphStyle('Timestamp', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#666666'))
    estilo_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=14)

    story = []

    # Header (same as receta)
    header_bg = colors.HexColor('#EAF4FB')
    left_para = Paragraph('<b>Consultorio Médico San Rafael</b>', ParagraphStyle('MedicoHeader', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor('#0b3358')))
    right_logo = None
    if logo_path:
        try:
            img_reader = ImageReader(logo_path)
            iw, ih = img_reader.getSize()
            target_h = 20 * mm
            ratio = target_h / float(ih) if ih else 1.0
            w = iw * ratio
            h = ih * ratio
            right_logo = RLImage(logo_path, width=w, height=h)
        except Exception:
            right_logo = None

    if right_logo:
        header_table = Table([[left_para, right_logo]], colWidths=[None, 40*mm])
    else:
        header_table = Table([[left_para]], colWidths=[None])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), header_bg),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # timestamp + title
    timestamp = datetime.utcnow().strftime('%d/%m/%Y %H:%M')
    story.append(Paragraph(timestamp, estilo_ts))
    story.append(Spacer(1, 6))
    story.append(Paragraph('ÓRDENES DE ESTUDIOS', estilo_titulo))
    story.append(Spacer(1, 12))

    # Patient block
    block_bg = colors.HexColor('#EAF4FB')
    block_border = colors.HexColor('#D0E6F7')
    paciente_cell = Paragraph(
        f'<b>Paciente:</b> {paciente or ""}<br/>' +
        f'<b>Dirección:</b> {direccion}<br/>' +
        f'<b>Edad:</b> {edad}<br/>' +
        f'<b>Motivo de Consulta:</b> {motivo}',
        ParagraphStyle('PacienteBlock', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.HexColor('#0b3358'))
    )
    patient_table = Table([[paciente_cell]], colWidths=[doc.width])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), block_bg),
        ('BOX', (0,0), (-1,-1), 1, block_border),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 12))

    # Main area: texto
    safe_text = '<br/>'.join([line.replace('<', '&lt;').replace('>', '&gt;') for line in texto.splitlines()]) if texto else '&nbsp;'
    receta_para = Paragraph(safe_text, estilo_body)
    col_table = Table([[receta_para]], colWidths=[doc.width])
    col_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(col_table)
    story.append(Spacer(1, 20))

    # Signature area
    firma_table = Table([['', Paragraph('______________________________<br/><i>Firma y sello</i>', ParagraphStyle('Firma', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT))]], colWidths=[doc.width-70*mm, 70*mm])
    firma_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(Spacer(1, 12))
    story.append(firma_table)
    story.append(Spacer(1, 6))

    # onPage callback (reuse): watermark and footer band
    def _on_page(canvas_obj, doc_obj):
        page_w, page_h = doc_obj.pagesize
        canvas_obj.saveState()
        if watermark_path:
            try:
                img = ImageReader(watermark_path)
                iw, ih = img.getSize()
                tgt_w = 120 * mm
                ratio = min(tgt_w / float(iw), (page_h * 0.5) / float(ih))
                w = iw * ratio
                h = ih * ratio
                x = (page_w - w) / 2.0
                y = (page_h - h) / 2.0
                try:
                    canvas_obj.setFillAlpha(0.06)
                except Exception:
                    pass
                try:
                    canvas_obj.drawImage(img, x, y, width=w, height=h, mask='auto')
                except Exception:
                    pass
                try:
                    canvas_obj.setFillAlpha(1.0)
                except Exception:
                    pass
            except Exception:
                try:
                    canvas_obj.setFont('Helvetica-Bold', 60)
                    canvas_obj.setFillColor(colors.HexColor('#E6EEF8'))
                    canvas_obj.drawCentredString(page_w/2.0, page_h/2.0, 'ÓRDEN')
                except Exception:
                    pass
        else:
            try:
                canvas_obj.setFont('Helvetica-Bold', 60)
                canvas_obj.setFillColor(colors.HexColor('#E6EEF8'))
                canvas_obj.drawCentredString(page_w/2.0, page_h/2.0, 'ÓRDEN')
            except Exception:
                pass

        band_height = 14 * mm
        try:
            canvas_obj.setFillColor(colors.HexColor('#f1f7fb'))
            canvas_obj.rect(0, 0, page_w, band_height, stroke=0, fill=1)
        except Exception:
            pass

        contact_text = '   '.join(filter(None, [contacto_tel, contacto_email, contacto_web]))
        try:
            canvas_obj.setFont('Helvetica', 9)
            canvas_obj.setFillColor(colors.HexColor('#4b4b4b'))
            canvas_obj.drawCentredString(page_w/2.0, band_height/2.0 - 2, contact_text)
        except Exception:
            pass

        canvas_obj.restoreState()

    try:
        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    except Exception:
        doc.build(story)

    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Orden_Preview.pdf')
