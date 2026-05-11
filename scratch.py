import streamlit as st

if "db" not in st.session_state:
    st.session_state.db = "A"

st.write("DB value:", st.session_state.db)

options = ["A", "B", "C"]
default_index = options.index(st.session_state.db)

with st.form("my_form"):
    selected = st.selectbox("Select", options, index=default_index)
    
    submitted = st.form_submit_button("Submit")

if submitted:
    st.session_state.db = selected
    st.success(f"Saved: {selected}")
    st.rerun()
