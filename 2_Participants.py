import streamlit as st
import pandas as pd

st.title("Participant Setup")

uploaded = st.file_uploader("Upload participant Excel file", type=["xlsx"])

if uploaded is None:
    st.info("Upload an Excel file to continue.")
    st.stop()

df = pd.read_excel(uploaded)
st.session_state["df"] = df

st.dataframe(df)

if st.button("Generate Groupings"):
    st.switch_page("pages/3_Run_and_Results.py")
