"""Utilidades del sistema"""
# Importar funciones de RBAC
from app.utils.rbac import get_filtered_query, can_access_data, get_menu_items

# PDF generators están temporalmente deshabilitados por errores de sintaxis
# from app.utils.pdf_generator import (
#     PDFGenerator, RecetaPDF, FichaMedicaPDF, FacturaPDF, ArqueoCajaPDF
# )

__all__ = [
    'get_filtered_query',
    'can_access_data', 
    'get_menu_items',
    # 'PDFGenerator', 'RecetaPDF', 'FichaMedicaPDF', 'FacturaPDF', 'ArqueoCajaPDF'
]
