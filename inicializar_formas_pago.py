"""
Script para inicializar formas de pago en la base de datos
"""
from app import create_app, db
from app.models.facturacion import FormaPago

app = create_app()

with app.app_context():
    # Verificar si ya existen formas de pago
    count = FormaPago.query.count()
    
    if count == 0:
        # Crear formas de pago
        formas = [
            FormaPago(
                nombre='efectivo',
                descripcion='Pago en efectivo',
                activo=True,
                requiere_referencia=False
            ),
            FormaPago(
                nombre='tarjeta_debito',
                descripcion='Tarjeta de débito',
                activo=True,
                requiere_referencia=True
            ),
            FormaPago(
                nombre='tarjeta_credito',
                descripcion='Tarjeta de crédito',
                activo=True,
                requiere_referencia=True
            ),
            FormaPago(
                nombre='cheque',
                descripcion='Cheque',
                activo=True,
                requiere_referencia=True
            ),
            FormaPago(
                nombre='transferencia',
                descripcion='Transferencia bancaria',
                activo=True,
                requiere_referencia=True
            )
        ]
        
        for forma in formas:
            db.session.add(forma)
        
        db.session.commit()
        print(f"✅ {len(formas)} formas de pago creadas exitosamente")
    else:
        print(f"ℹ️  Ya existen {count} formas de pago registradas")
        
        # Mostrar formas de pago existentes
        formas = FormaPago.query.all()
        for forma in formas:
            print(f"   - {forma.nombre}: {forma.descripcion}")
