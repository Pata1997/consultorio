// Funciones JavaScript del sistema

// ===== SISTEMA DE ALERTAS Y CONFIRMACIONES CON MODALES =====
function mostrarMensaje(titulo, mensaje, tipo = 'info') {
    const modal = new bootstrap.Modal(document.getElementById('mensajeModal'));
    document.getElementById('mensajeModalTitulo').textContent = titulo;
    document.getElementById('mensajeModalCuerpo').innerHTML = mensaje;
    
    // Cambiar color según tipo
    const header = document.querySelector('#mensajeModal .modal-header');
    header.classList.remove('bg-danger', 'bg-warning', 'bg-success', 'bg-info', 'text-white');
    if (tipo === 'error') {
        header.classList.add('bg-danger', 'text-white');
    } else if (tipo === 'warning') {
        header.classList.add('bg-warning');
    } else if (tipo === 'success') {
        header.classList.add('bg-success', 'text-white');
    } else {
        header.classList.add('bg-info', 'text-white');
    }
    
    modal.show();
}

function confirmar(titulo, mensaje, callback) {
    const modal = new bootstrap.Modal(document.getElementById('confirmarModal'));
    document.getElementById('confirmarModalTitulo').textContent = titulo;
    document.getElementById('confirmarModalCuerpo').innerHTML = mensaje;
    
    const boton = document.getElementById('confirmarModalBoton');
    // Remover listeners anteriores
    const nuevoBoton = boton.cloneNode(true);
    boton.parentNode.replaceChild(nuevoBoton, boton);
    
    nuevoBoton.addEventListener('click', function() {
        modal.hide();
        if (callback) callback();
    });
    
    modal.show();
}

// Alias para compatibilidad
window.alert = function(mensaje) {
    mostrarMensaje('Aviso', mensaje, 'info');
};

document.addEventListener('DOMContentLoaded', function() {
    // Auto-cerrar alertas después de 5 segundos
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Confirmación antes de eliminar/cancelar
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.dataset.confirm || '¿Está seguro de realizar esta acción?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Formateo automático de inputs con clase .currency-input
    const currencyInputs = document.querySelectorAll('.currency-input');

    // Helper: formatea el input y mantiene la posición del cursor basada en
    // la cantidad de dígitos a la izquierda del cursor.
    const formatCurrencyInput = function(input) {
        const selStart = input.selectionStart;
        const before = input.value.slice(0, selStart);
        const digitsBefore = (before.match(/\d/g) || []).length;

        const plain = parseFormattedNumberToPlain(input.value);
        if (plain === '') {
            input.value = '';
            return;
        }

        let parts = plain.split('.');
        let intPart = parts[0] || '0';
        let decPart = parts[1] || '';

        // eliminar ceros a la izquierda innecesarios
        intPart = intPart.replace(/^0+(?=\d)/, '');
        if (intPart === '') intPart = '0';

        const intFormatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        let formatted = intFormatted;
        if (decPart && decPart.length > 0) {
            formatted += ',' + decPart.slice(0, 2);
        }

        // debug: log for the specific modal input to trace unexpected truncation
        if (input.id === 'input_monto') {
            console.debug('formatCurrencyInput (input_monto):', { before: input.value, plain: plain, formatted: formatted });
        }
        input.value = formatted;

        // Reubicar caret: buscar la posición que corresponde a digitsBefore
        let pos = formatted.length;
        let digitsSeen = 0;
        for (let i = 0; i < formatted.length; i++) {
            if (/\d/.test(formatted[i])) digitsSeen++;
            if (digitsSeen >= digitsBefore) { pos = i + 1; break; }
        }
        try { input.setSelectionRange(pos, pos); } catch (e) { /* no crítico */ }
    };

    currencyInputs.forEach(inp => {
        // Formateo en tiempo real mientras se escribe
        inp.addEventListener('input', function() {
            formatCurrencyInput(this);
        });

        inp.addEventListener('blur', function() {
            // asegurar formato final al salir
            const plain = parseFormattedNumberToPlain(this.value);
            if (plain !== '') {
                this.value = formatNumberWithDots(plain);
            }
        });

        // formatear inicialmente si ya tiene valor
        if (inp.value && inp.value.trim() !== '') {
            inp.value = formatNumberWithDots(inp.value);
        }
    });

    // Interceptar submit de formularios con currency-inputs para asegurar formato correcto
    const formsWithCurrency = document.querySelectorAll('form');
    formsWithCurrency.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Antes de enviar, convertir todos los currency-inputs a formato plano
            const currencyFields = this.querySelectorAll('.currency-input');
            currencyFields.forEach(field => {
                const plainValue = parseFormattedNumberToPlain(field.value);
                field.value = plainValue;
            });
        });
    });
});

// Formatear números como moneda
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PY', {
        style: 'currency',
        currency: 'PYG',
        minimumFractionDigits: 0
    }).format(amount);
}

// Formatea un número (Number o string convertible) usando '.' como separador de miles
// y ',' como separador decimal. Devuelve string. Ej: 10000 -> '10.000'
function formatNumberWithDots(value) {
    if (value === null || value === undefined || value === '') return '';
    let n = Number(String(value).replace(/\s+/g, '').replace(',', '.'));
    if (isNaN(n)) return '';
    // Mantener dos decimales si existen fracciones
    const hasFraction = Math.round((n - Math.trunc(n)) * 100) !== 0;
    if (hasFraction) {
        // formato con 2 decimales
        const parts = n.toFixed(2).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return parts.join(',');
    } else {
        return String(Math.trunc(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }
}

// Parsea un string con separadores de miles '.' y decimal ',' o '.' a un string
// con punto decimal que el servidor pueda convertir: '1.234,56' -> '1234.56'
function parseFormattedNumberToPlain(value) {
    if (value === null || value === undefined) return '';
    let s = String(value).trim();
    if (s === '') return '';
    // eliminar espacios
    s = s.replace(/\s+/g, '');
    // si tiene coma decimal, eliminar puntos y reemplazar coma por punto
    if ((s.match(/,/g) || []).length === 1 && (s.match(/\./g) || []).length >= 1) {
        s = s.replace(/\./g, '').replace(',', '.');
    } else {
        // eliminar puntos que puedan ser separadores de miles, y reemplazar coma por punto
        s = s.replace(/\./g, '').replace(',', '.');
    }
    return s;
}

// Validación de formularios
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}
