import re
from pathlib import Path
import inspect

import pandas as pd
import streamlit as st

from solver_backend import solve_solver_v2
from ui import inject_global_styles, render_hero, render_progress

st.set_page_config(page_title="Group Formation Studio", page_icon="groups", layout="wide")
inject_global_styles()

# Path to the sample template included with the app that facilitators download and fill out. 
TEMPLATE_PATH = Path(__file__).parent / "User_Input_Template_SAMPLE.xlsx"

# Utility functions for parsing and normalizing the uploaded Excel template data.
def _normalize_label(value) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_int(value, default: int) -> int:
    try:
        if pd.isna(value):
            return int(default)
        return int(float(str(value).strip()))
    except Exception:
        return int(default)

# Convert to float if possible, otherwise return None for missing/invalid values.
def _to_float_or_none(value) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except Exception:
        return None

# Finds the sheet that best matches any of the provided candidate names, using normalization and partial matching.
def _find_sheet_name(workbook: pd.ExcelFile, *candidate_names: str) -> str | None:
    normalized = {_normalize_label(name): name for name in workbook.sheet_names}
    for candidate in candidate_names:
        key = _normalize_label(candidate)
        if key in normalized:
            return normalized[key]
    for key, original in normalized.items():
        if any(_normalize_label(cand) in key for cand in candidate_names):
            return original
    return None

# Parses the event_setup sheet to extract configuration values, applying defaults and normalization as needed.
def _parse_event_setup(workbook: pd.ExcelFile) -> dict:
    defaults = {
        "number_of_tables": 6,
        "min_people_per_table": 4,
        "max_people_per_table": 6,
        "optimization_stage": "Multi",
        "number_of_rounds": 3,
    }

    sheet = _find_sheet_name(workbook, "event_setup", "event setup")
    if sheet is None:
        return defaults

    raw = pd.read_excel(workbook, sheet_name=sheet, header=None)
    values = {}
    for _, row in raw.iterrows():
        key = _normalize_label(row.iloc[0])
        if key:
            values[key] = row.iloc[1] if len(row) > 1 else None

    stage = _clean_text(values.get("optimization_stage")) or defaults["optimization_stage"]
    is_single = stage.lower().startswith("single")
    rounds = 1 if is_single else _to_int(values.get("number_of_rounds_if_multi"), defaults["number_of_rounds"])

    return {
        "number_of_tables": max(1, _to_int(values.get("number_of_tables"), defaults["number_of_tables"])),
        "min_people_per_table": max(1, _to_int(values.get("min_people_per_table"), defaults["min_people_per_table"])),
        "max_people_per_table": max(1, _to_int(values.get("max_people_per_table"), defaults["max_people_per_table"])),
        "optimization_stage": stage,
        "number_of_rounds": max(1, rounds),
    }

# Parses the traits sheet to extract characteristics and trait constraints. 
def _parse_traits_sheet(workbook: pd.ExcelFile) -> dict:
    sheet = _find_sheet_name(workbook, "traits")
    if sheet is None:
        return {
            "characteristics": [],
            "trait_targets": {},
            "trait_max_allowed": {},
            "trait_min_required": {},
        }

    traits_df = pd.read_excel(workbook, sheet_name=sheet, header=1)
    traits_df.columns = [str(col).strip() for col in traits_df.columns]

    trait_indices = sorted(
        {
            int(match.group(1))
            for col in traits_df.columns
            for match in [re.match(r"^Trait_(\d+)$", str(col).strip(), flags=re.IGNORECASE)]
            if match
        }
    )

    characteristics = []
    seen = set()
    trait_targets = {}
    trait_max_allowed = {}
    trait_min_required = {}

    characteristic_col = None
    for col in traits_df.columns:
        if _normalize_label(col) == "characteristics":
            characteristic_col = col
            break

    if characteristic_col is None:
        return {
            "characteristics": [],
            "trait_targets": {},
            "trait_max_allowed": {},
            "trait_min_required": {},
        }

    for _, row in traits_df.iterrows():
        characteristic = _clean_text(row.get(characteristic_col, ""))
        if not characteristic:
            continue
        if characteristic not in seen:
            seen.add(characteristic)
            characteristics.append(characteristic)

        for idx in trait_indices:
            trait = _clean_text(row.get(f"Trait_{idx}", ""))
            if not trait:
                continue
            key = (characteristic, trait)

            target = _to_float_or_none(row.get(f"Target_{idx}"))
            max_allowed = _to_float_or_none(row.get(f"MaxAllowed_{idx}"))
            min_required = _to_float_or_none(row.get(f"MinRequired_{idx}"))

            if target is not None:
                trait_targets[key] = target
            if max_allowed is not None and max_allowed > 0:
                trait_max_allowed[key] = max_allowed
            if min_required is not None and min_required > 0:
                trait_min_required[key] = min_required

    return {
        "characteristics": characteristics,
        "trait_targets": trait_targets,
        "trait_max_allowed": trait_max_allowed,
        "trait_min_required": trait_min_required,
    }

