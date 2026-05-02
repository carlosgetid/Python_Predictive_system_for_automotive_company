import streamlit as st

def foo():
    st.write("FOO")
def bar():
    st.write("BAR")

pg = st.navigation([
    st.Page(foo, url_path="inicio", default=True),
    st.Page(bar, url_path="other")
])
pg.run()
