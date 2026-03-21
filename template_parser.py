import re
from pathlib import Path

import pandas as pd


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


# Parses the participant_lock sheet to extract pairs of participants who cannot be seated together.
def _parse_participant_lock_sheet(workbook: pd.ExcelFile) -> list[tuple[str, str]]:
    sheet = _find_sheet_name(workbook, "participant_lock", "participant locks")
    if sheet is None:
        return []

    locks_df = pd.read_excel(workbook, sheet_name=sheet, header=1)
    if locks_df.empty:
        return []

    locks_df.columns = [str(col).strip() for col in locks_df.columns]
    participant_1_col = None
    participant_2_col = None
    for col in locks_df.columns:
        norm = _normalize_label(col)
        if participant_1_col is None and norm in {"participant_id1", "participant_1", "participant1"}:
            participant_1_col = col
        if participant_2_col is None and norm in {"participant_id2", "participant_2", "participant2"}:
            participant_2_col = col

    if participant_1_col is None or participant_2_col is None:
        return []

    separation_pairs: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for _, row in locks_df.iterrows():
        participant_1 = _clean_text(row.get(participant_1_col, ""))
        participant_2 = _clean_text(row.get(participant_2_col, ""))
        if not participant_1 or not participant_2 or participant_1 == participant_2:
            continue
        pair = tuple(sorted((participant_1, participant_2)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        separation_pairs.append(pair)
    return separation_pairs


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
# participant data, table locks, and participant separation locks. Returns a structured dictionary of all parsed information.
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
    participant_locks = _parse_participant_lock_sheet(workbook)

    return {
        "raw_participants": raw_participants,
        "participants_df": participants_df,
        "characteristics": characteristics,
        "event_setup": event_setup,
        "trait_targets": traits_config["trait_targets"],
        "trait_max_allowed": traits_config["trait_max_allowed"],
        "trait_min_required": traits_config["trait_min_required"],
        "locks": locks,
        "participant_locks": participant_locks,
        "generated_ids": generated_ids,
    }


# Diversity score for each table.
def table_diversity_score(table_df: pd.DataFrame, diversity_cols: list[str]) -> int:
    score = 0
    for col in diversity_cols:
        if col in table_df.columns:
            values = table_df[col].dropna().astype(str).str.strip()
            values = values[values.ne("")]
            score += values.nunique(dropna=True)
    return int(score)
