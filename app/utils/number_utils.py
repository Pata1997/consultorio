from decimal import Decimal, InvalidOperation

def format_currency(value):
    """Formatea un número Decimal/float/int a string con separador de miles '.'
    y separador decimal ',' (ej: 10000 -> '10.000', 1234.5 -> '1.234,50').
    Devuelve cadena vacía si el valor es None o inválido.
    """
    if value is None:
        return ''
    try:
        v = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return ''

    sign = '-' if v < 0 else ''
    v = abs(v)
    # Separar parte entera y fraccionaria
    integer_part = int(v)
    frac = (v - integer_part).quantize(Decimal('0.01'))
    # Formatear miles usando el separador por defecto y luego reemplazar
    int_formatted = f"{integer_part:,}".replace(',', '.')
    if frac == 0:
        return f"{sign}{int_formatted}"
    # Obtener dos decimales
    frac_str = f"{frac:.2f}".split('.')[-1]
    return f"{sign}{int_formatted},{frac_str}"


def parse_decimal_from_form(raw):
    """Normaliza un string ingresado por usuario que puede contener separadores
    de miles '.' y separador decimal ',' o '.' y lo convierte a Decimal.
    Retorna None si no es convertible.
    Ejemplos:
      '10.000' -> Decimal('10000')
      '1.234,56' -> Decimal('1234.56')
      '1234.56' -> Decimal('1234.56')
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == '':
        return None
    # Remover espacios
    s = s.replace(' ', '')
    # Si contiene coma como decimal, asumir formato europeo: miles '.' y decimal ','
    if s.count(',') == 1 and s.count('.') >= 1:
        # eliminar puntos de miles y reemplazar coma por punto
        s = s.replace('.', '').replace(',', '.')
    else:
        # Caso general: eliminar puntos que pueden ser miles, dejar coma como decimal
        # Reemplazar coma por punto
        s = s.replace('.', '').replace(',', '.')

    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None
