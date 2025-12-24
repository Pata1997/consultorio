"""
Script para actualizar la base de datos con los nuevos campos necesarios para facturación
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Agregar campos a tabla insumos
    db.session.execute(text("""
        -- Agregar precio_compra
        ALTER TABLE insumos ADD COLUMN IF NOT EXISTS precio_compra NUMERIC(10, 2) DEFAULT 0;
        
        -- Renombrar precio_unitario a precio_venta (solo si existe)
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'insumos' AND column_name = 'precio_unitario'
            ) THEN
                ALTER TABLE insumos RENAME COLUMN precio_unitario TO precio_venta;
            END IF;
        END $$;
        
        -- Agregar precio_venta si no existe
        ALTER TABLE insumos ADD COLUMN IF NOT EXISTS precio_venta NUMERIC(10, 2) DEFAULT 0;
        
        -- Actualizar precio_compra con el 60% del precio_venta (estimación)
        UPDATE insumos SET precio_compra = precio_venta * 0.6 WHERE precio_compra = 0;
    """))
    
    # Agregar campos a tabla pacientes para facturación
    db.session.execute(text("""
        ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS ruc VARCHAR(20);
        ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS direccion_facturacion TEXT;
        ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS razon_social VARCHAR(200);
    """))
    
    # Agregar campo a ventas para nombre de facturación
    db.session.execute(text("""
        ALTER TABLE ventas ADD COLUMN IF NOT EXISTS timbrado VARCHAR(20);
        ALTER TABLE ventas ADD COLUMN IF NOT EXISTS ruc_factura VARCHAR(20);
        ALTER TABLE ventas ADD COLUMN IF NOT EXISTS nombre_factura VARCHAR(200);
        ALTER TABLE ventas ADD COLUMN IF NOT EXISTS direccion_factura TEXT;
    """))
    
    # Actualizar especialidades sin precio_consulta
    db.session.execute(text("""
        UPDATE especialidades SET precio_consulta = 30000 
        WHERE precio_consulta IS NULL OR precio_consulta = 0;
    """))
    
    db.session.commit()
    print("✅ Base de datos actualizada correctamente")
