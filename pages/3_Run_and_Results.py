import streamlit as st

st.title("Output Summary")

df = st.session_state.get("df")
if df is None:
    st.error("No data found. Go back and upload participants.")
    st.stop()

st.success("Data loaded successfully.")
st.dataframe(df)
