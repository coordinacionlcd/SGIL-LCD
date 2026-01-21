from flask import Blueprint, session, request, redirect, url_for, jsonify
from db import supabase, supabase_admin
from helpers import render_page, login_required, get_current_profile

# Definimos el "Blueprint" (El módulo)
auth_bp = Blueprint('auth', __name__)

# --- VISTAS (PÁGINAS) ---
@auth_bp.route('/')
def index(): return redirect(url_for('auth.login'))

@auth_bp.route('/login')
def login():
    if 'user_id' in session: return redirect(url_for('auth.home'))
    return render_page('login.html')

@auth_bp.route('/home')
@login_required
def home(): return render_page('dashboard.html', profile=get_current_profile())

@auth_bp.route('/perfil')
@login_required
def perfil(): return render_page('perfil.html')

@auth_bp.route('/force-logout')
def force_logout():
    session.clear()
    return redirect(url_for('auth.login'))

# --- APIS (BACKEND) ---
@auth_bp.route('/api/set-session', methods=['POST'])
def api_set_session():
    data = request.get_json()
    token = data.get('access_token')
    try:
        user = supabase.auth.get_user(token)
        if user:
            uid = user.user.id
            session['user_id'] = uid
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

@auth_bp.route('/api/session', methods=['GET'])
def api_session():
    p = get_current_profile()
    if p: return jsonify({"profile": p}), 200
    return jsonify({"error": "No session"}), 401

@auth_bp.route('/api/profile', methods=['GET'])
@login_required
def api_profile():
    return jsonify(get_current_profile())

@auth_bp.route('/api/profile/update', methods=['POST'])
@login_required
def api_profile_update():
    data = request.get_json()
    try:
        supabase_admin.table('profiles').update({
            "full_name": data.get('full_name')
        }).eq('id', session['user_id']).execute()
        session['name'] = data.get('full_name')
        return jsonify({"message": "Perfil actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route('/api/profile/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    new_pass = data.get('new_password')
    if not new_pass or len(new_pass) < 6:
        return jsonify({"error": "Mínimo 6 caracteres"}), 400
    try:
        supabase_admin.auth.admin.update_user_by_id(session['user_id'], {"password": new_pass})
        return jsonify({"message": "Contraseña actualizada"}), 200
    except Exception as e:
        return jsonify({"error": "Error al actualizar"}), 400