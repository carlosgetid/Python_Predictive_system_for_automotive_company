import streamlit as st
import sys
import logging
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
# Necesario para importar frontend.config correctamente
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN ---
try:
    from frontend.config import get_setting, update_setting
except ImportError as e:
    st.error(f"Error crítico importando configuración: {e}")
    st.stop()

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)

st.title("⚙️ Configuración del Sistema")
st.markdown("Panel de control para ajustar el comportamiento de la interfaz de usuario y funcionalidades del sistema.")

st.divider()

# --- SECCIÓN: CONTROL DE INGESTA ---
st.subheader("📂 Control de Ingesta de Datos")

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("""
    **Habilitar Carga Manual de Archivos**
    
    Define si los usuarios pueden subir archivos Excel/CSV manualmente desde la interfaz web.
    
    * **Activado (ON):** Muestra el cargador de archivos en la página 'Carga de Datos'.
    * **Desactivado (OFF):** Oculta el cargador. El sistema dependerá exclusivamente de la Ingesta Automatizada (carpeta `/data_fuente/entrada`).
    """)

with col2:
    # 1. Leer estado actual
    current_state = get_setting("MOSTRAR_CARGA_MANUAL", True)
    
    # 2. Widget de control (Toggle Switch)
    # key='toggle_manual' asegura que el estado se mantenga en la sesión
    new_state = st.toggle("Estado", value=current_state, key="toggle_manual")

    # 3. Lógica de Guardado
    if new_state != current_state:
        if update_setting("MOSTRAR_CARGA_MANUAL", new_state):
            st.toast(f"Configuración guardada: {'Habilitado' if new_state else 'Deshabilitado'}", icon="✅")
            logging.info(f"Configuración MOSTRAR_CARGA_MANUAL cambiada a {new_state}")
            
            # Pequeña pausa para que el usuario vea el cambio antes de cualquier recarga
            import time
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Error al guardar en settings.json")

# --- Indicador Visual del Estado Actual ---
if new_state:
    st.success("✅ La carga manual está **HABILITADA** actualmente.")
else:
    st.info("ℹ️ La carga manual está **DESHABILITADA**. El sistema opera en modo automático.")

st.divider()