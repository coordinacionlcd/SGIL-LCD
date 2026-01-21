from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Blueprint
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# --- CONFIGURACIÓN INICIAL ---
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_key_default')

# Credenciales Supabase
url: str = os.getenv('SUPABASE_URL')
key: str = os.getenv('SUPABASE_KEY') # ANON KEY (Pública)
service_key: str = os.getenv('SUPABASE_SERVICE_KEY') # SERVICE ROLE (Secreta)

# Clientes Supabase
supabase: Client = create_client(url, key)
supabase_admin: Client = create_client(url, service_key)

# --- HELPER PARA RENDERIZAR ---
def render_page(template_name, **kwargs):
    """Inyecta siempre las llaves de Supabase para el Frontend."""
    return render_template(template_name, 
                         supabase_url=os.getenv('SUPABASE_URL'), 
                         supabase_key=os.getenv('SUPABASE_KEY'),
                         **kwargs)

# --- DECORADORES ---
def get_current_profile():
    if 'user_id' not in session: return None
    try:
        # Usamos admin para leer sin bloqueos
        response = supabase_admin.table('profiles').select("*").eq('id', session['user_id']).execute()
        if response.data: return response.data[0]
    except Exception as e:
        print(f"Error perfil: {e}")
    return None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            profile = get_current_profile()
            if not profile or profile.get('role') not in allowed_roles:
                return render_page('base.html', error="Acceso denegado")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ================= RUTAS DE VISTAS =================
@app.route('/')
def index(): return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'user_id' in session: return redirect(url_for('home'))
    return render_page('login.html')

@app.route('/home')
@login_required
def home(): return render_page('dashboard.html', profile=get_current_profile())

@app.route('/perfil')
@login_required
def perfil(): return render_page('perfil.html')

@app.route('/gestion-usuarios')
@login_required
def gestion_usuarios(): return render_page('gestion_usuarios.html')

@app.route('/despacho')
@login_required
def despacho(): return render_page('despacho.html')

@app.route('/force-logout')
def force_logout():
    session.clear()
    return redirect(url_for('login'))

# ================= PLACEHOLDERS =================
rutas_faltantes = [
    'dosis_altas', 'relecturas', 'solicitudes', 'flujo_dosimetrico',
    'humedad_temperatura', 'indicadores_operativos', 'certificados_lcd',
    'indicadores_tecnicos', 'gestion_documental', 'indicadores',
    'indicadores_logisticos', 'actividad', 'niveles_investigacion'
]
for ruta in rutas_faltantes:
    app.add_url_rule(f'/{ruta.replace("_", "-")}', ruta, lambda: render_page('base.html'), methods=['GET'])

bp_automata = Blueprint('dosimetria_automata', __name__)
@bp_automata.route('/')
def index(): return render_page('base.html')
@bp_automata.route('/niveles')
def gestionar_niveles(): return render_page('base.html')
app.register_blueprint(bp_automata, url_prefix='/automata')


# ================= APIS (BACKEND) =================

# 1. AUTH
@app.route('/api/set-session', methods=['POST'])
def api_set_session():
    data = request.get_json()
    token = data.get('access_token')
    try:
        user = supabase.auth.get_user(token)
        if user:
            uid = user.user.id
            session['user_id'] = uid
            # Buscar perfil con ADMIN para evitar errores de permisos
            try:
                prof = supabase_admin.table('profiles').select('*').eq('id', uid).execute()
                p_data = prof.data[0] if prof.data else {}
                session['name'] = p_data.get('full_name', 'Usuario')
                session['role'] = p_data.get('role', 'invitado')
            except:
                session['name'] = 'Usuario'
                session['role'] = 'invitado'
            return jsonify({"message": "OK"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401
    return jsonify({"error": "Token inválido"}), 401

@app.route('/api/session', methods=['GET'])
def api_session():
    p = get_current_profile()
    if p: return jsonify({"profile": p}), 200
    return jsonify({"error": "No session"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"message": "Bye"}), 200


# 2. PERFIL (AQUÍ ESTABA EL ERROR)

@app.route('/api/profile', methods=['GET'])
@login_required
def api_profile():
    return jsonify(get_current_profile())

@app.route('/api/profile/update', methods=['POST'])
@login_required
def api_profile_update():
    data = request.get_json()
    try:
        # CORRECCIÓN: Usar supabase_admin para asegurar permiso de escritura
        supabase_admin.table('profiles').update({
            "full_name": data.get('full_name')
        }).eq('id', session['user_id']).execute()
        
        # Actualizar la sesión en vivo
        session['name'] = data.get('full_name')
        
        return jsonify({"message": "Perfil actualizado correctamente"}), 200
    except Exception as e:
        print(f"Error update profile: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    new_pass = data.get('new_password')
    
    if not new_pass or len(new_pass) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400

    try:
        # CORRECCIÓN: Usar supabase_admin explícito para cambiar contraseña
        supabase_admin.auth.admin.update_user_by_id(
            session['user_id'], 
            {"password": new_pass}
        )
        return jsonify({"message": "Contraseña actualizada. Úsala en tu próximo ingreso."}), 200
    except Exception as e:
        print(f"Error password: {e}")
        return jsonify({"error": "Error al actualizar contraseña. Intenta de nuevo."}), 400


# 3. GESTIÓN USUARIOS (ADMIN)
@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    try:
        res = supabase.table('profiles').select("*").order('full_name').execute()
        return jsonify(res.data), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/user-records/<user_id>', methods=['GET'])
@login_required
def api_user_records(user_id): return jsonify([]), 200 

@app.route('/api/admin/create-user', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_create_user():
    d = request.get_json()
    try:
        attrs = {
            "email": d.get('email'), "password": d.get('password'), "email_confirm": True,
            "user_metadata": { "full_name": d.get('full_name'), "role": d.get('role') }
        }
        u = supabase_admin.auth.admin.create_user(attrs)
        return jsonify({"message": "Creado", "user": str(u)}), 200
    except Exception as e: return jsonify({"error": "Error creando usuario (¿Email repetido?)"}), 400

@app.route('/api/admin/update-user', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_update_user():
    d = request.get_json()
    uid = d.get('user_id')
    updates = {}
    if 'full_name' in d: updates['full_name'] = d['full_name']
    if 'role' in d: updates['role'] = d['role']
    if 'is_active' in d: updates['is_active'] = d['is_active']

    try:
        supabase_admin.table('profiles').update(updates).eq('id', uid).execute()
        if 'role' in d or 'full_name' in d:
            meta = {}
            if 'role' in d: meta['role'] = d['role']
            if 'full_name' in d: meta['full_name'] = d['full_name']
            supabase_admin.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
        return jsonify({"message": "Actualizado"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/admin/delete-user', methods=['POST'])
@login_required
@role_required(['administracion'])
def api_delete_user():
    d = request.get_json()
    try:
        supabase_admin.auth.admin.delete_user(d.get('user_id'))
        return jsonify({"message": "Eliminado"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/admin/reset-user-password', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_reset_password():
    d = request.get_json()
    try:
        supabase_admin.auth.admin.update_user_by_id(d.get('user_id'), {"password": d.get('new_password')})
        return jsonify({"message": "Contraseña restablecida"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/dashboard/summary', methods=['GET'])
@login_required
def api_dashboard_summary(): return jsonify({"dosis_altas_pendientes": 0, "solicitudes_pendientes": 0})

if __name__ == '__main__':
    app.run(debug=True, port=5000)