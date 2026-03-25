from io import BytesIO
from pathlib import Path
import streamlit as st
from openpyxl import load_workbook
from template_parser import _clean_text, table_diversity_score


OUTPUT_TEMPLATE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "assets" / "Model_Output_Template_3.24.xlsx",
]
OUTPUT_DOWNLOAD_NAME = "Model_Output_Template_3.24.xlsx"


def _get_output_template_path() -> Path | None:
    for path in OUTPUT_TEMPLATE_CANDIDATES:
        if path.exists():
            return path
    return None


def _total_balance_interpretation(total_balance_score: float) -> str:
    if total_balance_score >= 95:
        return "Very evenly distributed"
    if total_balance_score >= 80:
        return "Small differences between tables"
    if total_balance_score >= 60:
        return "Noticeable imbalance"
    return "Uneven distribution across tables"


def _table_balance_interpretation(table_balance_score: float) -> str:
    if table_balance_score >= 100:
        return "All traits match targets"
    if table_balance_score >= 85:
        return "Most traits are correct"
    if table_balance_score >= 70:
        return "A few traits are off"
    return "Several traits need adjustment"


def _normalized_table_diversity_score(table_df, diversity_cols: list[str]) -> float:
    characteristic_count = max(1, len(diversity_cols))
    participant_count = max(1, len(table_df))
    raw_score = float(table_diversity_score(table_df, diversity_cols))
    return raw_score / characteristic_count / participant_count


def _calculate_total_balance_score(schedule_results, participant_results, diversity_cols: list[str]) -> float:
    all_rounds = sorted(schedule_results["Round"].unique().tolist())
    round_average_scores = []

    for round_number in all_rounds:
        round_df = schedule_results[schedule_results["Round"] == round_number]
        table_numbers = sorted(round_df["Table"].unique().tolist())
        table_scores = []
        for table_number in table_numbers:
            table_rows = round_df[round_df["Table"] == table_number]
            person_indices = table_rows["Person_Index"].astype(int).tolist()
            table_df = participant_results.iloc[person_indices]
            table_scores.append(_normalized_table_diversity_score(table_df, diversity_cols))

        if table_scores:
            round_average_scores.append(sum(table_scores) / len(table_scores))

    if not round_average_scores:
        return 0.0

    if len(round_average_scores) == 1:
        std_dev = 0.0
    else:
        mean_score = sum(round_average_scores) / len(round_average_scores)
        variance = sum((score - mean_score) ** 2 for score in round_average_scores) / len(round_average_scores)
        std_dev = variance ** 0.5

    total_balance_score = (1.0 - (std_dev / 0.5)) * 100.0
    return max(0.0, min(100.0, total_balance_score))


def _calculate_table_balance_scores(schedule_results, participant_results, diversity_cols: list[str]) -> list[tuple[int, float]]:
    score_by_table: dict[int, list[float]] = {}
    all_rounds = sorted(schedule_results["Round"].unique().tolist())

    for round_number in all_rounds:
        round_df = schedule_results[schedule_results["Round"] == round_number]
        table_numbers = sorted(round_df["Table"].unique().tolist())
        for table_number in table_numbers:
            table_rows = round_df[round_df["Table"] == table_number]
            person_indices = table_rows["Person_Index"].astype(int).tolist()
            table_df = participant_results.iloc[person_indices]
            score_by_table.setdefault(int(table_number), []).append(
                _normalized_table_diversity_score(table_df, diversity_cols) * 100.0
            )

    output_rows = []
    for table_number in sorted(score_by_table):
        scores = score_by_table[table_number]
        average_score = sum(scores) / len(scores) if scores else 0.0
        output_rows.append((table_number, max(0.0, min(100.0, average_score))))

    return output_rows


def _build_output_workbook(display_schedule, total_balance_score: float, table_balance_scores: list[tuple[int, float]]):
    template_path = _get_output_template_path()
    if template_path is None:
        raise FileNotFoundError(
            "Could not find the packaged output template in the repo."
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

    if "Total Balance Score" not in workbook.sheetnames:
        raise ValueError("Output template is missing the 'Total Balance Score' sheet.")

    score_sheet = workbook["Total Balance Score"]
    score_sheet["B7"] = f"{float(total_balance_score):.1f}%"
    score_sheet["B8"] = _total_balance_interpretation(float(total_balance_score))

    if "Table Balance Score" not in workbook.sheetnames:
        raise ValueError("Output template is missing the 'Table Balance Score' sheet.")

    table_sheet = workbook["Table Balance Score"]
    header_row = None
    for row_idx in range(1, table_sheet.max_row + 1):
        cell_a = _clean_text(table_sheet.cell(row=row_idx, column=1).value)
        cell_b = _clean_text(table_sheet.cell(row=row_idx, column=2).value)
        cell_c = _clean_text(table_sheet.cell(row=row_idx, column=3).value)
        if cell_a == "Table" and cell_b and cell_c == "Interpretation":
            header_row = row_idx
            break

    if header_row is None:
        raise ValueError("Could not find the per-table output header row in 'Table Balance Score'.")

    max_clear_row = max(table_sheet.max_row, header_row + len(table_balance_scores) + 50)
    for row_idx in range(header_row + 1, max_clear_row + 1):
        table_sheet.cell(row=row_idx, column=1).value = None
        table_sheet.cell(row=row_idx, column=2).value = None
        table_sheet.cell(row=row_idx, column=3).value = None

    for row_offset, (table_number, average_score) in enumerate(table_balance_scores, start=1):
        row_idx = header_row + row_offset
        table_sheet.cell(row=row_idx, column=1).value = f"Table {table_number}"
        table_sheet.cell(row=row_idx, column=2).value = f"{average_score:.1f}%"
        table_sheet.cell(row=row_idx, column=3).value = _table_balance_interpretation(average_score)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue(), OUTPUT_DOWNLOAD_NAME


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
    diversity_cols = st.session_state.get("characteristics", [])
    event_setup = st.session_state.get("event_setup", {})

    if participant_results is None or schedule_results is None:
        st.error("No grouping results found. Go back and click Generate Groupings.")
        st.stop()

    total_balance_score = _calculate_total_balance_score(schedule_results, participant_results, diversity_cols)
    table_balance_scores = _calculate_table_balance_scores(schedule_results, participant_results, diversity_cols)

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
        workbook_bytes, workbook_name = _build_output_workbook(
            display_schedule,
            total_balance_score,
            table_balance_scores,
        )
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

    left, right = st.columns(2)
    with left:
        if st.button("Back to Participants"):
            go_to(3)
    with right:
        st.info("If needed, go back and change participant data to regenerate groups.")
