import streamlit as st
import pandas as pd

st.title("📊 Datenvisualisierung")

df = pd.DataFrame({
    "x": range(10),
    "y": [i**2 for i in range(10)]
})
st.line_chart(df.set_index("x"))