# Reads the participants sheet from the workbook as a DataDrame. 
def _read_participants_sheet(workbook: pd.ExcelFile) -> pd.DataFrame:
    sheet = _find_sheet_name(workbook, "participants")
    if sheet is None:
        raise ValueError(
            "Could not find a 'participants' sheet in the uploaded file. "
            f"Available sheets: {', '.join(workbook.sheet_names)}"
        )
    return pd.read_excel(workbook, sheet_name=sheet, header=1)

# Parses the table_lock sheet to extract any participants locked to specific tables, returning a mapping of Participant_ID to locked table number.
def _parse_locked_table_value(value) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.isdigit():
        return int(text)
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def _parse_table_lock_sheet(workbook: pd.ExcelFile, table_count: int) -> dict[str, int]:
    sheet = _find_sheet_name(workbook, "table_lock", "table locks")
    if sheet is None:
        return {}

    locks_df = pd.read_excel(workbook, sheet_name=sheet, header=1)
    if locks_df.empty:
        return {}

    locks_df.columns = [str(col).strip() for col in locks_df.columns]
    participant_col = None
    locked_col = None
    for col in locks_df.columns:
        norm = _normalize_label(col)
        if participant_col is None and norm.startswith("participant_id"):
            participant_col = col
        if locked_col is None and norm == "locked_table":
            locked_col = col

    if participant_col is None or locked_col is None:
        return {}

    locks: dict[str, int] = {}
    for _, row in locks_df.iterrows():
        participant_id = _clean_text(row.get(participant_col, ""))
        table_number = _parse_locked_table_value(row.get(locked_col))
        if not participant_id or table_number is None:
            continue
        if 1 <= table_number <= table_count:
            locks[participant_id] = table_number
    return locks

# Normalizes and transforms the raw participants DataFrame, extracting Participant_ID, Name, and characteristic-trait pairs 
# into a clean format suitable for the solver. Also returns the list of characteristics and count of generated IDs.
def _transform_participants(raw_df: pd.DataFrame, characteristics_from_traits: list[str]) -> tuple[pd.DataFrame, list[str], int]:
    df = raw_df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    rename_map = {}
    for col in df.columns:
        norm = _normalize_label(col)
        if norm == "participant_id":
            rename_map[col] = "Participant_ID"
        if norm == "participant_id_":
            rename_map[col] = "Participant_ID"
        if norm == "name":
            rename_map[col] = "Name"
    if rename_map:
        df = df.rename(columns=rename_map)

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
        blank_mask = df["Participant_ID"].astype(str).str.strip().eq("")
        for alt in alt_id_cols:
            if alt in df.columns:
                df.loc[blank_mask, "Participant_ID"] = df.loc[blank_mask, alt]
                break

    if "Participant_ID" not in df.columns:
        df["Participant_ID"] = ""
    if "Name" not in df.columns:
        df["Name"] = ""

    characteristic_cols = {
        int(match.group(1)): col
        for col in df.columns
        for match in [re.match(r"^Characteristic_(\d+)$", str(col).strip(), flags=re.IGNORECASE)]
        if match
    }
    trait_cols = {
        int(match.group(1)): col
        for col in df.columns
        for match in [re.match(r"^Trait_(\d+)$", str(col).strip(), flags=re.IGNORECASE)]
        if match
    }
    pair_indices = sorted(set(characteristic_cols).intersection(trait_cols))

    characteristics = []
    seen_characteristics = set()
    for c in characteristics_from_traits:
        c_text = _clean_text(c)
        if c_text and c_text not in seen_characteristics:
            seen_characteristics.add(c_text)
            characteristics.append(c_text)

    records = []
    for _, row in df.iterrows():
        participant_id = _clean_text(row.get("Participant_ID", ""))
        name = _clean_text(row.get("Name", ""))
        trait_map = {}

        for idx in pair_indices:
            characteristic = _clean_text(row.get(characteristic_cols[idx], ""))
            trait = _clean_text(row.get(trait_cols[idx], ""))
            if not characteristic or not trait:
                continue
            trait_map[characteristic] = trait
            if characteristic not in seen_characteristics:
                seen_characteristics.add(characteristic)
                characteristics.append(characteristic)

        if not participant_id and not name and not trait_map:
            continue

        record = {"Participant_ID": participant_id, "Name": name}
        record.update(trait_map)
        records.append(record)

    out = pd.DataFrame(records)
    if out.empty:
        out = pd.DataFrame(columns=["Participant_ID", "Name", *characteristics])

    for characteristic in characteristics:
        if characteristic not in out.columns:
            out[characteristic] = ""

    out = out[["Participant_ID", "Name", *characteristics]]

    blank_id_mask = out["Participant_ID"].astype(str).str.strip().eq("")
    generated_ids = int(blank_id_mask.sum())
    if generated_ids:
        out.loc[blank_id_mask, "Participant_ID"] = [f"AUTO_{i + 1}" for i in range(generated_ids)]

    return out.reset_index(drop=True), characteristics, generated_ids

