from io import BytesIO
from pathlib import Path
import streamlit as st
from openpyxl import load_workbook
from template_parser import _clean_text, table_diversity_score


OUTPUT_TEMPLATE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "Model_Output_Template.xlsx",
    Path.home() / "Downloads" / "Model_Output_Template.xlsx",
]


def _get_output_template_path() -> Path | None:
    for path in OUTPUT_TEMPLATE_CANDIDATES:
        if path.exists():
            return path
    return None


def _build_output_workbook(display_schedule):
    template_path = _get_output_template_path()
    if template_path is None:
        raise FileNotFoundError(
            "Could not find Model_Output_Template.xlsx in the project folder or Downloads."
        )

    workbook = load_workbook(template_path)
    if "Current Assignments" not in workbook.sheetnames:
        raise ValueError("Output template is missing the 'Current Assignments' sheet.")

    worksheet = workbook["Current Assignments"]
    expected_columns = display_schedule.columns.tolist()
    header_row = None
    header_columns = {}

    for row_idx in range(1, worksheet.max_row + 1):
        row_values = [worksheet.cell(row=row_idx, column=col_idx).value for col_idx in range(1, worksheet.max_column + 1)]
        row_headers = {_clean_text(value): col_idx for col_idx, value in enumerate(row_values, start=1) if _clean_text(value)}
        if expected_columns and all(column in row_headers for column in expected_columns):
            header_row = row_idx
            header_columns = row_headers
            break

    if header_row is None:
        raise ValueError(
            "Could not find the assignment header row in 'Current Assignments'."
        )

    max_clear_row = max(worksheet.max_row, header_row + len(display_schedule) + 50)
    for row_idx in range(header_row + 1, max_clear_row + 1):
        for column in expected_columns:
            worksheet.cell(row=row_idx, column=header_columns[column]).value = None

    for row_offset, (_, row) in enumerate(display_schedule.iterrows(), start=1):
        for column in expected_columns:
            worksheet.cell(row=header_row + row_offset, column=header_columns[column]).value = row[column]

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue(), template_path.name


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

    try:
        workbook_bytes, workbook_name = _build_output_workbook(display_schedule)
    except Exception as exc:
        st.error(f"Could not build Excel output: {exc}")
        workbook_bytes = None
        workbook_name = None

    if workbook_bytes is not None:
        st.download_button(
            "Download Group Assignments (Excel)",
            data=workbook_bytes,
            file_name=workbook_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    left, right = st.columns(2)
    with left:
        if st.button("Back to Participants"):
            go_to(3)
    with right:
        st.info("If needed, go back and change participant data to regenerate groups.")
