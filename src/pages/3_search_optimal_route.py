import streamlit as st


st.title("⚙️ Einstellungen")
st.text_input("API-Key eingeben", key="api_key")
if st.button("Speichern"):
    st.success("Einstellungen gespeichert!")
