from flask import Blueprint, request, jsonify, render_template
from db import supabase_admin, supabase
from helpers import render_page, login_required
import json

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
            # Datos Cliente
            "cliente": data.get('cliente'),
            "nit": data.get('nit'),
            "email": data.get('email'),
            "instrumento_contaminacion": data.get('instrumento_contaminacion'),
            "responsable_medicion": data.get('responsable_medicion'),
            "cargo": data.get('cargo'),
            "responsable_general": data.get('responsable_general'),
            "direccion": data.get('direccion'),
            "telefono": data.get('telefono'),
            
            # Datos Instrumento Referencia
            "ref_marca": data.get('ref_marca'),
            "ref_modelo": data.get('ref_modelo'),
            "ref_serie": data.get('ref_serie'),
            
            # Datos Equipos (Tabla JSON)
            "items": data.get('items'), # Supabase guardará esto como JSONB
            
            "fecha_solicitada": data.get('fecha_solicitada'), # Usamos la fecha de envio
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
    try:
        response = supabase_admin.table('despachos').select("*").order('created_at', desc=True).execute()
        solicitudes = response.data
    except Exception as e:
        print(f"Error cargando despachos: {e}")
        solicitudes = []

    return render_page('despacho.html', solicitudes=solicitudes)