# Parses the uploaded template file to extract event setup, traits configuration, 
# participant data, and locks. Returns a structured dictionary of all parsed information.
def _parse_template(uploaded_file) -> dict:
    workbook = pd.ExcelFile(uploaded_file)
    event_setup = _parse_event_setup(workbook)
    traits_config = _parse_traits_sheet(workbook)
    raw_participants = _read_participants_sheet(workbook)
    participants_df, characteristics, generated_ids = _transform_participants(
        raw_participants,
        traits_config["characteristics"],
    )
    locks = _parse_table_lock_sheet(workbook, event_setup["number_of_tables"])

    return {
        "raw_participants": raw_participants,
        "participants_df": participants_df,
        "characteristics": characteristics,
        "event_setup": event_setup,
        "trait_targets": traits_config["trait_targets"],
        "trait_max_allowed": traits_config["trait_max_allowed"],
        "trait_min_required": traits_config["trait_min_required"],
        "locks": locks,
        "generated_ids": generated_ids,
    }


def go_to(step: int) -> None:
    st.session_state["step"] = step
    st.rerun()

# Resets the app to return to home page. 
def start_over() -> None:
    for key in list(st.session_state.keys()):
        if key not in {"theme"}:
            del st.session_state[key]
    st.session_state["step"] = 1
    st.rerun()

# Diversity score for each table. 
def table_diversity_score(table_df: pd.DataFrame, diversity_cols: list[str]) -> int:
    score = 0
    for col in diversity_cols:
        if col in table_df.columns:
            values = table_df[col].dropna().astype(str).str.strip()
            values = values[values.ne("")]
            score += values.nunique(dropna=True)
    return int(score)

# Loads the solver and sets the solver to only run for 2 minutes at a maximum. 
def _run_solver_with_compatibility(
    participants_df: pd.DataFrame,
    characteristics: list[str],
    event_setup: dict,
    parsed: dict,
    locks: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float | None]:
    signature = inspect.signature(solve_solver_v2)
    supports_dynamic_args = "characteristics" in signature.parameters

    if supports_dynamic_args:
        return solve_solver_v2(
            participants_df,
            debug=True,
            time_limit_seconds=120.0,
            characteristics=characteristics,
            num_tables=event_setup["number_of_tables"],
            num_rounds=event_setup["number_of_rounds"],
            min_people_per_table=event_setup["min_people_per_table"],
            max_people_per_table=event_setup["max_people_per_table"],
            trait_targets=parsed["trait_targets"],
            trait_max_allowed=parsed["trait_max_allowed"],
            trait_min_required=parsed["trait_min_required"],
            locked_tables=locks,
        )

    # Legacy solver signature compatibility (older deployed module).
    participant_results, schedule_results, objective_value = solve_solver_v2(
        participants_df,
        debug=True,
        time_limit_seconds=120.0,
    )
    return participant_results, schedule_results, objective_value, None


