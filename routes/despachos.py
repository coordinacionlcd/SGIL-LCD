from flask import Blueprint, request, jsonify, render_template
from db import supabase_admin, supabase 
from helpers import render_page, login_required

despachos_bp = Blueprint('despachos', __name__)

# --- RUTAS PÚBLICAS (CLIENTE) ---

@despachos_bp.route('/solicitud-servicio')
def public_form():
    return render_template('solicitud_cliente.html')

@despachos_bp.route('/api/public/guardar-despacho', methods=['POST'])
def api_public_save():
    data = request.get_json()
    try:
        supabase_admin.table('despachos').insert({
            "cliente": data.get('cliente'),
            "equipo": data.get('equipo'),
            "fecha_solicitada": data.get('fecha_solicitada'),
            "direccion": data.get('direccion'),
            "contacto": data.get('contacto'),
            "telefono": data.get('telefono'),
            "estado": "pendiente"
        }).execute()
        return jsonify({"message": "Solicitud guardada"}), 200
    except Exception as e:
        print(f"Error guardando despacho público: {e}")
        return jsonify({"error": str(e)}), 400


# --- RUTAS PRIVADAS (COORDINACIÓN) ---

@despachos_bp.route('/despacho')
@login_required
def despacho_dashboard():
    """
    Panel interno para ver las solicitudes.
    """
    try:
        # CORRECCIÓN AQUÍ: Usamos supabase_admin (la llave maestra)
        # para que pueda leer la tabla aunque tenga restricciones RLS activas.
        response = supabase_admin.table('despachos').select("*").order('created_at', desc=True).execute()
        solicitudes = response.data
    except Exception as e:
        print(f"Error cargando despachos: {e}")
        solicitudes = []

    return render_page('despacho.html', solicitudes=solicitudes)