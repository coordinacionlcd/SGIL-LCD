from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# --- CONFIGURACIÓN INICIAL ---
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Credenciales Supabase
url: str = os.getenv('SUPABASE_URL')
key: str = os.getenv('SUPABASE_KEY')
service_key: str = os.getenv('SUPABASE_SERVICE_KEY')

# Clientes Supabase
supabase: Client = create_client(url, key)
supabase_admin: Client = create_client(url, service_key)

# --- DECORADORES Y AYUDAS ---

def get_current_profile():
    """Obtiene el perfil del usuario actual."""
    if 'user_id' not in session:
        return None
    try:
        # CAMBIO AQUÍ: Usamos supabase_admin en vez de supabase
        response = supabase_admin.table('profiles').select("*").eq('id', session['user_id']).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"Error obteniendo perfil: {e}")
    return None

def login_required(f):
    """Protege las rutas para usuarios logueados."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """Restringe el acceso según el rol del usuario."""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            profile = get_current_profile()
            if not profile or profile.get('role') not in allowed_roles:
                return jsonify({"error": "Acceso denegado. Rol no autorizado."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==========================================
# RUTAS DE VISTAS (PÁGINAS HTML)
# ==========================================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    # CORRECCIÓN: Usamos 'SUPABASE_KEY' que es como la tienes en tu .env
    return render_template('login.html', 
                         supabase_url=os.getenv('SUPABASE_URL'), 
                         supabase_key=os.getenv('SUPABASE_KEY'))

@app.route('/home')
@login_required
def home():
    return render_template('dashboard.html', profile=get_current_profile())

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html')

@app.route('/gestion-usuarios')
@login_required
def gestion_usuarios():
    # Solo roles administrativos deberían entrar aquí
    return render_template('gestion_usuarios.html')

@app.route('/despacho')
@login_required
def despacho():
    """Módulo funcional: Formulario de Despacho."""
    return render_template('despacho.html')

# ==========================================
# APIS (ENDPOINTS PARA JAVASCRIPT)
# ==========================================

# --- 1. SESIÓN Y AUTH ---

@app.route('/api/set-session', methods=['POST'])
def api_set_session():
    """Crea la sesión en Flask guardando ID, Nombre y Rol."""
    data = request.get_json()
    access_token = data.get('access_token')
    
    try:
        # 1. Verificar token con Supabase
        user = supabase.auth.get_user(access_token)
        if user:
            user_id = user.user.id
            session['user_id'] = user_id

            # 2. BUSCAR PERFIL (Nombre y Rol) PARA LA SESIÓN
            # Usamos admin para asegurar que podamos leer los datos
            try:
                profile_resp = supabase_admin.table('profiles').select('*').eq('id', user_id).execute()
                if profile_resp.data:
                    profile = profile_resp.data[0]
                    session['name'] = profile.get('full_name', 'Usuario')
                    session['role'] = profile.get('role', 'invitado')
                else:
                    session['name'] = 'Usuario'
                    session['role'] = 'invitado'
            except Exception as e:
                print(f"Error cargando datos de sesión: {e}")
                session['name'] = 'Usuario'
                session['role'] = 'invitado'

            return jsonify({"message": "Sesión establecida"}), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 401
        
    return jsonify({"error": "Token inválido"}), 401

@app.route('/api/session', methods=['GET'])
def api_session():
    """Verifica sesión activa y devuelve perfil."""
    profile = get_current_profile()
    if profile:
        return jsonify({"profile": profile}), 200
    return jsonify({"error": "No session"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

# --- 2. PERFIL DE USUARIO ---

@app.route('/api/profile', methods=['GET'])
@login_required
def api_profile():
    profile = get_current_profile()
    return jsonify(profile)

@app.route('/api/profile/update', methods=['POST'])
@login_required
def api_profile_update():
    data = request.get_json()
    try:
        supabase.table('profiles').update({
            "full_name": data.get('full_name')
        }).eq('id', session['user_id']).execute()
        return jsonify({"message": "Perfil actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    new_password = data.get('new_password')
    try:
        # Actualiza contraseña usando el cliente admin para evitar restricciones
        supabase_admin.auth.admin.update_user_by_id(session['user_id'], {"password": new_password})
        return jsonify({"message": "Contraseña actualizada exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- 3. GESTIÓN DE USUARIOS (ADMIN) ---

@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    try:
        response = supabase.table('profiles').select("*").order('full_name').execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user-records/<user_id>', methods=['GET'])
@login_required
def api_user_records(user_id):
    """Devuelve historial de actividad (Placeholder por ahora)."""
    # Aquí consultarías tu tabla de logs/bitácora real en el futuro.
    return jsonify([]), 200 

@app.route('/api/admin/create-user', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_create_user():
    data = request.get_json()
    try:
        attributes = {
            "email": data.get('email'),
            "password": data.get('password'),
            "email_confirm": True,
            "user_metadata": {
                "full_name": data.get('full_name'),
                "role": data.get('role')
            }
        }
        user = supabase_admin.auth.admin.create_user(attributes)
        return jsonify({"message": "Usuario creado", "user": str(user)}), 200
    except Exception as e:
        return jsonify({"error": "Error al crear usuario. Posiblemente el email ya existe."}), 400

@app.route('/api/admin/update-user', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_update_user():
    data = request.get_json()
    user_id = data.get('user_id')
    updates = {}
    
    if 'full_name' in data: updates['full_name'] = data['full_name']
    if 'role' in data: updates['role'] = data['role']
    if 'is_active' in data: updates['is_active'] = data['is_active']

    try:
        # 1. Actualizar perfil en tabla
        supabase.table('profiles').update(updates).eq('id', user_id).execute()
        
        # 2. Sincronizar metadata de Auth si cambia rol/nombre
        if 'role' in data or 'full_name' in data:
            meta = {}
            if 'role' in data: meta['role'] = data['role']
            if 'full_name' in data: meta['full_name'] = data['full_name']
            supabase_admin.auth.admin.update_user_by_id(user_id, {"user_metadata": meta})
            
        return jsonify({"message": "Usuario actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/admin/delete-user', methods=['POST'])
@login_required
@role_required(['administracion'])
def api_delete_user():
    data = request.get_json()
    try:
        supabase_admin.auth.admin.delete_user(data.get('user_id'))
        return jsonify({"message": "Usuario eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/admin/reset-user-password', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_reset_password():
    data = request.get_json()
    try:
        supabase_admin.auth.admin.update_user_by_id(
            data.get('user_id'), 
            {"password": data.get('new_password')}
        )
        return jsonify({"message": "Contraseña restablecida"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- 4. DASHBOARD DATA ---

@app.route('/api/dashboard/summary', methods=['GET'])
@login_required
def api_dashboard_summary():
    """Datos resumidos para los contadores del dashboard."""
    # Aquí puedes conectar conteos reales de la tabla 'despachos' cuando la crees
    return jsonify({
        "dosis_altas_pendientes": 0,
        "solicitudes_pendientes": 0
    })

@app.route('/force-logout')
def force_logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)