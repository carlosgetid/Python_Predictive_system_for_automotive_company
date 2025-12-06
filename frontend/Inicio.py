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
    page_title="Teo Analytics - Acceso",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- GESTIÓN DE ESTADO DE SESIÓN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

# --- FUNCIÓN DE LOGIN (CORREGIDA) ---
def login_screen():
    # 1. Inyectar CSS Global
    st.markdown(get_app_css(), unsafe_allow_html=True)
    
    # 2. CSS Local para la Tarjeta
    st.markdown("""
        <style>
            /* Convertir el formulario nativo en la Login Card */
            [data-testid="stForm"] {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
                padding: 40px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                border-top: 6px solid #0F2942;
                max-width: 450px;
                margin: 0 auto;
            }
            /* --- NUEVO: Ocultar completamente la Sidebar y su botón --- */
            [data-testid="stSidebar"] { display: none; }
            [data-testid="collapsedControl"] { display: none; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 5vh;'></div>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.markdown("""
            <div style="text-align: center; margin-bottom: 25px;">
                <div class="login-header">🔐 Iniciar Sesión</div>
                <div class="login-subtext">
                    <b>Teo Analytics</b><br>Plataforma de Inteligencia Automotriz
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Usuario Corporativo", placeholder="Ej. lfernandez")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Acceder a la Plataforma", type="primary", use_container_width=True)
        
        # --- [RESTAURADO] LÓGICA DE AUTENTICACIÓN ---
        if submitted:
            if not username or not password:
                st.warning("⚠️ Ingrese sus credenciales para continuar.")
                return

            try:
                with st.spinner("Validando acceso..."):
                    payload = {"username": username, "password": password}
                    response = requests.post(URL_LOGIN, json=payload, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.authenticated = True
                        st.session_state.user = data.get("user")
                        
                        st.toast(f"¡Bienvenido, {st.session_state.user['nombre']}!", icon="👋")
                        time.sleep(0.8)
                        st.rerun()
                        
                    elif response.status_code == 401:
                        st.error("Credenciales incorrectas. Verifique e intente nuevamente.")
                    else:
                        st.error(f"Error de conexión ({response.status_code})")
            
            except requests.exceptions.ConnectionError:
                st.error("❌ Servidor no disponible. Contacte a soporte TI.")
            except Exception as e:
                st.error(f"Error inesperado: {e}")
        # ---------------------------------------------

    st.markdown("""
        <div style="text-align: center; margin-top: 30px; color: #94A3B8; font-size: 12px;">
            © 2024 Teo Autopartes S.A.C. | v2.0 Enterprise Release
        </div>
    """, unsafe_allow_html=True)

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

# --- CONTROLADOR PRINCIPAL ---
if not st.session_state.authenticated:
    login_screen()
else:
    dashboard_screen()