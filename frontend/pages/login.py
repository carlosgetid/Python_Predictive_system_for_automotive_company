import streamlit as st
import requests
import time
import os
import sys
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN Y ESTILOS ---
try:
    from frontend.config import URL_LOGIN
    from frontend.styles import get_app_css 
except ImportError:
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
    URL_LOGIN = f"http://{BACKEND_HOST}:{BACKEND_PORT}/login"
    def get_app_css(): return ""

# --- CONFIGURACIÓN DE PÁGINA ---
# Movido a Inicio.py debido a st.navigation

# --- GESTIÓN DE ESTADO DE SESIÓN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

if st.session_state.authenticated:
    st.rerun()

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
    
    username = st.text_input("Usuario Corporativo")
    password = st.text_input("Contraseña", type="password")
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    submitted = st.form_submit_button("Acceder a la Plataforma", type="primary", use_container_width=True)
    
    # --- LÓGICA DE AUTENTICACIÓN ---
    if submitted:
        if not username or not password:
            st.warning("⚠️ Ingrese sus credenciales para continuar.")
        else:
            try:
                with st.spinner("Validando acceso..."):
                    payload = {"username": username, "password": password}
                    response = requests.post(URL_LOGIN, json=payload, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.authenticated = True
                        st.session_state.user = data.get("user")
                        st.session_state.token = data.get("token")
                        
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

st.markdown("""
    <div style="text-align: center; margin-top: 30px; color: #94A3B8; font-size: 12px;">
        © 2024 Teo Autopartes S.A.C. | v2.0 Enterprise Release
    </div>
""", unsafe_allow_html=True)
