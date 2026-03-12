import streamlit as st


# Step 2: Event setup page where users input event name and review settings. Then proceed to participant setup.
def render(go_to) -> None:
    st.title("Event Setup")
    st.markdown(
        """
        <div class="hero">
            <h2 style="margin:0;">Set the event context</h2>
            <p class="app-subtitle">
                Name the run. Table and round settings are read from EVENT_SETUP in your uploaded template.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("event_form", clear_on_submit=False):
        event_name = st.text_input(
            "Event name",
            value=st.session_state["event_name"],
            placeholder="World Cafe - Team Building Event",
        )
        submitted = st.form_submit_button("Continue to Participants", type="primary")
    if submitted:
        st.session_state["event_name"] = event_name
        go_to(3)
