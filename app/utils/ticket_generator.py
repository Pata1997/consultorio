"""
Generador de tickets térmicos (80mm) para impresoras POS
Formato compatible con Paraguay (SET)
"""
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm as mm_unit
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def generar_ticket_pdf(venta, config, buffer):
    """
    Genera un ticket térmico de 80mm en formato PDF
    
    Args:
        venta: Objeto Venta con todos los datos
        config: ConfiguracionConsultorio con datos del negocio
        buffer: BytesIO buffer para escribir el PDF
    """
    print(f"[TICKET GEN] Iniciando generación de ticket...")
    print(f"[TICKET GEN] Venta: {venta.numero_factura}, Total: {venta.total}")
    
    # Configurar tamaño de página: 80mm de ancho, alto variable
    page_width = 80 * mm_unit
    page_height = 297 * mm_unit  # A4 height, se ajustará al contenido
    
    # Crear canvas
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Posición inicial Y (desde arriba)
    y_position = page_height - 10 * mm_unit
    margin_left = 3 * mm_unit
    margin_right = 3 * mm_unit
    content_width = page_width - margin_left - margin_right
    
    # Fuente monoespaciada
    font_normal = 'Courier'
    font_bold = 'Courier-Bold'
    size_small = 7
    size_normal = 8
    size_large = 10
    size_title = 11
    
    def wrap_text(text, font, size, max_width):
        """Envuelve texto en múltiples líneas para que quepa en max_width."""
        if not text:
            return [""]
        words = str(text).split(" ")
        lines = []
        current = ""
        for w in words:
            candidate = (current + " " + w).strip()
            if c.stringWidth(candidate, font, size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                # Si una palabra individual no cabe, cortarla por caracteres
                if c.stringWidth(w, font, size) > max_width:
                    chunk = ""
                    for ch in w:
                        cand = chunk + ch
                        if c.stringWidth(cand, font, size) <= max_width:
                            chunk = cand
                        else:
                            if chunk:
                                lines.append(chunk)
                            chunk = ch
                    current = chunk
                else:
                    current = w
        if current:
            lines.append(current)
        return lines

    def draw_text_center(text, y, font=font_normal, size=size_normal):
        """Dibuja texto centrado con ajuste de línea"""
        c.setFont(font, size)
        for line in wrap_text(text, font, size, content_width):
            text_width = c.stringWidth(line, font, size)
            x = (page_width - text_width) / 2
            c.drawString(x, y, line)
            y -= (size + 2)
        return y
    
    def draw_text_left(text, y, font=font_normal, size=size_normal):
        """Dibuja texto alineado a la izquierda con ajuste de línea"""
        c.setFont(font, size)
        for line in wrap_text(text, font, size, content_width):
            c.drawString(margin_left, y, line)
            y -= (size + 2)
        return y
    
    def draw_separator(y, char='-'):
        """Dibuja línea separadora ajustada al ancho de contenido"""
        c.setFont(font_normal, size_small)
        line = char
        while c.stringWidth(line + char, font_normal, size_small) <= content_width:
            line += char
        text_width = c.stringWidth(line, font_normal, size_small)
        x = (page_width - text_width) / 2
        c.drawString(x, y, line)
        return y - (size_small + 2)
    
    # Logo si existe
    if config.logo_path:
        print(f"[TICKET GEN] Intentando cargar logo: {config.logo_path}")
        # Construir path absoluto si es relativo
        if not os.path.isabs(config.logo_path):
            from flask import current_app
            logo_full_path = os.path.join(current_app.root_path, 'static', config.logo_path)
        else:
            logo_full_path = config.logo_path
        
        print(f"[TICKET GEN] Path completo del logo: {logo_full_path}")
        print(f"[TICKET GEN] ¿Existe el archivo?: {os.path.exists(logo_full_path)}")
        
        if os.path.exists(logo_full_path):
            try:
                logo_width = 40 * mm_unit
                logo_height = 20 * mm_unit
                x_logo = (page_width - logo_width) / 2
                c.drawImage(logo_full_path, x_logo, y_position - logo_height, 
                           width=logo_width, height=logo_height, preserveAspectRatio=True)
                y_position -= (logo_height + 3 * mm_unit)
                print(f"[TICKET GEN] Logo dibujado correctamente")
            except Exception as e_logo:
                print(f"[TICKET GEN] Error al dibujar logo: {e_logo}")
                # Continuar sin logo
        else:
            print(f"[TICKET GEN] Logo no encontrado, continuando sin logo")
    
    # Encabezado
    y_position = draw_text_center(config.nombre.upper(), y_position, font_bold, size_title)
    if config.razon_social and config.razon_social != config.nombre:
        y_position = draw_text_center(f'"{config.razon_social}"', y_position, font_normal, size_normal)
    y_position = draw_text_center(f'RUC: {config.ruc}', y_position, font_normal, size_normal)
    if config.telefono:
        y_position = draw_text_center(f'Tel: {config.telefono}', y_position, font_normal, size_small)
    if config.direccion:
        # Dividir dirección larga en múltiples líneas
        direccion_lines = config.direccion.split(',')
        for line in direccion_lines:
            y_position = draw_text_center(line.strip(), y_position, font_normal, size_small)
    
    y_position -= 2 * mm_unit
    y_position = draw_separator(y_position)
    
    # Datos de timbrado y factura
    if config.punto_expedicion:
        y_position = draw_text_center(f'Punto de Expedicion: {config.punto_expedicion}', y_position, font_normal, size_small)
    if config.timbrado:
        y_position = draw_text_center(f'Timbrado: {config.timbrado}', y_position, font_normal, size_small)
    if config.fecha_inicio_timbrado and config.fecha_fin_timbrado:
        vigencia = f"Vigencia: {config.fecha_inicio_timbrado.strftime('%d/%m/%Y')} - {config.fecha_fin_timbrado.strftime('%d/%m/%Y')}"
        y_position = draw_text_center(vigencia, y_position, font_normal, size_small)
    
    y_position = draw_text_center(f'Factura N: {venta.numero_factura}', y_position, font_bold, size_normal)
    y_position = draw_text_center(f'Fecha: {venta.fecha.strftime("%d/%m/%Y %H:%M")}', y_position, font_normal, size_small)
    
    y_position = draw_separator(y_position)
    
    # Datos del cliente
    y_position = draw_text_left(f'Cliente: {venta.nombre_factura}', y_position, font_normal, size_small)
    if venta.paciente and venta.paciente.cedula:
        y_position = draw_text_left(f'C.I.: {venta.paciente.cedula}', y_position, font_normal, size_small)
    ruc_text = venta.ruc_factura if venta.ruc_factura else 'Sin RUC'
    y_position = draw_text_left(f'RUC: {ruc_text}', y_position, font_normal, size_small)
    if venta.direccion_facturacion:
        y_position = draw_text_left(f'Dir: {venta.direccion_facturacion[:35]}', y_position, font_normal, size_small)
    
    y_position = draw_separator(y_position)
    
    # Detalle de items (IVA incluido)
    y_position = draw_text_left('DETALLE (PRECIOS IVA INCLUIDO)', y_position, font_bold, size_small)
    y_position -= 1 * mm_unit
    
    # Encabezados de columnas
    c.setFont(font_normal, size_small)
    c.drawString(margin_left, y_position, 'Concepto')
    c.drawRightString(margin_left + content_width * 0.55, y_position, 'Cant')
    c.drawRightString(margin_left + content_width * 0.75, y_position, 'P.Unit')
    c.drawRightString(margin_left + content_width, y_position, 'Subtotal')
    y_position -= (size_small + 2)
    
    # Items
    for detalle in venta.detalles:
        # Concepto (truncar si es muy largo)
        concepto = detalle.concepto[:22]
        c.setFont(font_normal, size_small)
        c.drawString(margin_left, y_position, concepto)
        c.drawRightString(margin_left + content_width * 0.55, y_position, str(detalle.cantidad))
        c.drawRightString(margin_left + content_width * 0.75, y_position, f'{int(detalle.precio_unitario):,}')
        c.drawRightString(margin_left + content_width, y_position, f'{int(detalle.subtotal):,}')
        y_position -= (size_small + 2)
        
        # Descripción si existe (más pequeña)
        if detalle.descripcion:
            desc = detalle.descripcion[:30]
            c.setFont(font_normal, size_small - 1)
            c.drawString(margin_left + 2 * mm_unit, y_position, desc)
            y_position -= (size_small + 1)
    
    y_position = draw_separator(y_position)

    # Discriminación de IVA (asumiendo todo al 10% incluido)
    try:
        total_decimal = Decimal(str(venta.total)) if not isinstance(venta.total, Decimal) else venta.total
        gravado_10 = (total_decimal / Decimal('1.1')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        iva_10 = total_decimal - gravado_10
    except Exception:
        gravado_10 = Decimal(int(venta.total // 1.1))
        iva_10 = Decimal(int(venta.total)) - gravado_10

    c.setFont(font_bold, size_small)
    c.drawString(margin_left, y_position, 'Subtotal Gravado 10%:')
    c.drawRightString(margin_left + content_width, y_position, f'{int(gravado_10):,}')
    y_position -= (size_small + 2)

    c.setFont(font_bold, size_small)
    c.drawString(margin_left, y_position, 'IVA 10%:')
    c.drawRightString(margin_left + content_width, y_position, f'{int(iva_10):,}')
    y_position -= (size_small + 3)

    y_position = draw_separator(y_position)

    # Total a pagar
    c.setFont(font_bold, size_normal)
    c.drawString(margin_left, y_position, 'TOTAL A PAGAR:')
    c.drawRightString(margin_left + content_width, y_position, f'{int(venta.total):,}')
    y_position -= (size_normal + 3)
    
    y_position = draw_separator(y_position)
    
    # Formas de pago
    if venta.pagos and len(venta.pagos) > 0:
        y_position = draw_text_left('Formas de Pago:', y_position, font_bold, size_small)
        total_pagado = Decimal('0')
        
        for pago in venta.pagos:
            forma_nombre = pago.forma_pago_rel.nombre.replace('_', ' ').title() if pago.forma_pago_rel else 'Efectivo'
            c.setFont(font_normal, size_small)
            c.drawString(margin_left, y_position, f'{forma_nombre}:')
            c.drawRightString(margin_left + content_width, y_position, f'{int(pago.monto):,}')
            y_position -= (size_small + 2)
            total_pagado += pago.monto
            
            # Referencia si existe
            if pago.referencia:
                c.setFont(font_normal, size_small - 1)
                c.drawString(margin_left + 2 * mm_unit, y_position, f'Ref: {pago.referencia[:25]}')
                y_position -= (size_small + 1)
        
        y_position = draw_separator(y_position, '-')
        
        # Total pagado
        c.setFont(font_bold, size_small)
        c.drawString(margin_left, y_position, 'Total Pagado:')
        c.drawRightString(margin_left + content_width, y_position, f'{int(total_pagado):,}')
        y_position -= (size_small + 3)
        
        # Vuelto si existe
        vuelto = total_pagado - venta.total
        if vuelto > 0:
            c.setFont(font_bold, size_normal)
            c.drawString(margin_left, y_position, 'Vuelto:')
            c.drawRightString(margin_left + content_width, y_position, f'{int(vuelto):,}')
            y_position -= (size_normal + 3)
        
        y_position = draw_separator(y_position)
    
    # Información adicional
    if config.slogan:
        y_position -= 1 * mm_unit
        y_position = draw_text_center(config.slogan, y_position, font_normal, size_small)
    
    if config.horario_atencion:
        y_position = draw_text_center(f'Horario: {config.horario_atencion}', y_position, font_normal, size_small)
    
    y_position = draw_separator(y_position)
    y_position = draw_text_center('Gracias por su visita!', y_position, font_bold, size_normal)
    y_position = draw_separator(y_position)
    
    # Calcular altura final (desde arriba hasta donde terminamos)
    final_height = page_height - y_position + 10 * mm_unit
    
    print(f"[TICKET GEN] Ticket generado con éxito")
    print(f"[TICKET GEN] Dimensiones: {page_width/mm_unit}mm x {final_height/mm_unit}mm")
    print(f"[TICKET GEN] Y final: {y_position/mm_unit}mm")
    
    # Guardar PDF (NO ajustar tamaño, dejarlo como está)
    c.showPage()
    c.save()
    
    # Verificar tamaño del buffer ANTES de resetear
    buffer_size = buffer.tell()
    print(f"[TICKET GEN] PDF guardado, tamaño: {buffer_size} bytes")
    
    # IMPORTANTE: Resetear posición del buffer al inicio para que se pueda leer
    buffer.seek(0)
    
    print(f"[TICKET GEN] Buffer reseteado a posición: {buffer.tell()} bytes")
    print(f"[TICKET GEN] Listo para enviar {buffer_size} bytes")
    
    buffer.seek(0)
    return buffer
