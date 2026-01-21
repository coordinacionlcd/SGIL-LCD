import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
        # 1. Guardar en Base de Datos (Sin dirección, ciudad, ni teléfono)
        supabase_admin.table('despachos').insert({
            "cliente": data.get('cliente'),
            "nit": data.get('nit'),
            "email": data.get('email'),
            "responsable_medicion": data.get('responsable_medicion'),
            "cargo": data.get('cargo'),
            
            # Dirección, Ciudad y Teléfono eliminados de aquí
            
            "ref_marca": data.get('ref_marca'),
            "ref_modelo": data.get('ref_modelo'),
            "ref_serie": data.get('ref_serie'),
            "items": data.get('items'),
            "fecha_solicitada": data.get('fecha_solicitada'),
            "instrumento_contaminacion": data.get('instrumento_contaminacion'),
            "estado": "pendiente"
        }).execute()

        # 2. ENVIAR CORREOS
        try:
            send_notification_emails(data)
        except Exception as mail_error:
            print(f"Error enviando correos: {mail_error}")

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


# ==========================================
#  FUNCIÓN DE ENVÍO DE CORREOS
# ==========================================
def send_notification_emails(data):
    smtp_server = os.getenv('MAIL_SERVER')
    smtp_port = os.getenv('MAIL_PORT')
    sender_email = os.getenv('MAIL_USERNAME')
    sender_password = os.getenv('MAIL_PASSWORD')
    logistics_email = os.getenv('MAIL_LOGISTICS')

    if not all([smtp_server, sender_email, sender_password]):
        print("Faltan configuraciones de correo en .env")
        return

    # 1. CORREO INTERNO (LOGÍSTICA + DIANA)
    recipients_internal = [logistics_email, sender_email]
    
    msg_internal = MIMEMultipart()
    msg_internal['Subject'] = f"🚚 NUEVA RECOLECCIÓN - {data.get('cliente')}"
    msg_internal['From'] = f"Sievert Sistema <{sender_email}>"
    msg_internal['To'] = ", ".join(recipients_internal)

    # HTML Logística Actualizado (Sin campos eliminados)
    html_internal = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="background-color: #003366; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0;">⚠️ Nueva Solicitud de Recolección</h2>
                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">Acción Requerida - Equipo Logístico</p>
            </div>
            <div style="padding: 30px;">
                <div style="background-color: #f8fafc; border-left: 4px solid #52277c; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                    <h3 style="color: #003366; margin-top: 0; margin-bottom: 15px; font-size: 16px;">📦 Datos del Cliente</h3>
                    <p style="margin: 5px 0;"><strong>🏢 Cliente:</strong> {data.get('cliente')}</p>
                    <p style="margin: 5px 0;"><strong>🆔 NIT:</strong> {data.get('nit')}</p>
                </div>
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px; font-size: 15px;">👤 Contacto en Sitio</h3>
                    <ul style="list-style: none; padding: 0; color: #333;">
                        <li style="margin-bottom: 8px;">• <strong>Nombre:</strong> {data.get('responsable_medicion')} ({data.get('cargo')})</li>
                        <li style="margin-bottom: 8px;">• <strong>Email:</strong> {data.get('email')}</li>
                    </ul>
                </div>
                <div>
                    <h3 style="color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px; font-size: 15px;">☢️ Equipos a Recoger: {len(data.get('items', []))}</h3>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr style="background-color: #eee;">
                            <th style="padding: 8px; text-align: left;">Marca</th>
                            <th style="padding: 8px; text-align: left;">Modelo</th>
                            <th style="padding: 8px; text-align: left;">Serie</th>
                        </tr>
                        {''.join([f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;">{i.get("marca")}</td><td style="padding: 8px; border-bottom: 1px solid #eee;">{i.get("modelo")}</td><td style="padding: 8px; border-bottom: 1px solid #eee;">{i.get("serie")}</td></tr>' for i in data.get('items', [])])}
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    msg_internal.attach(MIMEText(html_internal, 'html'))

    # 2. CORREO AL CLIENTE
    client_email = data.get('email')
    
    with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        
        server.sendmail(sender_email, recipients_internal, msg_internal.as_string())
        
        if client_email:
            msg_client = MIMEMultipart()
            msg_client['Subject'] = f"✅ Solicitud Recibida - Sievert LCD"
            msg_client['From'] = f"Sievert LCD <{sender_email}>"
            msg_client['To'] = client_email

            html_client = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 0;">
                <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="background-color: #52277c; color: white; padding: 25px; text-align: center;">
                        <h1 style="margin: 0; font-size: 22px;">¡Solicitud Recibida!</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">Hemos registrado su información correctamente.</p>
                    </div>
                    <div style="padding: 30px;">
                        <p style="color: #333; font-size: 16px;">Hola <strong>{data.get('responsable_medicion')}</strong>,</p>
                        <p style="color: #555; line-height: 1.5;">
                            Confirmamos que hemos recibido la información técnica y de contaminación para <strong>{len(data.get('items', []))} equipos</strong>.
                            Nuestro equipo logístico ha sido notificado y procederá con la programación de la recolección.
                        </p>
                        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 6px; margin: 20px 0;">
                            <strong style="color: #166534; display: block; margin-bottom: 5px;">📋 Resumen de Equipos Registrados:</strong>
                            <ul style="margin: 0; padding-left: 20px; color: #14532d;">
                                {''.join([f'<li>{i.get("marca")} {i.get("modelo")} (SN: {i.get("serie")})</li>' for i in data.get('items', [])])}
                            </ul>
                        </div>
                        <p style="color: #666; font-size: 13px; text-align: center; margin-top: 30px;">
                            Si tienes alguna duda, contacta a Coordinación:<br>
                            <strong style="color: #52277c;">(+57) 317 638 8661</strong>
                        </p>
                    </div>
                    <div style="background-color: #eee; padding: 15px; text-align: center; font-size: 11px; color: #888;">
                        Sievert LCD - Laboratorio de Calibración Dosimétrica<br>
                        Este es un mensaje automático, por favor no responder.
                    </div>
                </div>
            </body>
            </html>
            """
            msg_client.attach(MIMEText(html_client, 'html'))
            server.sendmail(sender_email, client_email, msg_client.as_string())