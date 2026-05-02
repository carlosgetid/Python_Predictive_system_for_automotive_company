import streamlit as st
import time

def dashboard():
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] ul li:first-child {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    st.write("DASHBOARD EN /INICIO")

def root_redirect():
    st.switch_page(pg_dash)

pg_root = st.Page(root_redirect, title="Root", default=True)
pg_dash = st.Page(dashboard, title="Inicio", url_path="inicio")
pg_other = st.Page(lambda: st.write("Other"), title="Other")

pg = st.navigation([pg_root, pg_dash, pg_other])
pg.run()
