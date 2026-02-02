import streamlit as st

st.set_page_config(page_title="Group Formation Tool", layout="wide")

st.title("Multi-Step Optimization Model for Group Formation!")
st.caption("Generate diverse discussion groups based on participant traits")

if st.button("Create Group Assignments"):
    st.switch_page("pages/1_Event_Setup.py")
