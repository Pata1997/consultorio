from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os

class PDFGenerator:
    """Clase base para generar PDFs"""
    
    def __init__(self, filename, config=None):
        self.filename = filename
        self.config = config
        self.doc = SimpleDocTemplate(filename, pagesize=letter)
        self.story = []
        self.styles = getSampleStyleSheet()
        
        # Estilos personalizados
        self.styles.add(ParagraphStyle(
            name='CenterTitle',
            parent=self.styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=16,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT
        ))
    
    def add_membrete(self, titulo=None):
        """Agregar membrete con logo y datos del consultorio"""
        if not self.config:
            return
        
        membrete_data = []
        
        # Si hay logo, agregarlo
        if self.config.logo_path:
            try:
                logo_path = os.path.join('app', 'static', self.config.logo_path)
                if os.path.exists(logo_path):
                    logo = Image(logo_path, width=0.6*inch, height=0.6*inch)
                    info_consultorio = f"""
                    <b><font size="10">{self.config.nombre}</font></b><br/>
                    <font size="7">{self.config.direccion or ''}<br/>
                    Tel: {self.config.telefono or 'N/A'} | Email: {self.config.email or 'N/A'}<br/>
                    RUC: {self.config.ruc}</font>
                    """
                    membrete_data = [[logo, Paragraph(info_consultorio, self.styles['Normal'])]]
                else:
                    # Si no existe el logo, solo texto
                    membrete_data = self._crear_membrete_texto()
            except:
                membrete_data = self._crear_membrete_texto()
        else:
            membrete_data = self._crear_membrete_texto()
        
        if membrete_data:
            membrete_table = Table(membrete_data, colWidths=[0.8*inch, 5*inch])
            membrete_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ]))
            self.story.append(membrete_table)
            self.story.append(Spacer(1, 0.1*inch))
        
        # Título del documento
        if titulo:
            titulo_style = ParagraphStyle(
                name='TituloCompacto',
                parent=self.styles['Heading1'],
                alignment=TA_CENTER,
                fontSize=12,
                spaceAfter=4
            )
            self.story.append(Paragraph(titulo, titulo_style))
            self.story.append(Spacer(1, 0.1*inch))
        
        # Línea separadora
        line_data = [['_' * 100]]
        line_table = Table(line_data, colWidths=[6.5*inch])
        self.story.append(line_table)
        self.story.append(Spacer(1, 0.1*inch))
    
    def _crear_membrete_texto(self):
        """Crear membrete solo con texto cuando no hay logo"""
        info = f"""
        <b><font size="10">{self.config.nombre}</font></b><br/>
        <font size="7">{self.config.direccion or ''}<br/>
        Tel: {self.config.telefono or 'N/A'} | Email: {self.config.email or 'N/A'}<br/>
        RUC: {self.config.ruc}</font>
        """
        return [[Paragraph(info, self.styles['Normal'])]]
    
    def add_header(self, titulo, subtitulo=None):
        """Agregar encabezado al documento"""
        self.story.append(Paragraph(titulo, self.styles['CenterTitle']))
        if subtitulo:
            self.story.append(Paragraph(subtitulo, self.styles['Normal']))
        self.story.append(Spacer(1, 0.3*inch))
    
    def add_paragraph(self, text, style='Normal'):
        """Agregar párrafo"""
        self.story.append(Paragraph(text, self.styles[style]))
        self.story.append(Spacer(1, 0.1*inch))
    
    def add_spacer(self, height=0.2):
        """Agregar espacio"""
        self.story.append(Spacer(1, height*inch))
    
    def build(self):
        """Construir el PDF"""
        self.doc.build(self.story)

