import streamlit as st

st.set_page_config(page_title="World Café Grouping Tool", layout="wide")

st.title("Multi-Step Optimization Model for Group Formation")
st.caption("Generate diverse discussion groups based on participant traits")

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Create Group Assignments", use_container_width=True):
        st.switch_page("pages/1_Event_Setup.py")
