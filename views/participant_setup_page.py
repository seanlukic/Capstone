import streamlit as st

from solver_backend import solve_solver_v2
from template_parser import TEMPLATE_PATH, _parse_template


# Template upload and participant setup page. Users download the template, fill it out, and upload it.
# The app parses the uploaded file, extracts participant data and event configuration, and then allows users to generate group assignments.
def render(go_to) -> None:
    st.title("Participant Setup")
    st.markdown(
        """
        <div class="hero">
            <h2 style="margin:0;">Import participant data</h2>
            <p class="app-subtitle">
                Upload your completed file. The app reads event setup, traits, participants, and optional locks.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
            div[data-testid="stDownloadButton"] > button {
                background: linear-gradient(120deg, var(--accent) 0%, var(--accent-2) 100%);
                border: none !important;
                color: #ffffff !important;
                border-radius: 10px;
            }
            div[data-testid="stDownloadButton"] > button:hover {
                background: linear-gradient(120deg, var(--accent) 0%, var(--accent-2) 100%);
                color: #ffffff !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if TEMPLATE_PATH.exists():
        template_bytes = TEMPLATE_PATH.read_bytes()
        st.download_button(
            "Download Participant Template (Excel)",
            data=template_bytes,
            file_name=TEMPLATE_PATH.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning(f"Template file not found: `{TEMPLATE_PATH}`")

    uploaded = st.file_uploader("Upload completed template", type=["xlsx", "xls"])
    if uploaded is None:
        st.info("Download the template above, fill it out, then upload the completed Excel file.")
        st.stop()

    try:
        parsed = _parse_template(uploaded)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Could not parse template: {exc}")
        st.stop()

    participants_df = parsed["participants_df"]
    characteristics = parsed["characteristics"]
    event_setup = parsed["event_setup"]
    locks = parsed["locks"]
    participant_locks = parsed["participant_locks"]

    st.success(f"Loaded `{uploaded.name}` with {len(participants_df)} participant rows.")
    if parsed["generated_ids"] > 0:
        st.warning(f"Generated {parsed['generated_ids']} missing Participant_ID values as AUTO_*.")

    st.session_state["uploaded_df"] = parsed["raw_participants"]
    st.session_state["df"] = participants_df
    st.session_state["event_setup"] = event_setup
    st.session_state["characteristics"] = characteristics
    st.session_state["trait_targets"] = parsed["trait_targets"]
    st.session_state["trait_max_allowed"] = parsed["trait_max_allowed"]
    st.session_state["trait_min_required"] = parsed["trait_min_required"]
    st.session_state["locks"] = locks
    st.session_state["participant_locks"] = participant_locks

    min_total = event_setup["number_of_tables"] * event_setup["min_people_per_table"]
    max_total = event_setup["number_of_tables"] * event_setup["max_people_per_table"]

    st.metric("Participant rows", len(participants_df))
    st.caption(
        f"Event settings: {event_setup['number_of_tables']} tables, "
        f"{event_setup['min_people_per_table']}-{event_setup['max_people_per_table']} people/table, "
        f"{event_setup['number_of_rounds']} round(s), stage={event_setup['optimization_stage']}"
    )
    st.caption(
        f"Traits in model: {len(characteristics)}. "
        f"Table locks: {len(locks)}. "
        f"Participant separation locks: {len(participant_locks)}"
    )

    st.subheader("Current Participant Data")
    st.dataframe(st.session_state["uploaded_df"], use_container_width=True, hide_index=True)

    invalid_count = len(participants_df) < min_total or len(participants_df) > max_total
    if invalid_count:
        st.error(
            f"Participant count must be between {min_total} and {max_total} "
            f"for {event_setup['number_of_tables']} tables at size "
            f"{event_setup['min_people_per_table']}-{event_setup['max_people_per_table']}."
        )
    else:
        st.info("Group assignments can take up to 3 minutes to generate.")

    left, right = st.columns(2)
    with left:
        if st.button("Back to Event Setup"):
            go_to(2)
    with right:
        if st.button("Generate Groupings", type="primary", disabled=invalid_count):
            with st.spinner("Solving group assignments..."):
                try:
                    participant_results, schedule_results, objective_value, optimality_gap = solve_solver_v2(
                        participants_df,
                        debug=True,
                        time_limit_seconds=180.0,
                        characteristics=characteristics,
                        num_tables=event_setup["number_of_tables"],
                        num_rounds=event_setup["number_of_rounds"],
                        min_people_per_table=event_setup["min_people_per_table"],
                        max_people_per_table=event_setup["max_people_per_table"],
                        trait_targets=parsed["trait_targets"],
                        trait_max_allowed=parsed["trait_max_allowed"],
                        trait_min_required=parsed["trait_min_required"],
                        locked_tables=locks,
                        separation_pairs=participant_locks,
                    )
                except Exception as exc:
                    st.error(f"Solver failed: {exc}")
                    st.stop()

            st.session_state["participant_results"] = participant_results
            st.session_state["schedule_results"] = schedule_results
            st.session_state["objective_value"] = objective_value
            st.session_state["optimality_gap"] = optimality_gap
            go_to(4)
