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
key: str = os.getenv('SUPABASE_KEY') # Esta es la ANON KEY (Pública)
service_key: str = os.getenv('SUPABASE_SERVICE_KEY') # Esta es la SERVICE ROLE (Secreta)

# Clientes Supabase
# Cliente normal (para lecturas públicas si las hubiera)
supabase: Client = create_client(url, key)
# Cliente ADMIN (para gestionar usuarios, perfiles y saltarse reglas de seguridad)
supabase_admin: Client = create_client(url, service_key)

# --- HELPER PARA RENDERIZAR (IMPORTANTE) ---
def render_page(template_name, **kwargs):
    """
    Renderiza la plantilla inyectando SIEMPRE las llaves de Supabase
    para que base.html y los scripts de JS funcionen.
    """
    return render_template(template_name, 
                         supabase_url=os.getenv('SUPABASE_URL'), 
                         supabase_key=os.getenv('SUPABASE_KEY'),
                         **kwargs)

# --- DECORADORES Y AYUDAS ---

def get_current_profile():
    """Obtiene el perfil del usuario actual desde la DB."""
    if 'user_id' not in session:
        return None
    try:
        # Usamos admin para asegurar lectura sin bloqueos RLS
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
                return render_page('base.html', error="Acceso denegado") # O redirigir
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==========================================
# RUTAS PRINCIPALES
# ==========================================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_page('login.html')

@app.route('/home')
@login_required
def home():
    return render_page('dashboard.html', profile=get_current_profile())

@app.route('/perfil')
@login_required
def perfil():
    return render_page('perfil.html')

@app.route('/gestion-usuarios')
@login_required
def gestion_usuarios():
    return render_page('gestion_usuarios.html')

@app.route('/despacho')
@login_required
def despacho():
    return render_page('despacho.html')

@app.route('/force-logout')
def force_logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# PLACEHOLDERS (PARA EVITAR ERRORES EN EL SIDEBAR)
# ==========================================
# Como copiaste el sidebar de otro proyecto, tiene enlaces a rutas que aquí no existen.
# Esto crea rutas vacías para que el código no falle al cargar.

rutas_faltantes = [
    'dosis_altas', 'relecturas', 'solicitudes', 'flujo_dosimetrico',
    'humedad_temperatura', 'indicadores_operativos', 'certificados_lcd',
    'indicadores_tecnicos', 'gestion_documental', 'indicadores',
    'indicadores_logisticos', 'actividad' # Agregado por si acaso
]

for ruta in rutas_faltantes:
    # Creamos una función dinámica para cada ruta faltante
    app.add_url_rule(f'/{ruta.replace("_", "-")}', ruta, 
                     lambda: render_page('base.html'), methods=['GET'])

# Parche especial para "dosimetria_automata" que es un Blueprint en el otro proyecto
bp_automata = Blueprint('dosimetria_automata', __name__)
@bp_automata.route('/')
def index(): return render_page('base.html')
@bp_automata.route('/niveles')
def gestionar_niveles(): return render_page('base.html')

app.register_blueprint(bp_automata, url_prefix='/automata')


# ==========================================
# APIS (BACKEND JSON)
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
    """Devuelve el perfil al Frontend (JS)."""
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
        
        # Actualizamos también la sesión
        session['name'] = data.get('full_name')
        
        return jsonify({"message": "Perfil actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    new_password = data.get('new_password')
    try:
        # Actualiza contraseña usando el cliente admin
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
    # Placeholder: Devuelve lista vacía por ahora
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
        return jsonify({"error": "Error al crear usuario. Verifica el email."}), 400

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
        
        # 2. Sincronizar metadata de Auth
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
    # Placeholder: Conecta aquí tus conteos reales en el futuro
    return jsonify({
        "dosis_altas_pendientes": 0,
        "solicitudes_pendientes": 0
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)