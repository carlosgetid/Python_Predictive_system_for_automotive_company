import streamlit as st
import requests
import time
import os
import sys
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
# Agregamos la raíz del proyecto al sys.path para importar config correctamente
# frontend/Inicio.py -> parent = frontend -> parent = raiz
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN ---
try:
    from frontend.config import URL_LOGIN, HIDE_SIDEBAR_CSS # --- NUEVO: Importar CSS
except ImportError:
    # Fallback por si falla la importación
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
    URL_LOGIN = f"http://{BACKEND_HOST}:{BACKEND_PORT}/login"
    HIDE_SIDEBAR_CSS = "" # Fallback vacío

# --- CONFIGURACIÓN DE PÁGINA ---
# Debe ser la primera instrucción de Streamlit
st.set_page_config(
    page_title="Sistema Predictivo - Login",
    page_icon="🚗",
    layout="centered", # Centrado para el Login
    initial_sidebar_state="collapsed" # Ocultar sidebar en login
)

# --- GESTIÓN DE ESTADO DE SESIÓN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

# --- FUNCIÓN DE LOGIN ---
def login_screen():
    # --- NUEVO: Ocultar Sidebar visualmente ---
    st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
    # ------------------------------------------
    
    st.title("🔐 Iniciar Sesión")
    st.markdown("### Sistema Predictivo de Gestión de Inventarios")
    st.markdown("Ingrese sus credenciales corporativas para continuar.")
    
    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="Ej. lfernandez")
        password = st.text_input("Contraseña", type="password")
        
        submitted = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("⚠️ Por favor ingrese usuario y contraseña.")
                return

            try:
                with st.spinner("Verificando credenciales..."):
                    # Llamada al API de Autenticación
                    payload = {"username": username, "password": password}
                    response = requests.post(URL_LOGIN, json=payload, timeout=5)
                    
                    if response.status_code == 200:
                        # Login Exitoso
                        data = response.json()
                        st.session_state.authenticated = True
                        st.session_state.user = data.get("user")
                        
                        st.success(f"¡Bienvenido {st.session_state.user['nombre']}!")
                        time.sleep(0.5)
                        st.rerun() # Recargar para mostrar el Dashboard
                        
                    elif response.status_code == 401:
                        st.error("❌ Usuario o contraseña incorrectos.")
                    else:
                        st.error(f"Error del servidor: {response.text}")
            
            except requests.exceptions.ConnectionError:
                st.error("❌ No se pudo conectar al servidor Backend. Verifique que esté corriendo.")
            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {e}")

# --- FUNCIÓN DE DASHBOARD (App Principal) ---
def dashboard_screen():
    # Cambiar layout visualmente (hack)
    # Nota: st.set_page_config solo se puede llamar una vez, por eso manejamos el contenido.
    
    # Sidebar con Info del Usuario
    with st.sidebar:
        st.title(f"👤 {st.session_state.user['nombre']}")
        st.caption(f"Rol: **{st.session_state.user['rol']}**")
        st.divider()
        
        if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    # Contenido Principal
    st.write(f"# Hola, {st.session_state.user['nombre'].split()[0]} 👋")
    st.markdown(f"Has ingresado como: **{st.session_state.user['rol']}**")
    st.divider()
    
    st.markdown(
        """
        Bienvenido al sistema de optimización de inventarios **Teo Autopartes**.
        Seleccione una opción en el menú lateral según su perfil:
        """
    )
    
    # Tarjetas de Acceso Rápido
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📤 **Carga de Datos**\n\nSubida de históricos y gestión de archivos transaccionales.")
        st.success("📈 **Predicción**\n\nGeneración de pronósticos de demanda por producto.")
        
    with col2:
        st.warning("⚙️ **Administración**\n\nRe-entrenamiento del modelo, monitoreo de métricas y configuración.")
        
    st.caption("v1.2.0 - Sprint 2 Release")

# --- CONTROLADOR PRINCIPAL ---
if not st.session_state.authenticated:
    login_screen()
else:
    dashboard_screen()