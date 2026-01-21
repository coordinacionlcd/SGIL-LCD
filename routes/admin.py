from flask import Blueprint, request, jsonify
from db import supabase, supabase_admin
from helpers import render_page, login_required, role_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/gestion-usuarios')
@login_required
def gestion_usuarios(): return render_page('gestion_usuarios.html')

# --- APIS DE ADMIN ---
@admin_bp.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    try:
        res = supabase.table('profiles').select("*").order('full_name').execute()
        return jsonify(res.data), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/admin/create-user', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_create_user():
    d = request.get_json()
    if len(d.get('password', '')) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
    try:
        attrs = {
            "email": d.get('email'), "password": d.get('password'), "email_confirm": True,
            "user_metadata": { "full_name": d.get('full_name'), "role": d.get('role') }
        }
        u = supabase_admin.auth.admin.create_user(attrs)
        return jsonify({"message": "Creado", "user": str(u)}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@admin_bp.route('/api/admin/update-user', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_update_user():
    d = request.get_json()
    uid = d.get('user_id')
    updates = {}
    if 'full_name' in d: updates['full_name'] = d['full_name']
    if 'role' in d: updates['role'] = d['role']
    try:
        supabase_admin.table('profiles').update(updates).eq('id', uid).execute()
        if 'role' in d or 'full_name' in d:
            meta = {}
            if 'role' in d: meta['role'] = d['role']
            if 'full_name' in d: meta['full_name'] = d['full_name']
            supabase_admin.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
        return jsonify({"message": "Actualizado"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@admin_bp.route('/api/admin/delete-user', methods=['POST'])
@login_required
@role_required(['administracion'])
def api_delete_user():
    d = request.get_json()
    try:
        supabase_admin.auth.admin.delete_user(d.get('user_id'))
        return jsonify({"message": "Eliminado"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@admin_bp.route('/api/admin/reset-user-password', methods=['POST'])
@login_required
@role_required(['administracion', 'coordinacion'])
def api_reset_password():
    d = request.get_json()
    try:
        supabase_admin.auth.admin.update_user_by_id(d.get('user_id'), {"password": d.get('new_password')})
        return jsonify({"message": "Contraseña restablecida"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400