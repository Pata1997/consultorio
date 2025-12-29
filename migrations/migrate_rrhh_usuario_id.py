import os
import sys
from sqlalchemy import text

# Ensure project root is on sys.path so `import app` works when run from migrations/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db

"""
One-time migration to switch RRHH tables (vacaciones, permisos, asistencias)
from medico_id to usuario_id, with no historical data kept.

Steps:
1) Truncate tables
2) Drop medico_id columns (if any)
3) Add usuario_id with NOT NULL and FKs
"""

STATEMENTS = [
    # 1) Clear data
    "TRUNCATE TABLE asistencias RESTART IDENTITY CASCADE;",
    "TRUNCATE TABLE permisos RESTART IDENTITY CASCADE;",
    "TRUNCATE TABLE vacaciones RESTART IDENTITY CASCADE;",

    # 2) Drop old columns (if they exist)
    "ALTER TABLE IF EXISTS vacaciones DROP COLUMN IF EXISTS medico_id;",
    "ALTER TABLE IF EXISTS permisos DROP COLUMN IF EXISTS medico_id;",
    "ALTER TABLE IF EXISTS asistencias DROP COLUMN IF EXISTS medico_id;",

    # 3) Add new usuario_id columns (if missing)
    "ALTER TABLE IF EXISTS vacaciones ADD COLUMN IF NOT EXISTS usuario_id INTEGER;",
    "ALTER TABLE IF EXISTS permisos ADD COLUMN IF NOT EXISTS usuario_id INTEGER;",
    "ALTER TABLE IF EXISTS asistencias ADD COLUMN IF NOT EXISTS usuario_id INTEGER;",

    # Set NOT NULL now that tables are empty
    "ALTER TABLE IF EXISTS vacaciones ALTER COLUMN usuario_id SET NOT NULL;",
    "ALTER TABLE IF EXISTS permisos ALTER COLUMN usuario_id SET NOT NULL;",
    "ALTER TABLE IF EXISTS asistencias ALTER COLUMN usuario_id SET NOT NULL;",

    # 4) Add FK constraints if not present (Postgres: need constraint names)
    # Use deterministic names so re-run is safe after dropping if exist
    "ALTER TABLE IF EXISTS vacaciones DROP CONSTRAINT IF EXISTS fk_vacaciones_usuario;",
    "ALTER TABLE IF EXISTS permisos DROP CONSTRAINT IF EXISTS fk_permisos_usuario;",
    "ALTER TABLE IF EXISTS asistencias DROP CONSTRAINT IF EXISTS fk_asistencias_usuario;",

    "ALTER TABLE IF EXISTS vacaciones ADD CONSTRAINT fk_vacaciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;",
    "ALTER TABLE IF EXISTS permisos ADD CONSTRAINT fk_permisos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;",
    "ALTER TABLE IF EXISTS asistencias ADD CONSTRAINT fk_asistencias_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;",
]


def run():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in STATEMENTS:
                conn.execute(text(stmt))
        print("RRHH migration completed: switched to usuario_id.")


if __name__ == "__main__":
    run()
