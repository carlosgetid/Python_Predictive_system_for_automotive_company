import streamlit as st

def redirect():
    st.switch_page(pg_inicio)

def inicio():
    st.write("INICIO")

pg_root = st.Page(redirect, url_path="root", default=True)
pg_inicio = st.Page(inicio, url_path="inicio")

nav = st.navigation([pg_root, pg_inicio])
nav.run()
