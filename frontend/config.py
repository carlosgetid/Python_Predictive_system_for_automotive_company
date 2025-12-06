import os
import json
from pathlib import Path

# --- Configuración del Servidor Backend ---
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# URLs de Endpoints
URL_LOGIN = f"{BASE_URL}/login" # --- NUEVO: Endpoint de autenticación
URL_UPLOAD = f"{BASE_URL}/upload"
URL_PREDICT = f"{BASE_URL}/predict"
URL_RETRAIN = f"{BASE_URL}/api/v1/trigger_retraining"
URL_METRICS = f"{BASE_URL}/api/v1/metrics"

# --- Gestión Dinámica de Configuración (Settings) ---
# Ruta absoluta al archivo settings.json (en la misma carpeta que este script)
SETTINGS_PATH = Path(__file__).parent / "settings.json"

def get_setting(key, default=None):
    """
    Lee un valor de configuración desde settings.json.
    Si hay error o no existe, devuelve el valor default.
    """
    if not SETTINGS_PATH.exists():
        return default
    
    try:
        with open(SETTINGS_PATH, "r") as f:
            data = json.load(f)
            return data.get(key, default)
    except Exception as e:
        print(f"Error leyendo configuración: {e}")
        return default

def update_setting(key, value):
    """
    Actualiza un valor en settings.json y guarda el archivo.
    """
    data = {}
    # 1. Leer estado actual (si existe)
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r") as f:
                data = json.load(f)
        except Exception:
            data = {} # Si está corrupto, empezamos de nuevo

    # 2. Actualizar valor
    data[key] = value

    # 3. Guardar cambios
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error guardando configuración: {e}")
        return False

# --- Variables de Acceso Rápido ---
# Estas variables se cargan al iniciar, pero para valores que cambian
# en tiempo real (como flags), es mejor llamar a get_setting() directamente.

# Por compatibilidad inicial, leemos el valor al cargar el módulo:
MOSTRAR_CARGA_MANUAL = get_setting("MOSTRAR_CARGA_MANUAL", True)

# --- Estilos CSS (UI Hacks) ---
# CSS para ocultar la barra lateral en la pantalla de Login
HIDE_SIDEBAR_CSS = """
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    /* Opcional: Ocultar también el botón de colapsar sidebar para que sea totalmente invisible */
    [data-testid="collapsedControl"] {
        display: none;
    }
</style>
"""

# --- CSS Dinámico por Rol (RBAC Visual) ---
def get_role_based_sidebar_css(role):
    """
    Genera CSS para ocultar pestañas de navegación según el perfil del usuario.
    Se basa en selectores de atributos href que coincidan con los nombres de archivo.
    """
    if role == "Vendedora":
        # Ana (Vendedora) solo debe ver "Visualizacion_de_Prediccion".
        # Ocultamos explícitamente las otras 3 páginas.
        return """
        <style>
            /* Ocultar enlace a Carga de Datos */
            [data-testid="stSidebarNav"] a[href*="Carga_de_Datos"] { display: none !important; }
            
            /* Ocultar enlace a Administración */
            [data-testid="stSidebarNav"] a[href*="Administracion"] { display: none !important; }
            
            /* Ocultar enlace a Configuración */
            [data-testid="stSidebarNav"] a[href*="Configuracion"] { display: none !important; }
        </style>
        """
    # Si es otro rol (Administrador, Logística, etc.), no ocultamos nada (retorna string vacío)
    return ""