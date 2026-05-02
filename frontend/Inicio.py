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
    from frontend.styles import get_app_css 
except ImportError:
    # Fallback
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
    URL_LOGIN = f"http://{BACKEND_HOST}:{BACKEND_PORT}/login"
    def get_role_based_sidebar_css(role): return ""
    def get_app_css(): return ""

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Teo Analytics - Inicio",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- GESTIÓN DE ESTADO DE SESIÓN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

# --- (La función login_screen fue movida a frontend/pages/login.py) ---

# --- FUNCIÓN DE DASHBOARD ---
def dashboard_screen():
    st.markdown(get_app_css(), unsafe_allow_html=True)
    
    role_css = get_role_based_sidebar_css(st.session_state.user['rol'])
    st.markdown(role_css, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"""
            <div style="padding: 10px 0;">
                <h2 style="color: #F8FAFC; margin:0;">Teo Analytics</h2>
                <p style="color: #94A3B8; font-size: 12px; margin:0;">Enterprise Edition</p>
            </div>
            <hr style="margin: 10px 0; border-color: #334155;">
        """, unsafe_allow_html=True)
        
        st.write(f"👤 **{st.session_state.user['nombre']}**")
        st.caption(f"Perfil: {st.session_state.user['rol']}")
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    st.title(f"Bienvenido, {st.session_state.user['nombre'].split()[0]}")
    st.markdown("### Acceso Rápido")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title" style="color: #0F2942;">📤 Operaciones</div>
            <p style="color: #64748B; font-size: 14px;">
                Carga de históricos y gestión de archivos.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title" style="color: #0F2942;">📊 Analítica</div>
            <p style="color: #64748B; font-size: 14px;">
                Dashboards de predicción y reportes de IA.
            </p>
        </div>
        """, unsafe_allow_html=True)

# --- DEFINICIÓN DE PÁGINAS ---
def root_redirect():
    if not st.session_state.authenticated:
        st.switch_page(page_login)
    else:
        st.switch_page(page_inicio)

page_root = st.Page(root_redirect, title="App", default=True)
page_inicio = st.Page(dashboard_screen, title="Inicio", url_path="inicio")
page_carga = st.Page("pages/1_Carga_de_Datos.py", title="Carga de Datos")
page_admin = st.Page("pages/2_Administracion.py", title="Administracion")
page_vis = st.Page("pages/3_Visualizacion_de_Prediccion.py", title="Visualizacion de Prediccion")
page_config = st.Page("pages/4_Configuracion.py", title="Configuracion")
page_login = st.Page("pages/login.py", title="Login", url_path="login")

# --- CONTROLADOR PRINCIPAL ---
if not st.session_state.authenticated:
    pg = st.navigation([page_root, page_login])
    pg.run()
else:
    pg = st.navigation([page_root, page_inicio, page_carga, page_admin, page_vis, page_config])
    pg.run()