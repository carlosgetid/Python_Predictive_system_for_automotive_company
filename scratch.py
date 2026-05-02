import streamlit as st

if "auth" not in st.session_state:
    st.session_state.auth = False

def dashboard():
    st.write("Dashboard")
    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

def login():
    st.write("Login")
    if st.button("Login"):
        st.session_state.auth = True
        st.rerun()

pg_dash = st.Page(dashboard, title="Inicio", url_path="inicio", default=True)
pg_login = st.Page(login, title="Login", url_path="login")

if not st.session_state.auth:
    pg = st.navigation([pg_login])
    pg.run()
else:
    pg = st.navigation([pg_dash])
    pg.run()