class RecetaPDF(PDFGenerator):
    """Generar receta médica"""
    
    def __init__(self, filename, consulta, config=None):
        super().__init__(filename, config)
        self.consulta = consulta
    
    def generar(self):
        """Generar PDF de receta"""
        # Membrete
        self.add_membrete("RECETA MÉDICA")
        
        # Datos del médico y paciente en tabla compacta
        datos_info = [
            ['Médico:', self.consulta.medico.nombre_completo, 'Reg. Prof.:', self.consulta.medico.registro_profesional],
            ['Paciente:', self.consulta.paciente.nombre_completo, 'Fecha:', self.consulta.fecha.strftime('%d/%m/%Y')],
        ]
        
        tabla_info = Table(datos_info, colWidths=[1*inch, 2.5*inch, 1*inch, 2*inch])
        tabla_info.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        self.story.append(tabla_info)
        self.add_spacer(0.15)
        
        # Prescripción
        titulo_rx = ParagraphStyle(
            name='TituloRx',
            parent=self.styles['Heading2'],
            fontSize=10,
            spaceAfter=4,
            spaceBefore=4
        )
        self.story.append(Paragraph("<b>Rp/</b>", titulo_rx))
        self.add_spacer(0.1)
        
        for receta in self.consulta.recetas:
            # Usar fuente más pequeña para el contenido
            self.story.append(Paragraph(f"<font size='9'><b>{receta.medicamento}</b></font>", self.styles['Normal']))
            self.story.append(Paragraph(f"<font size='8'>Dosis: {receta.dosis}</font>", self.styles['Normal']))
            self.story.append(Paragraph(f"<font size='8'>Frecuencia: {receta.frecuencia}</font>", self.styles['Normal']))
            self.story.append(Paragraph(f"<font size='8'>Duración: {receta.duracion}</font>", self.styles['Normal']))
            if receta.indicaciones:
                self.story.append(Paragraph(f"<font size='8'>Indicaciones: {receta.indicaciones}</font>", self.styles['Normal']))
            self.add_spacer(0.15)
        
        # Observaciones generales
        if self.consulta.observaciones:
            self.add_spacer(0.15)
            self.story.append(Paragraph("<b>Indicaciones Generales:</b>", titulo_rx))
            self.story.append(Paragraph(f"<font size='8'>{self.consulta.observaciones}</font>", self.styles['Normal']))
        
        # Firma
        self.add_spacer(0.5)
        firma_style = ParagraphStyle(
            name='Firma',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT,
            fontSize=8
        )
        self.story.append(Paragraph("_" * 40, firma_style))
        self.story.append(Paragraph(f"<b>{self.consulta.medico.nombre_completo}</b>", firma_style))
        self.story.append(Paragraph(f"Reg. Prof. {self.consulta.medico.registro_profesional}", firma_style))
        
        # Construir PDF
        self.build()
        return self.filename

class FichaMedicaPDF(PDFGenerator):
    """Generar ficha médica completa"""
    
    def __init__(self, filename, consulta, config=None):
        super().__init__(filename, config)
        self.consulta = consulta
    
    def generar(self):
        """Generar PDF de ficha médica"""
        # Encabezado
        self.add_header("FICHA MÉDICA")
        
        # Datos del paciente
        paciente = self.consulta.paciente
        datos_paciente = [
            ['Nombre:', paciente.nombre_completo, 'Edad:', f"{paciente.edad} años"],
            ['Cédula:', paciente.cedula, 'Sexo:', paciente.sexo],
            ['Teléfono:', paciente.telefono or 'N/A', 'Tipo Sangre:', paciente.tipo_sangre or 'N/A'],
        ]
        
        tabla_paciente = Table(datos_paciente, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2*inch])
        tabla_paciente.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        self.story.append(tabla_paciente)
        self.add_spacer()
        
        # Consulta
        self.add_paragraph(f"<b>Fecha:</b> {self.consulta.fecha.strftime('%d/%m/%Y %H:%M')}")
        self.add_paragraph(f"<b>Médico:</b> {self.consulta.medico.nombre_completo}")
        self.add_paragraph(f"<b>Especialidad:</b> {self.consulta.especialidad.nombre}")
        
        self.add_spacer()
        
        # Signos vitales
        if any([self.consulta.presion_arterial, self.consulta.temperatura, 
                self.consulta.pulso, self.consulta.peso, self.consulta.altura]):
            self.add_paragraph("<b>Signos Vitales:</b>", 'Heading3')
            
            signos = []
            if self.consulta.presion_arterial:
                signos.append(f"PA: {self.consulta.presion_arterial}")
            if self.consulta.temperatura:
                signos.append(f"Temp: {self.consulta.temperatura}°C")
            if self.consulta.pulso:
                signos.append(f"Pulso: {self.consulta.pulso} lpm")
            if self.consulta.peso:
                signos.append(f"Peso: {self.consulta.peso} kg")
            if self.consulta.altura:
                signos.append(f"Altura: {self.consulta.altura} m")
            
            self.add_paragraph(", ".join(signos))
            self.add_spacer()
        
        # Motivo y diagnóstico
        self.add_paragraph(f"<b>Motivo:</b> {self.consulta.motivo}")
        self.add_paragraph(f"<b>Diagnóstico:</b> {self.consulta.diagnostico}")
        
        # Procedimientos realizados
        if self.consulta.procedimientos_realizados:
            self.add_spacer()
            self.add_paragraph("<b>Procedimientos Realizados:</b>", 'Heading3')
            for cp in self.consulta.procedimientos_realizados:
                self.add_paragraph(f"• {cp.procedimiento_rel.nombre}")
        
        # Observaciones
        if self.consulta.observaciones:
            self.add_spacer()
            self.add_paragraph(f"<b>Observaciones:</b> {self.consulta.observaciones}")
        
        # Construir PDF
        self.build()
        return self.filename


