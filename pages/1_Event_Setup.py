import streamlit as st

st.title("Event Setup")

st.session_state.setdefault("event_name", "")
st.session_state.setdefault("num_people", "")

with st.form("event_form"):
    st.session_state["event_name"] = st.text_input("Event name", st.session_state["event_name"])
    st.session_state["num_people"] = st.number_input("No. of People", min_value=1, value=int(st.session_state["num_people"]), step=1)

    ok = st.form_submit_button("Continue")

if ok:
    st.switch_page("pages/2_Participants.py")
