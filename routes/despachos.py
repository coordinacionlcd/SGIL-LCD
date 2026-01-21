from flask import Blueprint, request, jsonify, render_template
from db import supabase_admin, supabase # Necesitamos admin para guardar lo público
from helpers import render_page, login_required

despachos_bp = Blueprint('despachos', __name__)

# --- RUTAS PÚBLICAS (CLIENTE) ---

@despachos_bp.route('/solicitud-servicio')
def public_form():
    """Ruta pública para que el cliente llene datos. NO TIENE login_required."""
    # Usamos render_template normal porque render_page inyecta cosas que el público no necesita saber
    return render_template('solicitud_cliente.html')

@despachos_bp.route('/api/public/guardar-despacho', methods=['POST'])
def api_public_save():
    """API pública para guardar el formulario."""
    data = request.get_json()
    try:
        # Usamos supabase_admin para saltarnos las restricciones de RLS
        # ya que el usuario 'anon' no tiene permiso de escribir normalmente.
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
    Aquí cargamos los datos de Supabase antes de renderizar.
    """
    try:
        # Traer todas las solicitudes ordenadas por fecha (más nuevas primero)
        response = supabase.table('despachos').select("*").order('created_at', desc=True).execute()
        solicitudes = response.data
    except Exception as e:
        print(f"Error cargando despachos: {e}")
        solicitudes = []

    return render_page('despacho.html', solicitudes=solicitudes)