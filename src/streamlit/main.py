import streamlit as st

st.set_page_config(
    page_title="LA Metro Bike Share",
    page_icon="🚲",
    layout="wide",
)

st.title("🚲 Metro Bike Share Tools")
st.markdown(
    """
    Use the navigation menu on the left to:

    1. **Find Bikes:** Locate the K nearest stations with available bikes.  
    2. **Find Docks:** Locate the K nearest stations with free docks.  
    3. **Plan Route:** Get a foot → bike → foot route between two locations.
    """
)
