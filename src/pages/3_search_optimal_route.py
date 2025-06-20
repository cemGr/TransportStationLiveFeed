import streamlit as st


st.title("⚙️ Settings")
st.text_input("Enter API key", key="api_key")
if st.button("Save"):
    st.success("Settings saved!")
