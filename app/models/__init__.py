"""Inicialización de modelos"""
from app.models.usuario import Usuario, Paciente, Especialidad, Medico, MedicoEspecialidad, HorarioAtencion
from app.models.consultorio import (
    Cita, Consulta, Receta, OrdenEstudio, Insumo, InsumoEspecialidad,
    ConsultaInsumo, MovimientoInsumo, Procedimiento, ConsultaProcedimiento
)
from app.models.consultorio import ProcedimientoPrecio
from app.models.facturacion import (
    Caja, Venta, VentaDetalle, FormaPago, Pago, NotaCredito, NotaDebito
)
from app.models.rrhh import Vacacion, Permiso, Asistencia
from app.models.configuracion import ConfiguracionConsultorio

__all__ = [
    'Usuario', 'Paciente', 'Especialidad', 'Medico', 'MedicoEspecialidad', 'HorarioAtencion',
    'Cita', 'Consulta', 'Receta', 'OrdenEstudio', 'Insumo', 'InsumoEspecialidad',
    'ConsultaInsumo', 'MovimientoInsumo', 'Procedimiento', 'ConsultaProcedimiento',
    'ProcedimientoPrecio',
    'Caja', 'Venta', 'VentaDetalle', 'FormaPago', 'Pago', 'NotaCredito', 'NotaDebito',
    'Vacacion', 'Permiso', 'Asistencia', 'ConfiguracionConsultorio'
]
