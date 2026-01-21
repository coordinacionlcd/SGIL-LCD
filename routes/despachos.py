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

    # HTML Logística (Solo Cliente, NIT y Cantidad de Equipos - Estilo Tarjeta Elegante)
    html_internal = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 40px 0;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.08); border: 1px solid #e0e0e0;">
            
            <div style="background-color: #003366; color: white; padding: 30px 20px; text-align: center;">
                <h2 style="margin: 0; font-size: 24px; font-weight: 600;">⚠️ Solicitud de Recolección</h2>
                <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.8; letter-spacing: 0.5px;">ACCIÓN REQUERIDA - EQUIPO LOGÍSTICO</p>
            </div>

            <div style="padding: 40px 30px;">
                
                <div style="background-color: #ffffff; border: 1px solid #eef1f5; border-radius: 10px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                    <h3 style="color: #003366; margin-top: 0; margin-bottom: 20px; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">
                        📦 Datos Generales
                    </h3>
                    <div style="margin-bottom: 12px;">
                        <span style="display: block; font-size: 12px; color: #888; text-transform: uppercase;">Cliente</span>
                        <span style="display: block; font-size: 18px; color: #333; font-weight: 600;">{data.get('cliente')}</span>
                    </div>
                    <div>
                        <span style="display: block; font-size: 12px; color: #888; text-transform: uppercase;">NIT</span>
                        <span style="display: block; font-size: 16px; color: #555;">{data.get('nit')}</span>
                    </div>
                </div>

                <div style="background-color: #e8f4fd; color: #0c5460; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #b8daff;">
                    <span style="display: block; font-size: 14px; margin-bottom: 5px; font-weight: 600;">TOTAL EQUIPOS A RECOGER</span>
                    <span style="display: block; font-size: 32px; font-weight: 700; color: #003366;">{len(data.get('items', []))}</span>
                </div>

            </div>
            
            <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee;">
                Sistema de Gestión Logística - Sievert LCD
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
        
        # Enviar Interno
        server.sendmail(sender_email, recipients_internal, msg_internal.as_string())
        
        # Enviar a Cliente
        if client_email:
            msg_client = MIMEMultipart()
            msg_client['Subject'] = f"✅ Solicitud Recibida - Sievert LCD"
            msg_client['From'] = f"Sievert LCD <{sender_email}>"
            msg_client['To'] = client_email

            # Link al logo (Asegúrate que este link sea accesible públicamente)
            logo_url = "https://coordinacionlcd.pythonanywhere.com/static/img/Logo_LCD.png"

            html_client = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 40px 0;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.08); border: 1px solid #e0e0e0;">
                    
                    <div style="text-align: center; padding: 30px 20px; background-color: #ffffff; border-bottom: 1px solid #f0f0f0;">
                         <img src="{logo_url}" alt="Sievert LCD" style="max-height: 70px; width: auto; display: block; margin: 0 auto;">
                    </div>

                    <div style="background: linear-gradient(135deg, #52277c 0%, #3a1b59 100%); color: white; padding: 30px 20px; text-align: center;">
                        <h1 style="margin: 0; font-size: 24px; font-weight: 600;">¡Solicitud Recibida!</h1>
                        <p style="margin: 10px 0 0 0; font-size: 15px; opacity: 0.9; font-weight: 300;">Hemos registrado su información correctamente.</p>
                    </div>

                    <div style="padding: 40px 30px;">
                        <p style="color: #333; font-size: 16px; margin-top: 0;">Hola <strong>{data.get('responsable_medicion')}</strong>,</p>
                        <p style="color: #555; line-height: 1.6; font-size: 15px;">
                            Confirmamos que hemos recibido la información técnica y de contaminación para <strong>{len(data.get('items', []))} equipos</strong>.
                            Nuestro equipo logístico ha sido notificado y procederá con la programación de la recolección.
                        </p>
                        
                        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 20px; border-radius: 10px; margin: 25px 0;">
                            <strong style="color: #166534; display: block; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">📋 Resumen de Equipos Registrados:</strong>
                            <ul style="margin: 0; padding-left: 20px; color: #14532d; font-size: 14px; line-height: 1.6;">
                                {''.join([f'<li>{i.get("marca")} {i.get("modelo")} (SN: {i.get("serie")})</li>' for i in data.get('items', [])])}
                            </ul>
                        </div>

                        <div style="text-align: center; margin-top: 35px; border-top: 1px solid #f0f0f0; padding-top: 25px;">
                            <p style="color: #888; font-size: 13px; margin-bottom: 10px;">¿Tienes alguna duda?</p>
                            <p style="margin: 0; color: #52277c; font-size: 15px;">
                                Contacta a Coordinación:<br>
                                <strong style="font-size: 16px; display: block; margin-top: 5px;">Diana Ortegón Pineda</strong>
                                <span style="font-weight: 600;">(+57) 317 638 8661</span>
                            </p>
                        </div>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 11px; color: #aaa; border-top: 1px solid #eee;">
                        &copy; Sievert LCD - Laboratorio de Calibración Dosimétrica<br>
                        Este es un mensaje automático, por favor no responder.
                    </div>
                </div>
            </body>
            </html>
            """
            msg_client.attach(MIMEText(html_client, 'html'))
            server.sendmail(sender_email, client_email, msg_client.as_string())