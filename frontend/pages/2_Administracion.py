import streamlit as st
import requests
import os
import time

# --- Configuración de la Página ---
# No usamos st.set_page_config() aquí, ya se llamó en app.py
st.title("Panel de Administración 🛡️")
st.markdown("""
Esta página permite ejecutar operaciones críticas del sistema, como el 
re-entrenamiento de los modelos de Machine Learning.
""")

# --- URL del Backend ---
# Definir la URL del nuevo endpoint que crearemos en el backend
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
# Este es el NUEVO endpoint que debemos crear en routes.py
BACKEND_URL_RETRAIN = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/v1/trigger_retraining"


# --- Lógica de Contraseña Simple ---
def check_password():
    """Devuelve True si el usuario está autenticado, sino muestra el formulario de contraseña."""
    
    # Usar st.session_state para mantener el estado de autenticación
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # Si no está autenticado, mostrar el formulario de login
    if not st.session_state.password_correct:
        st.info("Por favor, ingrese la contraseña de administrador para continuar.")
        with st.form("login_form"):
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Ingresar")

            if submitted:
                # --- CONTRASEÑA DE MVP ---
                # Esta es una contraseña simple para el MVP.
                # En un sistema real, esto debe ser manejado de forma segura (variables de entorno, hash).
                if password == "admin123": 
                    st.session_state.password_correct = True
                    # Re-ejecutar el script para recargar la página en estado autenticado
                    st.rerun() 
                else:
                    st.error("Contraseña incorrecta.")
        return False # No está autenticado
    else:
        return True # Está autenticado

# --- Mostrar Contenido de Administración solo si la contraseña es correcta ---
if check_password():

    st.success("Autenticación exitosa. Panel de administrador desbloqueado.")
    
    # Contenedor para la acción de re-entrenamiento
    with st.container(border=True):
        st.subheader("🤖 Re-entrenamiento del Modelo")
        st.markdown("""
        Presione este botón para forzar al sistema a re-entrenar los modelos de predicción (MLP y XGBoost) 
        utilizando **todos los datos** actualmente disponibles en la base de datos `ventas_historicas`.
        """)
        st.warning("""
        **Advertencia:** Esta operación es intensiva y no se puede deshacer.
        1.  Puede tardar varios minutos en completarse.
        2.  Reemplazará los modelos actuales que están en producción.
        3.  Se recomienda realizar esta acción solo después de una carga de datos significativa.
        """)
        
        # El botón de re-entrenamiento
        if st.button("Iniciar Re-entrenamiento del Modelo", type="primary", use_container_width=True):
            try:
                # Mostrar un spinner mientras el backend trabaja
                with st.spinner("Iniciando re-entrenamiento... Esto puede tardar varios minutos. Por favor, no cierre esta ventana."):
                    
                    # Llamar al nuevo endpoint del backend
                    # Usamos un timeout largo (600 segundos = 10 minutos) porque el entrenamiento puede tardar
                    response = requests.post(BACKEND_URL_RETRAIN, timeout=600)

                    # Manejar la respuesta del backend
                    if response.status_code == 200:
                        st.success(f"✅ ¡Re-entrenamiento completado con éxito!")
                        st.json(response.json()) # Mostrar el JSON de respuesta (que tendrá el mensaje y métricas)
                    else:
                        # Mostrar el error devuelto por el backend
                        error_msg = response.json().get('error', 'Error desconocido del backend.')
                        st.error(f"Error {response.status_code}: {error_msg}")
            
            except requests.exceptions.ConnectionError:
                st.error(f"Error de Conexión: No se pudo conectar al backend en {BACKEND_URL_RETRAIN}. ¿Está el backend (python -m backend.app) corriendo?")
            except requests.exceptions.Timeout:
                st.error("Error: La solicitud de re-entrenamiento superó el tiempo límite (10 minutos). El servidor puede seguir entrenando en segundo plano.")
            except Exception as e:
                st.error(f"Ocurrió un error inesperado al contactar el backend: {e}")
