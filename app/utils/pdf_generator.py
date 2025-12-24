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
                    logo = Image(logo_path, width=1*inch, height=1*inch)
                    info_consultorio = f"""
                    <b><font size="14">{self.config.nombre}</font></b><br/>
                    {self.config.direccion or ''}<br/>
                    Tel: {self.config.telefono or 'N/A'} | Email: {self.config.email or 'N/A'}<br/>
                    RUC: {self.config.ruc}
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
            membrete_table = Table(membrete_data, colWidths=[1.2*inch, 5*inch])
            membrete_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ]))
            self.story.append(membrete_table)
            self.story.append(Spacer(1, 0.2*inch))
        
        # Título del documento
        if titulo:
            self.story.append(Paragraph(titulo, self.styles['CenterTitle']))
            self.story.append(Spacer(1, 0.2*inch))
        
        # Línea separadora
        line_data = [['_' * 100]]
        line_table = Table(line_data, colWidths=[6.5*inch])
        self.story.append(line_table)
        self.story.append(Spacer(1, 0.2*inch))
    
    def _crear_membrete_texto(self):
        """Crear membrete solo con texto cuando no hay logo"""
        info = f"""
        <b><font size="16">{self.config.nombre}</font></b><br/>
        <font size="10">{self.config.direccion or ''}<br/>
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
        
        # Datos del médico
        self.add_paragraph(f"<b>Médico:</b> {self.consulta.medico.nombre_completo}")
        self.add_paragraph(f"<b>Reg. Profesional:</b> {self.consulta.medico.registro_profesional}")
        self.add_spacer(0.2)
        
        # Datos del paciente
        self.add_paragraph(f"<b>Paciente:</b> {self.consulta.paciente.nombre_completo}")
        self.add_paragraph(f"<b>Fecha:</b> {self.consulta.fecha.strftime('%d/%m/%Y')}")
        
        self.add_spacer()
        
        # Prescripción
        self.add_paragraph("<b>Rp/</b>", 'Heading2')
        
        for receta in self.consulta.recetas:
            self.add_paragraph(f"<b>{receta.medicamento}</b>")
            self.add_paragraph(f"Dosis: {receta.dosis}")
            self.add_paragraph(f"Frecuencia: {receta.frecuencia}")
            self.add_paragraph(f"Duración: {receta.duracion}")
            if receta.indicaciones:
                self.add_paragraph(f"Indicaciones: {receta.indicaciones}")
            self.add_spacer(0.3)
        
        # Observaciones generales
        if self.consulta.observaciones:
            self.add_spacer()
            self.add_paragraph("<b>Indicaciones Generales:</b>", 'Heading3')
            self.add_paragraph(self.consulta.observaciones)
        
        # Firma
        self.add_spacer(1.5)
        self.add_paragraph("_" * 40, 'RightAlign')
        self.add_paragraph(f"{self.consulta.medico.nombre_completo}", 'RightAlign')
        self.add_paragraph(f"Reg. Prof. {self.consulta.medico.registro_profesional}", 'RightAlign')
        
        # Construir PDF
        self.build()
        return self.filename
    
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
        return self.filename, config=None):
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
        
        self.add_spacer("""Generar PDF de factura"""
        # Encabezado
        self.add_header(
            "FACTURA",
            f"N° {self.venta.numero_factura}"
        )
        
        # Datos de la factura
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
        
        # Totales
        datos_items.append(['', '', 'Subtotal:', f"{float(self.venta.subtotal):,.0f} Gs"])
        datos_items.append(['', '', 'IVA 10%:', f"{float(self.venta.iva):,.0f} Gs"])
        datos_items.append(['', '', 'TOTAL:', f"{float(self.venta.total):,.0f} Gs"])
        
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
            self.add_paragraph(f"<b>Saldo Pendiente:</b> {saldo:,.0f} , config=None):
        super().__init__(filename, config)
        self.caja = caja
        self.ventas = ventas
        self.formas_pago = formas_pago
        self.diferencia = diferencia
    
    def generar(self):
        """Generar PDF de arqueo de caja"""
        self.add_membretefilename, caja, ventas, formas_pago, diferencia):
        super().__init__(filename)
        self.caja = caja
        self.ventas = ventas
        self.formas_pago = formas_pago
        self.diferencia = diferencia
    
    def generar(self):
        """Generar PDF de arqueo de caja"""
        self.add_header("ARQUEO DE CAJA")
        
        # Datos de la caja
        self.add_paragraph(f"<b>Fecha Apertura:</b> {self.caja.fecha_apertura.strftime('%d/%m/%Y %H:%M')}")
        if self.caja.fecha_cierre:
            self.add_paragraph(f"<b>Fecha Cierre:</b> {self.caja.fecha_cierre.strftime('%d/%m/%Y %H:%M')}")
        self.add_paragraph(f"<b>Monto Inicial:</b> {float(self.caja.monto_inicial):,.0f} Gs")
        
        self.add_spacer()
        
        # Resumen por forma de pago
        self.add_paragraph("<b>Recaudación por Forma de Pago:</b>", 'Heading3')
        
        datos_formas = [['Forma de Pago', 'Total']]
        total_recaudado = 0
        
        for forma, total in self.formas_pago:
            datos_formas.append([forma, f"{float(total):,.0f} Gs"])
            total_recaudado += float(total)
        
        datos_formas.append(['TOTAL RECAUDADO', f"{total_recaudado:,.0f} Gs"])
        
        tabla_formas = Table(datos_formas, colWidths=[4*inch, 2*inch])
        tabla_formas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        self.story.append(tabla_formas)
        self.add_spacer()
        
        # Cálculo final
        monto_esperado = float(self.caja.monto_inicial) + total_recaudado
        monto_final = float(self.caja.monto_final) if self.caja.monto_final else 0
        
        self.add_paragraph(f"<b>Monto Esperado:</b> {monto_esperado:,.0f} Gs")
        self.add_paragraph(f"<b>Monto Final:</b> {monto_final:,.0f} Gs")
        
        if self.diferencia != 0:
            color = "red" if self.diferencia < 0 else "green"
            self.add_paragraph(
                f"<b>Diferencia:</b> <font color='{color}'>{self.diferencia:,.0f} Gs</font>"
            )
        
        # Construir PDF
        self.build()
        return self.filename
