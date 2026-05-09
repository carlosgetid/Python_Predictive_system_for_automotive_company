import streamlit as st
import sys
import os
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

try:
    from frontend.config import get_role_based_sidebar_css
    from frontend.styles import get_app_css
except ImportError:
    def get_role_based_sidebar_css(role): return ""
    def get_app_css(): return ""


role_css = get_role_based_sidebar_css(st.session_state.user['rol'])
st.markdown(role_css, unsafe_allow_html=True)

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
