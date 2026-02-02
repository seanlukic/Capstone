import streamlit as st

from ui import inject_global_styles, render_hero, render_progress, render_start_over_button

st.set_page_config(page_title="Run & Results | Group Formation Studio", page_icon="groups", layout="wide")
inject_global_styles()
render_progress(4)
render_start_over_button("start_over_results")

st.title("Run and Results")
render_hero(
    "Review your current input data",
    "This page confirms loaded participant data and is ready for optimizer output integration.",
)

df = st.session_state.get("df")
if df is None:
    st.error("No participant data found. Go back to Participant Setup.")
    st.stop()

st.success("Participant data loaded.")
st.dataframe(df, use_container_width=True)

left, right = st.columns(2)
with left:
    if st.button("Back to Participants"):
        st.switch_page("pages/2_Participants.py")
with right:
    st.info("Next step: connect your optimization model and display grouped assignments here.")
