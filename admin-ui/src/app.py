import streamlit as st
from components.sidebar import render_sidebar

st.set_page_config(page_title="Clinica CRM", page_icon="\U0001f3e5", layout="wide")

# Shared sidebar -- appears on every page (per D-03)
render_sidebar()

# Page routing using st.navigation
dashboard = st.Page("pages/1_Dashboard.py", title="Dashboard", icon=":material/dashboard:")
whatsapp = st.Page("pages/2_WhatsApp.py", title="WhatsApp", icon=":material/chat:")

pg = st.navigation({"Principal": [dashboard], "Conexion": [whatsapp]})
pg.run()
