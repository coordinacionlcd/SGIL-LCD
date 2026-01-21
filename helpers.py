import os
from flask import render_template, session, redirect, url_for
from functools import wraps
from db import supabase_admin # Importamos la conexión desde db.py

# --- 1. RENDERIZADOR BLINDADO ---
def render_page(template_name, **kwargs):
    """Renderiza inyectando siempre las llaves de Supabase."""
    return render_template(template_name, 
                         supabase_url=os.getenv('SUPABASE_URL'), 
                         supabase_key=os.getenv('SUPABASE_KEY'),
                         **kwargs)

# --- 2. OBTENER PERFIL ---
def get_current_profile():
    if 'user_id' not in session: return None
    try:
        response = supabase_admin.table('profiles').select("*").eq('id', session['user_id']).execute()
        if response.data: return response.data[0]
    except Exception as e:
        print(f"Error perfil: {e}")
    return None

# --- 3. DECORADORES DE SEGURIDAD ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('auth.login')) # Nota: 'auth.login'
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            profile = get_current_profile()
            if not profile or profile.get('role') not in allowed_roles:
                return render_page('base.html', error="Acceso denegado")
            return f(*args, **kwargs)
        return decorated_function
    return decorator