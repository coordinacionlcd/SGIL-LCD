from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Leer la secret key del archivo .env
app.secret_key = os.getenv('SECRET_KEY')

# Leer credenciales de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Simulación de Base de Datos de Usuarios (Esto luego se conecta a Supabase/SQL)
USERS_DB = {
    "operario@sievert.com.co": {"name": "Operario", "role": "operario", "password": "123"},
    "comercial@sievert.com.co": {"name": "Comercial", "role": "comercial", "password": "123"},
    "admin@sievert.com.co": {"name": "coordinacion", "role": "administrador", "password": "123"}
}

# --- RUTAS DE ACCESO ---

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Aquí capturamos los datos del fetch de JS o del form
        data = request.get_json()
        email = data.get('email')
        # Nota: En producción, la validación de contraseña se hace con Hash
        # Aquí simulamos validación simple para el prototipo
        user = USERS_DB.get(email)
        
        if user:
            # Creamos la sesión del servidor
            session['user'] = email
            session['role'] = user['role']
            session['name'] = user['name']
            return jsonify({"success": True, "redirect": url_for('dashboard')})
        else:
            return jsonify({"success": False, "message": "Usuario no encontrado (Demo: usa admin@sievert.com.co)"}), 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- RUTAS DEL PANEL ---

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', 
                           user_name=session['name'], 
                           user_role=session['role'])

@app.route('/despacho', methods=['GET', 'POST'])
def despacho():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Lógica para guardar el formulario de despacho
        cliente = request.form.get('cliente')
        equipo = request.form.get('equipo')
        # Aquí iría la lógica para guardar en Supabase o SQL
        return jsonify({"success": True, "message": "Despacho registrado correctamente"})

    return render_template('despacho.html', user_role=session['role'])

if __name__ == '__main__':
    app.run(debug=True, port=5000)