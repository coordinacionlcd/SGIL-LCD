import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

# Credenciales
url: str = os.getenv('SUPABASE_URL')
key: str = os.getenv('SUPABASE_KEY')         # ANON KEY
service_key: str = os.getenv('SUPABASE_SERVICE_KEY') # SERVICE ROLE

# Crear clientes
# Cliente normal
supabase: Client = create_client(url, key)

# Cliente ADMIN (Maestro)
supabase_admin: Client = create_client(url, service_key)