class FacturaPDF(PDFGenerator):
    """Generador de PDF para facturas"""
    
    def __init__(self, filename, venta, config=None):
        super().__init__(filename, config)
        self.venta = venta
    
    def generar(self):
        """Generar PDF de factura"""
        # Membrete y datos de timbrado
        self.add_membrete()
        
        # Título y número de factura
        self.add_paragraph(f"<b><font size='16'>FACTURA</font></b><br/>N° {self.venta.numero_factura}", 'CenterTitle')
        
        # Timbrado (si existe)
        if self.config and self.config.timbrado:
            timbrado_info = f"<b>Timbrado:</b> {self.config.timbrado}<br/>"
            if self.config.fecha_inicio_timbrado and self.config.fecha_fin_timbrado:
                timbrado_info += f"Vigencia: {self.config.fecha_inicio_timbrado.strftime('%d/%m/%Y')} al {self.config.fecha_fin_timbrado.strftime('%d/%m/%Y')}"
            self.add_paragraph(timbrado_info)
        
        self.add_spacer()
        
        # Datos del cliente
        self.add_paragraph(f"<b>Fecha:</b> {self.venta.fecha.strftime('%d/%m/%Y %H:%M')}")
        self.add_paragraph(f"<b>Cliente:</b> {self.venta.paciente.nombre_completo}")
        self.add_paragraph(f"<b>Cédula:</b> {self.venta.paciente.cedula}")
        
        self.add_spacer()
        
        # Detalle de items
        datos_items = [['Concepto', 'Cant.', 'Precio Unit.', 'Subtotal']]
        
        for detalle in self.venta.detalles:
            datos_items.append([
                detalle.concepto,
                str(detalle.cantidad),
                f"{float(detalle.precio_unitario):,.0f} Gs",
                f"{float(detalle.subtotal):,.0f} Gs"
            ])
        
        # Totales (IVA Incluido - Paraguay)
        datos_items.append(['', '', 'TOTAL:', f"{float(self.venta.total):,.0f} Gs"])
        datos_items.append(['', '', 'Gravadas 10%:', f"{float(self.venta.subtotal):,.0f} Gs"])
        datos_items.append(['', '', 'IVA 10%:', f"{float(self.venta.iva):,.0f} Gs"])
        
        tabla_items = Table(datos_items, colWidths=[3.5*inch, 0.7*inch, 1.2*inch, 1.2*inch])
        tabla_items.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            
            # Contenido
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 10),
            
            # Totales
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 11),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            
            # Bordes y alineación
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -4), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        self.story.append(tabla_items)
        
        # Estado del pago
        self.add_spacer()
        if self.venta.estado == 'pagada':
            self.add_paragraph("<b>PAGADO</b>", 'CenterTitle')
        else:
            saldo = self.venta.saldo_pendiente
            self.add_paragraph(f"<b>Saldo Pendiente:</b> {saldo:,.0f} Gs")
        
        # Construir PDF
        self.build()
        return self.filename


