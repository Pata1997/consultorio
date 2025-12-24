from app import create_app, db
from app.models import *

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Usuario': Usuario,
        'Paciente': Paciente,
        'Especialidad': Especialidad,
        'Medico': Medico,
        'Cita': Cita,
        'Consulta': Consulta
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
