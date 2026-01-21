from flask import Flask, redirect, url_for
import os
from dotenv import load_dotenv
from helpers import render_page

# Importar los "Blueprints"
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.despachos import despachos_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta')

# Registrar los Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(despachos_bp)

# --- RUTAS DE PLACEHOLDER ---
# AQUÍ ESTABA EL ERROR: Faltaba 'calibracion' y 'clientes'
rutas_faltantes = [
    'dosis_altas', 'relecturas', 'solicitudes', 'flujo_dosimetrico',
    'humedad_temperatura', 'indicadores_operativos', 'certificados_lcd',
    'indicadores_tecnicos', 'gestion_documental', 'indicadores',
    'indicadores_logisticos', 'actividad', 'niveles_investigacion',
    'calibracion', 'clientes' 
]

# Creamos rutas "dummy" dinámicamente
for ruta in rutas_faltantes:
    endpoint_name = ruta 
    url_path = f'/{ruta.replace("_", "-")}' 
    
    # Creamos la ruta
    app.add_url_rule(url_path, endpoint_name, lambda: render_page('base.html'))

# API dummy para el dashboard
@app.route('/api/dashboard/summary', methods=['GET'])
def api_dashboard_summary():
    from flask import jsonify
    return jsonify({"dosis_altas_pendientes": 0, "solicitudes_pendientes": 0})

# Redirección inicial
@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)