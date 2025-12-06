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
    # [NUEVO] Importar motor de estilos
    from frontend.styles import get_app_css
except ImportError as e:
    st.error(f"Error crítico importando configuración: {e}")
    st.stop()

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)

# --- PROTECCIÓN DE PÁGINA (Login Required + RBAC) ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.stop()

# Validación de Rol: Bloquear acceso a "Vendedora"
if st.session_state.user['rol'] == 'Vendedora':
    st.error("⛔ Acceso Restringido: Su perfil no tiene permisos de configuración.")
    st.stop()
# ----------------------------------------------------

# ----------------------------------------------------

# [NUEVO] Inyectar CSS Global para el estilo Enterprise
st.markdown(get_app_css(), unsafe_allow_html=True)

# [REEMPLAZO] Encabezado Corporativo
st.markdown('<h1 style="color:#0F2942; margin-bottom: 5px;">⚙️ Configuración del Sistema</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#64748B;">Panel de control para ajustar el comportamiento de la interfaz y funcionalidades del sistema.</p>', unsafe_allow_html=True)

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True) 

# --- SECCIÓN: CONTROL DE INGESTA ---
# [REEMPLAZO] Subtítulo estilizado con separador
st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">📂 Control de Ingesta de Datos</h2>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    # [REEMPLAZO] Usar metric-card para encapsular las instrucciones
    st.markdown("""
    <div class="metric-card" style="padding: 20px; border-left: 4px solid #0F2942;">
        <h4 style="margin-top:0; color:#0F2942; font-size: 16px;">Habilitar Carga Manual de Archivos</h4>
        <p style="color:#475569; margin-bottom: 10px; font-size: 14px;">
        Define si los usuarios pueden subir archivos Excel/CSV manualmente desde la interfaz web.
        </p>
        <ul style="color:#64748B; font-size: 13px; margin-bottom: 0; padding-left: 20px;">
            <li><b>Activado (ON):</b> Muestra el cargador en 'Carga de Datos'.</li>
            <li><b>Desactivado (OFF):</b> Se utiliza exclusivamente la Ingesta Automatizada (carpeta <code>/data_fuente/entrada</code>).</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # 1. Leer estado actual
# ... (el resto del código en col2 permanece igual)
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

# --- Indicador Visual del Estado Actual (REEMPLAZO) ---
if new_state:
    st.markdown("""
    <div style="margin-top: 15px; padding: 10px; background-color: #D1FAE5; color: #10B981; border-radius: 6px; font-weight: 600; border: 1px solid #10B981;">
        ✅ La carga manual está HABILITADA actualmente.
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="margin-top: 15px; padding: 10px; background-color: #F0F4F8; color: #64748B; border-radius: 6px; border: 1px solid #94A3B8;">
        ℹ️ La carga manual está DESHABILITADA. El sistema opera en modo automático.
    </div>
    """, unsafe_allow_html=True)

st.divider()