st.session_state.setdefault("step", 1)
st.session_state.setdefault("event_name", "")

step = st.session_state["step"]
render_progress(step, total_steps=4)

if step > 1 and st.button("Start Over"):
    start_over()

# Step 1: Home page with app title, description, and button to start setup.
if step == 1:
    st.title("Group Formation Studio")
    st.caption("Build diverse teams from spreadsheet uploads")
    render_hero(
        "Design balanced, high-diversity groups in minutes",
        "Start by setting event details. Then upload your completed template to generate group assignments.",
    )
    if st.button("Start Setup", type="primary"):
        go_to(2)

# Step 2: Event setup page where users input event name and review settings. Then proceed to participant setup.
elif step == 2:
    st.title("Event Setup")
    render_hero(
        "Set the event context",
        "Name the run. Table and round settings are read from EVENT_SETUP in your uploaded template.",
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

# Template upload and participant setup page. Users download the template, fill it out, and upload it. 
# The app parses the uploaded file, extracts participant data and event configuration, and then allows users to generate group assignments.
elif step == 3:
    st.title("Participant Setup")
    render_hero(
        "Import participant data",
        "Upload your completed template. The app reads event setup, traits, participants, and optional locks.",
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

    min_total = event_setup["number_of_tables"] * event_setup["min_people_per_table"]
    max_total = event_setup["number_of_tables"] * event_setup["max_people_per_table"]

    st.metric("Participant rows", len(participants_df))
    st.caption(
        f"Event settings: {event_setup['number_of_tables']} tables, "
        f"{event_setup['min_people_per_table']}-{event_setup['max_people_per_table']} people/table, "
        f"{event_setup['number_of_rounds']} round(s), stage={event_setup['optimization_stage']}"
    )
    st.caption(f"Traits in model: {len(characteristics)}. Locked participants: {len(locks)}")

    st.subheader("Current Participant Data")
    st.dataframe(st.session_state["uploaded_df"], use_container_width=True)

    invalid_count = len(participants_df) < min_total or len(participants_df) > max_total
    if invalid_count:
        st.error(
            f"Participant count must be between {min_total} and {max_total} "
            f"for {event_setup['number_of_tables']} tables at size "
            f"{event_setup['min_people_per_table']}-{event_setup['max_people_per_table']}."
        )
    else:
        st.info("Group assignments can take up to 2 minutes to generate.")

    left, right = st.columns(2)
    with left:
        if st.button("Back to Event Setup"):
            go_to(2)
    with right:
        if st.button("Generate Groupings", type="primary", disabled=invalid_count):
            with st.spinner("Solving group assignments..."):
                try:
                    participant_results, schedule_results, objective_value, optimality_gap = _run_solver_with_compatibility(
                        participants_df=participants_df,
                        characteristics=characteristics,
                        event_setup=event_setup,
                        parsed=parsed,
                        locks=locks,
                    )
                except Exception as exc:
                    st.error(f"Solver failed: {exc}")
                    st.stop()

            st.session_state["participant_results"] = participant_results
            st.session_state["schedule_results"] = schedule_results
            st.session_state["objective_value"] = objective_value
            st.session_state["optimality_gap"] = optimality_gap
            go_to(4)

# Step 4: Results page showing the generated group assignments, diversity scores, and allowing users to download the results as CSV.
else:
    st.title("Run and Results")
    render_hero(
        "Generated group assignments",
        "Review and download your grouping results.",
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
                        person_id = _clean_text(person_row.get("Participant_ID", ""))
                        person_name = _clean_text(person_row.get("Name", ""))
                        if person_name:
                            st.write(f"- {person_name} ({person_id})")
                        else:
                            st.write(f"- Participant_ID: {person_id}")

    round_count = int(event_setup.get("number_of_rounds", 3))
    schedule_cols = ["Participant_ID", *[f"Round_{r}_Table" for r in range(1, round_count + 1)]]
    available_schedule_cols = [col for col in schedule_cols if col in participant_results.columns]

    if "Person_Index" in participant_results.columns:
        display_schedule = participant_results.sort_values("Person_Index")[available_schedule_cols].reset_index(drop=True)
    else:
        display_schedule = participant_results[available_schedule_cols].reset_index(drop=True)

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