class ArqueoCajaPDF(PDFGenerator):
    """Generador de PDF para arqueo de caja"""
    
    def __init__(self, filename, caja, ventas, formas_pago, config=None):
        super().__init__(filename, config)
        self.caja = caja
        self.ventas = ventas
        self.formas_pago = formas_pago
        
        # Calcular totales
        from decimal import Decimal
        self.total_ingresos = sum((Decimal(str(v.total)) for v in ventas if v.estado == 'pagada'), Decimal('0'))
        self.total_egresos = Decimal('0')  # Por ahora no hay egresos
        self.saldo_teorico = Decimal(str(caja.monto_inicial)) + self.total_ingresos - self.total_egresos
        self.efectivo_contado = Decimal(str(caja.monto_final)) if caja.monto_final else Decimal('0')
        self.diferencia = self.efectivo_contado - self.saldo_teorico
    
    def generar(self):
        """Genera el PDF del arqueo"""
        # Membrete
        self.add_membrete("ARQUEO DE CAJA")
        
        # Información de la sesión
        titulo_style = ParagraphStyle(
            name='TituloSeccion',
            parent=self.styles['Heading2'],
            fontSize=10,
            spaceAfter=4,
            spaceBefore=4
        )
        self.story.append(Paragraph("<b>INFORMACIÓN DE LA SESIÓN</b>", titulo_style))
        self.add_spacer(0.1)
        
        info_data = [
            ['Cajero:', self.caja.usuario_apertura.username if self.caja.usuario_apertura else 'N/A'],
            ['Fecha/Hora Apertura:', self.caja.fecha_apertura.strftime('%d/%m/%Y %H:%M') if self.caja.fecha_apertura else 'N/A'],
            ['Fecha/Hora Cierre:', self.caja.fecha_cierre.strftime('%d/%m/%Y %H:%M') if self.caja.fecha_cierre else 'Abierta'],
        ]
        
        tabla_info = Table(info_data, colWidths=[2.5*inch, 4*inch])
        tabla_info.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        self.story.append(tabla_info)
        self.add_spacer(0.15)
        
        # Resumen de movimientos
        self.story.append(Paragraph("<b>RESUMEN DE MOVIMIENTOS</b>", titulo_style))
        self.add_spacer(0.1)
        
        movimientos_data = [
            ['Descripción', 'Monto'],
            ['Saldo Inicial', f'{float(self.caja.monto_inicial):,.0f} Gs'],
            ['+ Ingresos (Ventas)', f'{float(self.total_ingresos):,.0f} Gs'],
            ['- Egresos', f'{float(self.total_egresos):,.0f} Gs'],
            ['Saldo Teórico (Esperado)', f'{float(self.saldo_teorico):,.0f} Gs'],
            ['Efectivo Contado', f'{float(self.efectivo_contado):,.0f} Gs'],
            ['Diferencia', f'{float(self.diferencia):,.0f} Gs'],
        ]
        
        tabla_mov = Table(movimientos_data, colWidths=[4*inch, 2.5*inch])
        tabla_mov.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
            ('BACKGROUND', (0, 4), (-1, 4), colors.lightblue),  # Saldo teórico
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 6), (-1, 6), colors.red if self.diferencia != 0 else colors.lightgreen),
            ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
        ]))
        self.story.append(tabla_mov)
        self.add_spacer(0.15)
        
        # Alerta si hay diferencia
        if self.diferencia != 0:
            diferencia_texto = f"<font size='8'><b>¡ATENCIÓN!</b> Hay una diferencia de {float(self.diferencia):,.0f} Gs en el arqueo.</font>"
            self.story.append(Paragraph(f'<para backColor="#ffcccc" leftIndent="5" rightIndent="5" spaceAfter="2" spaceBefore="2">{diferencia_texto}</para>', self.styles['Normal']))
            self.add_spacer(0.15)
        else:
            cuadra_texto = "<font size='8'><b>✓ Caja cuadrada:</b> El efectivo contado coincide con el saldo teórico.</font>"
            self.story.append(Paragraph(f'<para backColor="#ccffcc" leftIndent="5" rightIndent="5" spaceAfter="2" spaceBefore="2">{cuadra_texto}</para>', self.styles['Normal']))
            self.add_spacer(0.15)
        
        # Detalle por forma de pago
        if self.formas_pago:
            self.story.append(Paragraph("<b>DETALLE POR FORMA DE PAGO</b>", titulo_style))
            self.add_spacer(0.1)
            
            formas_data = [['Forma de Pago', 'Total']]
            for forma, total in self.formas_pago:
                formas_data.append([forma, f'{float(total):,.0f} Gs'])
            
            tabla_formas = Table(formas_data, colWidths=[4*inch, 2.5*inch])
            tabla_formas.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
            ]))
            self.story.append(tabla_formas)
            self.add_spacer(0.15)
        
        # Resumen de ventas
        self.story.append(Paragraph("<b>RESUMEN DE VENTAS</b>", titulo_style))
        self.add_spacer(0.1)
        self.story.append(Paragraph(f"<font size='8'>Total de ventas: <b>{len(self.ventas)}</b></font>", self.styles['Normal']))
        self.add_spacer(0.15)
        
        # Espacio para firmas
        self.story.append(Paragraph("<b>FIRMAS</b>", titulo_style))
        self.add_spacer(0.1)
        
        # Tabla de firmas
        firmas_data = [
            ['_____________________________', '_____________________________'],
            ['Firma del Cajero', 'Firma del Supervisor/Encargado'],
        ]
        
        tabla_firmas = Table(firmas_data, colWidths=[3.25*inch, 3.25*inch])
        tabla_firmas.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 2),
        ]))
        self.story.append(tabla_firmas)
        self.add_spacer(0.15)
        
        # Fecha de generación
        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        fecha_style = ParagraphStyle(
            name='FechaGen',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT,
            fontSize=7
        )
        self.story.append(Paragraph(f"<i>Documento generado el {fecha_gen}</i>", fecha_style))
        
        # Construir PDF
        self.build()
        return self.filename
