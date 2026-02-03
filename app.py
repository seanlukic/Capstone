import pandas as pd
import streamlit as st

from solver_backend import solve_solver_v2
from ui import inject_global_styles, render_hero, render_progress

st.set_page_config(page_title="Group Formation Studio", page_icon="groups", layout="wide")
inject_global_styles()

REQUIRED_COLS = ["Participant_ID", "Expertise", "Lived_Experience", "Minnesota"]
DIVERSITY_COLS = ["Expertise", "Lived_Experience", "Minnesota"]


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Use Person_ID from source files when Participant_ID is missing/blank.
    alt_id_cols = ["Person_ID", "person_id", "personid", "PersonID"]
    if "Participant_ID" not in df.columns:
        for alt in alt_id_cols:
            if alt in df.columns:
                df["Participant_ID"] = df[alt]
                break
    elif df["Participant_ID"].astype(str).str.strip().eq("").all():
        for alt in alt_id_cols:
            if alt in df.columns:
                df["Participant_ID"] = df[alt]
                break
    else:
        # Fill any blank Participant_ID cells from Person_ID when available.
        blank_mask = df["Participant_ID"].astype(str).str.strip().eq("")
        for alt in alt_id_cols:
            if alt in df.columns:
                df.loc[blank_mask, "Participant_ID"] = df.loc[blank_mask, alt]
                break

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


def table_diversity_score(table_df: pd.DataFrame) -> int:
    score = 0
    for col in DIVERSITY_COLS:
        if col in table_df.columns:
            score += table_df[col].astype(str).nunique(dropna=True)
    return int(score)


st.session_state.setdefault("step", 1)
st.session_state.setdefault("event_name", "")
st.session_state.setdefault("num_people", 30)

step = st.session_state["step"]
render_progress(step, total_steps=4)

if step > 1 and st.button("Start Over"):
    start_over()

if step == 1:
    st.title("Group Formation Studio")
    st.caption("Build diverse teams from spreadsheet uploads")
    render_hero(
        "Design balanced, high-diversity groups in minutes",
        "Start by setting event details. Then upload participants data to generate group assignments.",
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
                placeholder="World Cafe - Team Building Event",
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
        "Import participant data",
        "Upload participant records, validate key fields, then continue to run your grouping logic.",
    )
    uploaded = st.file_uploader("Upload participant file", type=["xlsx", "xls", "csv"])
    if uploaded is None:
        st.info("Upload a .csv or .xlsx file to continue.")
        st.stop()
    if uploaded.name.lower().endswith(".csv"):
        raw_df = pd.read_csv(uploaded)
    else:
        raw_df = pd.read_excel(uploaded)
    st.success(f"Loaded `{uploaded.name}` with {len(raw_df)} rows.")
    st.session_state["uploaded_df"] = raw_df
    df = ensure_columns(raw_df)

    df = ensure_columns(df)
    if df.empty:
        st.warning("No participants yet. Add at least one row to continue.")
        st.stop()

    st.session_state["df"] = df
    st.metric("Participant rows", len(df))
    st.subheader("Current Participant Data")
    st.dataframe(st.session_state["uploaded_df"], use_container_width=True)
    invalid_count = len(df) < 24 or len(df) > 36
    if invalid_count:
        st.error("SolverV2 backend expects 24-36 participants (6 tables, size 4-6).")

    left, right = st.columns(2)
    with left:
        if st.button("Back to Event Setup"):
            go_to(2)
    with right:
        if st.button("Generate Groupings", type="primary", disabled=invalid_count):
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
    st.success("Solved with Gurobi optimizer.")
    st.metric("Diversity Score", f"{objective_value:.1f}")

    all_rounds = sorted(schedule_results["Round"].unique().tolist())
    for round_number in all_rounds:
        st.subheader(f"Round {round_number}")
        round_df = schedule_results[schedule_results["Round"] == round_number]
        table_numbers = sorted(round_df["Table"].unique().tolist())
        cols = st.columns(3)
        for idx, table_number in enumerate(table_numbers):
            table_rows = round_df[round_df["Table"] == table_number]
            person_indices = table_rows["Person_Index"].astype(int).tolist()
            table_df = participant_results.iloc[person_indices]
            score = table_diversity_score(table_df)

            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"**Table {table_number}**")
                    st.caption(f"Diversity score: {score}")
                    for _, person_row in table_df.iterrows():
                        person_id = str(person_row.get("Participant_ID", "")).strip()
                        st.write(f"- Person ID: {person_id}")

    schedule_cols = ["Participant_ID", "Round_1_Table", "Round_2_Table", "Round_3_Table"]
    if "Person_Index" in participant_results.columns:
        display_schedule = participant_results.sort_values("Person_Index")[schedule_cols].reset_index(drop=True)
    else:
        display_schedule = participant_results[schedule_cols].reset_index(drop=True)
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
