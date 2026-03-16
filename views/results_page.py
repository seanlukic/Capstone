import streamlit as st

from template_parser import _clean_text, table_diversity_score


# Step 4: Results page showing the generated group assignments, diversity scores, and allowing users to download the results as CSV.
def render(go_to) -> None:
    st.title("Run and Results")
    st.markdown(
        """
        <div class="hero">
            <h2 style="margin:0;">Generated group assignments</h2>
            <p class="app-subtitle">Review and download your grouping results.</p>
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

    participant_results = st.session_state.get("participant_results")
    schedule_results = st.session_state.get("schedule_results")
    objective_value = st.session_state.get("objective_value")
    optimality_gap = st.session_state.get("optimality_gap")
    diversity_cols = st.session_state.get("characteristics", [])
    event_setup = st.session_state.get("event_setup", {})

    if participant_results is None or schedule_results is None:
        st.error("No grouping results found. Go back and click Generate Groupings.")
        st.stop()

    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("Diversity Score", f"{objective_value:.1f}")
    with metrics_col2:
        if optimality_gap is None:
            st.metric("Optimality Gap", "N/A")
        else:
            st.metric("Optimality Gap", f"{optimality_gap:.2%}")

    all_rounds = sorted(schedule_results["Round"].unique().tolist())
    for round_number in all_rounds:
        st.subheader(f"Round {round_number}")
        round_df = schedule_results[schedule_results["Round"] == round_number]
        table_numbers = sorted(round_df["Table"].unique().tolist())
        cols = st.columns(max(1, min(3, len(table_numbers))))

        for idx, table_number in enumerate(table_numbers):
            table_rows = round_df[round_df["Table"] == table_number]
            person_indices = table_rows["Person_Index"].astype(int).tolist()
            table_df = participant_results.iloc[person_indices]
            score = table_diversity_score(table_df, diversity_cols)

            with cols[idx % len(cols)]:
                with st.container(border=True):
                    st.markdown(f"**Table {table_number}**")
                    st.caption(f"Diversity score: {score}")
                    for _, person_row in table_df.iterrows():
                        person_name = _clean_text(person_row.get("Name", ""))
                        if person_name:
                            st.write(f"- {person_name}")

    round_count = int(event_setup.get("number_of_rounds", 3))
    participant_label_col = "Name" if "Name" in participant_results.columns else "Participant_ID"
    round_table_cols = [f"Round_{r}_Table" for r in range(1, round_count + 1)]
    schedule_cols = [participant_label_col, *round_table_cols]
    available_schedule_cols = [col for col in schedule_cols if col in participant_results.columns]

    sort_cols = [col for col in round_table_cols if col in participant_results.columns]
    if participant_label_col in participant_results.columns:
        sort_cols.append(participant_label_col)

    if sort_cols:
        display_schedule = participant_results.sort_values(sort_cols)[available_schedule_cols].reset_index(drop=True)
    else:
        display_schedule = participant_results[available_schedule_cols].reset_index(drop=True)

    if participant_label_col == "Name":
        display_schedule = display_schedule.rename(columns={"Name": "Participant_Name"})

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
