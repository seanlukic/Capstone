import streamlit as st

from ui import inject_global_styles, render_hero, render_progress, render_start_over_button

st.set_page_config(page_title="Event Setup | Group Formation Studio", page_icon="groups", layout="wide")
inject_global_styles()
render_progress(2)
render_start_over_button("start_over_event")

st.session_state.setdefault("event_name", "")
st.session_state.setdefault("num_people", 30)

st.title("Event Setup")
render_hero(
    "Set the event context",
    "These values are used to guide participant intake and group generation.",
)

with st.form("event_form", clear_on_submit=False):
    col1, col2 = st.columns([2, 1])
    with col1:
        event_name = st.text_input("Event name", value=st.session_state["event_name"], placeholder="Capstone Collaboration Day")
    with col2:
        num_people = st.number_input("Expected participants", min_value=1, value=int(st.session_state["num_people"]), step=1)

    submitted = st.form_submit_button("Continue to Participants", type="primary")

if submitted:
    st.session_state["event_name"] = event_name
    st.session_state["num_people"] = int(num_people)
    st.switch_page("pages/2_Participants.py")
