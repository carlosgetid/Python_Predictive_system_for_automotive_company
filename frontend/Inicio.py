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

# --- GESTIÓN DE ESTADO DE SESIÓN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

# --- DEFINICIÓN DE PÁGINAS ---
page_inicio = st.Page("pages/0_Dashboard.py", title="Inicio", icon="🏠", default=True)
page_carga = st.Page("pages/1_Carga_de_Datos.py", title="Carga de Datos")
page_admin = st.Page("pages/2_Administracion.py", title="Administracion")
page_vis = st.Page("pages/3_Visualizacion_de_Prediccion.py", title="Visualizacion de Prediccion")
page_config = st.Page("pages/4_Configuracion.py", title="Configuracion")

# El login será la página por defecto cuando no haya sesión
page_login = st.Page("pages/login.py", title="Login", default=True)

# --- CONTROLADOR PRINCIPAL ---
if not st.session_state.authenticated:
    pg = st.navigation([page_login])
    pg.run()
else:
    with st.sidebar:
        render_sidebar_profile()
    pg = st.navigation([page_inicio, page_carga, page_admin, page_vis, page_config])
    pg.run()