import pandas as pd
import streamlit as st

from solver_backend import solve_solver_v2
from ui import inject_global_styles, render_hero, render_progress

st.set_page_config(page_title="Group Formation Studio", page_icon="groups", layout="wide")
inject_global_styles()

REQUIRED_COLS = ["Participant_ID", "Expertise", "Lived_Experience", "Minnesota"]


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[REQUIRED_COLS]


def go_to(step: int) -> None:
    st.session_state["step"] = step
    st.rerun()


def start_over() -> None:
    for key in list(st.session_state.keys()):
        if key not in {"theme"}:
            del st.session_state[key]
    st.session_state["step"] = 1
    st.rerun()


st.session_state.setdefault("step", 1)
st.session_state.setdefault("event_name", "")
st.session_state.setdefault("num_people", 30)

step = st.session_state["step"]
render_progress(step, total_steps=4)

if step > 1 and st.button("Start Over"):
    start_over()

if step == 1:
    st.title("Group Formation Studio")
    st.caption("Build diverse teams from spreadsheet uploads or manual participant entry")
    render_hero(
        "Design balanced, high-diversity groups in minutes",
        "Start by setting event details. Then upload participants or enter them manually before generating group assignments.",
    )
    if st.button("Start Setup", type="primary"):
        go_to(2)

elif step == 2:
    st.title("Event Setup")
    render_hero(
        "Set the event context",
        "These values are used to guide participant intake and group generation.",
    )
    with st.form("event_form", clear_on_submit=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            event_name = st.text_input(
                "Event name",
                value=st.session_state["event_name"],
                placeholder="Capstone Collaboration Day",
            )
        with col2:
            num_people = st.number_input(
                "Expected participants",
                min_value=1,
                value=int(st.session_state["num_people"]),
                step=1,
            )
        submitted = st.form_submit_button("Continue to Participants", type="primary")
    if submitted:
        st.session_state["event_name"] = event_name
        st.session_state["num_people"] = int(num_people)
        go_to(3)

elif step == 3:
    st.title("Participant Setup")
    render_hero(
        "Add or import participant data",
        "Provide participant records, validate key fields, then continue to run your grouping logic.",
    )
    mode = st.radio("Input method", ["Upload file", "Add manually"], horizontal=True)
    df = None
    if mode == "Upload file":
        uploaded = st.file_uploader("Upload participant file", type=["xlsx", "csv"])
        if uploaded is None:
            st.info("Upload a .csv or .xlsx file to continue, or switch to manual entry.")
            st.stop()
        if uploaded.name.lower().endswith(".csv"):
            df = ensure_columns(pd.read_csv(uploaded))
        else:
            df = ensure_columns(pd.read_excel(uploaded))
    else:
        st.caption("Use the editor below to add rows, paste from a spreadsheet, and adjust values.")
        if "manual_df" not in st.session_state:
            st.session_state["manual_df"] = pd.DataFrame(columns=REQUIRED_COLS)
        edited = st.data_editor(
            st.session_state["manual_df"],
            num_rows="dynamic",
            use_container_width=True,
            key="manual_editor",
        )
        st.session_state["manual_df"] = ensure_columns(edited)
        df = st.session_state["manual_df"]
        st.download_button(
            "Download manual entries (CSV)",
            df.to_csv(index=False).encode("utf-8"),
            file_name="participants.csv",
            mime="text/csv",
            disabled=df.empty,
        )

    df = ensure_columns(df)
    if df.empty:
        st.warning("No participants yet. Add at least one row to continue.")
        st.stop()

    missing_ids = df["Participant_ID"].astype(str).str.strip().eq("").sum()
    if missing_ids > 0:
        st.warning(f"{missing_ids} participant(s) are missing Participant_ID.")

    st.session_state["df"] = df
    metric1, metric2 = st.columns(2)
    metric1.metric("Participant rows", len(df))
    metric2.metric("Missing Participant_ID", int(missing_ids))
    if len(df) < 24 or len(df) > 36:
        st.error("SolverV2 backend expects 24-36 participants (6 tables, size 4-6).")
        st.stop()
    st.subheader("Current Participant Data")
    st.dataframe(df, use_container_width=True)

    left, right = st.columns(2)
    with left:
        if st.button("Back to Event Setup"):
            go_to(2)
    with right:
        if st.button("Generate Groupings", type="primary"):
            with st.spinner("Solving group assignments..."):
                try:
                    participant_results, schedule_results, objective_value = solve_solver_v2(df)
                except Exception as exc:
                    st.error(f"Solver failed: {exc}")
                    st.stop()
            st.session_state["participant_results"] = participant_results
            st.session_state["schedule_results"] = schedule_results
            st.session_state["objective_value"] = objective_value
            go_to(4)

else:
    st.title("Run and Results")
    render_hero(
        "Generated group assignments",
        "Review and download your grouping results.",
    )
    participant_results = st.session_state.get("participant_results")
    schedule_results = st.session_state.get("schedule_results")
    objective_value = st.session_state.get("objective_value")
    if participant_results is None or schedule_results is None:
        st.error("No grouping results found. Go back and click Generate Groupings.")
        st.stop()
    st.success(f"Solved with Gurobi optimizer. Objective value: {objective_value:.1f}")

    st.subheader("Participant Schedule")
    schedule_cols = ["Participant_ID", "Round_1_Table", "Round_2_Table", "Round_3_Table"]
    display_schedule = participant_results[schedule_cols].sort_values("Participant_ID").reset_index(drop=True)
    st.dataframe(display_schedule, use_container_width=True)

    st.subheader("Round-by-Round Table Assignments")
    st.dataframe(schedule_results, use_container_width=True)

    csv_data = display_schedule.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Group Assignments (CSV)",
        data=csv_data,
        file_name="group_assignments.csv",
        mime="text/csv",
    )

    left, right = st.columns(2)
    with left:
        if st.button("Back to Participants"):
            go_to(3)
    with right:
        st.info("If needed, go back and change participant data to regenerate groups.")
