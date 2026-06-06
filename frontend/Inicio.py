import streamlit as st
import requests
import time
import os
import sys
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN Y ESTILOS ---
try:
    from frontend.config import URL_LOGIN, get_role_based_sidebar_css
    # [NUEVO] Importamos el motor de estilos
    from frontend.styles import get_app_css, render_sidebar_profile
except ImportError:
    # Fallback
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
    URL_LOGIN = f"http://{BACKEND_HOST}:{BACKEND_PORT}/login"
    def get_role_based_sidebar_css(role): return ""
    def get_app_css(): return ""
    def render_sidebar_profile(): pass

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Teo Analytics - Inicio",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- INYECCIÓN DE CSS GLOBAL ---
st.markdown(get_app_css(), unsafe_allow_html=True)

# --- GESTIÓN DE ESTADO DE SESIÓN (Persistencia con st.context.cookies) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

# Intentar recuperar sesión desde las cookies de forma síncrona
if not st.session_state.authenticated:
    if st.session_state.get('logout_requested', False):
        # Si se acaba de cerrar sesión, ignoramos las cookies para no re-autenticar
        pass
    else:
        try:
            cookies = st.context.cookies
            auth_cookie = cookies.get("auth_token")
            user_cookie = cookies.get("user_data")
            
            if auth_cookie and user_cookie:
                import ast
                user_data = ast.literal_eval(user_cookie)
                st.session_state.token = auth_cookie
                st.session_state.user = user_data
                st.session_state.authenticated = True
        except Exception:
            pass


# --- DEFINICIÓN DE PÁGINAS COMUNES ---
page_login  = st.Page("pages/login.py", title="Login", icon="🔑", url_path="login")
page_inicio = st.Page("pages/0_Dashboard.py", title="Inicio", icon="🏠", url_path="inicio")
page_carga  = st.Page("pages/1_Carga_de_Datos.py",   title="Carga de Datos", url_path="carga")
page_ingesta= st.Page("pages/2_Ingesta_de_Datos.py",  title="Ingesta de Datos", url_path="ingesta")
page_admin  = st.Page("pages/2_Administracion.py",    title="Administracion", url_path="admin")
page_vis    = st.Page("pages/3_Visualizacion_de_Prediccion.py", title="Visualizacion de Prediccion", url_path="prediccion")
page_config = st.Page("pages/4_Configuracion.py",     title="Configuracion", url_path="configuracion")
page_error  = st.Page("pages/error.py", title="Error 403", url_path="error")

# --- CONTROLADOR PRINCIPAL ---
if not st.session_state.authenticated:
    # Registramos todas las páginas para evitar el popup "Page not found" al hacer Ctrl+R
    # El primer elemento de la lista es la página por defecto
    pg = st.navigation([page_login, page_inicio, page_carga, page_ingesta, page_admin, page_vis, page_config, page_error])
    # Ocultar la barra lateral para que no puedan navegar usando el menú
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="collapsedControl"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)
    pg.run()
else:
    with st.sidebar:
        render_sidebar_profile()
    # El primer elemento de la lista es la página por defecto
    pg = st.navigation([page_inicio, page_carga, page_ingesta, page_admin, page_vis, page_config, page_error, page_login])
    pg.run()