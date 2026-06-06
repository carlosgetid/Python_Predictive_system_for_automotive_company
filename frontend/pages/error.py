import streamlit as st
import sys
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

try:
    from frontend.styles import get_app_css
except ImportError:
    def get_app_css(): return ""


st.markdown(get_app_css(), unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; margin-top: 50px;">
    <h1 style="color: #EF4444; font-size: 80px; margin-bottom: 0;">403</h1>
    <h2 style="color: #0F2942;">Acceso Denegado</h2>
    <p style="color: #64748B; font-size: 18px; margin-top: 10px;">
        Lo sentimos, no tienes los permisos necesarios para acceder a esta página.
    </p>
</div>
""", unsafe_allow_html=True)

if st.button("Volver al Inicio", type="primary", use_container_width=True):
    st.switch_page("pages/0_Dashboard.py")
