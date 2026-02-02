import pandas as pd
import streamlit as st
import numpy as np

from ui import inject_global_styles, render_hero, render_progress

st.set_page_config(page_title="Group Formation Studio", page_icon="groups", layout="wide")
inject_global_styles()

REQUIRED_COLS = ["Participant_ID", "Expertise", "Lived_Experience", "Minnesota"]
TRAIT_COLS = ["Expertise", "Lived_Experience", "Minnesota"]


def _normalized_text(value: object) -> str:
    text = str(value).strip()
    return text if text else "Unknown"


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


def _target_group_count(n_people: int, min_size: int = 4, max_size: int = 6) -> int:
    low = int(np.ceil(n_people / max_size))
    high = int(np.floor(n_people / min_size))
    if low > high:
        # Fallback for tiny inputs; still returns a valid group count.
        return max(1, int(np.round(n_people / max_size)))
    target = int(np.round(n_people / 5))
    return max(low, min(high, max(1, target)))


def _group_capacities(n_people: int, n_groups: int) -> list[int]:
    base = n_people // n_groups
    extra = n_people % n_groups
    return [base + 1 if g < extra else base for g in range(n_groups)]


def _solve_with_gurobi(df: pd.DataFrame, capacities: list[int]) -> tuple[pd.DataFrame, str]:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception as exc:
        raise RuntimeError(f"Gurobi is not available: {exc}") from exc

    work_df = df.copy().reset_index(drop=True)
    for col in TRAIT_COLS:
        work_df[col] = work_df[col].map(_normalized_text)

    n_people = len(work_df)
    n_groups = len(capacities)
    model = gp.Model("diverse_group_assignment")
    model.Params.OutputFlag = 0

    x = {(i, g): model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{g}") for i in range(n_people) for g in range(n_groups)}
    dev_plus = {}
    dev_minus = {}

    for i in range(n_people):
        model.addConstr(gp.quicksum(x[i, g] for g in range(n_groups)) == 1, name=f"assign_{i}")

    for g in range(n_groups):
        model.addConstr(gp.quicksum(x[i, g] for i in range(n_people)) == capacities[g], name=f"capacity_{g}")

    obj = gp.LinExpr()
    for trait in TRAIT_COLS:
        values = sorted(work_df[trait].unique().tolist())
        totals = work_df[trait].value_counts().to_dict()
        for val in values:
            target = totals.get(val, 0) / n_groups
            indicators = [1 if work_df.at[i, trait] == val else 0 for i in range(n_people)]
            for g in range(n_groups):
                dp = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"dp_{trait}_{val}_{g}")
                dm = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"dm_{trait}_{val}_{g}")
                dev_plus[(trait, val, g)] = dp
                dev_minus[(trait, val, g)] = dm
                model.addConstr(
                    gp.quicksum(indicators[i] * x[i, g] for i in range(n_people)) - target == dp - dm,
                    name=f"bal_{trait}_{val}_{g}",
                )
                obj += dp + dm

    model.setObjective(obj, GRB.MINIMIZE)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi could not find an optimal solution (status={model.Status}).")

    assignments = []
    for i in range(n_people):
        for g in range(n_groups):
            if x[i, g].X > 0.5:
                assignments.append(g + 1)
                break

    result = work_df.copy()
    result["Group"] = assignments
    return result, "gurobi"


def _solve_with_greedy(df: pd.DataFrame, capacities: list[int], random_seed: int = 42) -> tuple[pd.DataFrame, str]:
    work_df = df.copy().reset_index(drop=True)
    for col in TRAIT_COLS:
        work_df[col] = work_df[col].map(_normalized_text)

    rng = np.random.default_rng(random_seed)
    n_people = len(work_df)
    n_groups = len(capacities)

    rarity = np.zeros(n_people)
    for trait in TRAIT_COLS:
        freq = work_df[trait].value_counts()
        rarity += work_df[trait].map(lambda v: 1.0 / max(1, freq.get(v, 1))).to_numpy()

    order = np.arange(n_people)
    rng.shuffle(order)
    order = sorted(order, key=lambda i: -rarity[i])

    group_members = [[] for _ in range(n_groups)]
    group_counts = {trait: [dict() for _ in range(n_groups)] for trait in TRAIT_COLS}

    for i in order:
        best_group = None
        best_score = None
        row = work_df.iloc[i]
        for g in range(n_groups):
            if len(group_members[g]) >= capacities[g]:
                continue
            score = 0.0
            for trait in TRAIT_COLS:
                val = row[trait]
                current = group_counts[trait][g].get(val, 0)
                score += (current + 1) ** 2
            if best_score is None or score < best_score:
                best_score = score
                best_group = g
        group_members[best_group].append(i)
        for trait in TRAIT_COLS:
            val = row[trait]
            group_counts[trait][best_group][val] = group_counts[trait][best_group].get(val, 0) + 1

    assignments = [0] * n_people
    for g, members in enumerate(group_members, start=1):
        for i in members:
            assignments[i] = g

    result = work_df.copy()
    result["Group"] = assignments
    return result, "greedy"


def solve_groupings(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    n_people = len(df)
    n_groups = _target_group_count(n_people)
    capacities = _group_capacities(n_people, n_groups)
    try:
        return _solve_with_gurobi(df, capacities)
    except Exception:
        return _solve_with_greedy(df, capacities)


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
    mode = st.radio("Input method", ["Upload Excel", "Add manually"], horizontal=True)
    df = None
    if mode == "Upload Excel":
        uploaded = st.file_uploader("Upload participant Excel file", type=["xlsx"])
        if uploaded is None:
            st.info("Upload a .xlsx file to continue, or switch to manual entry.")
            st.stop()
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
    st.subheader("Current Participant Data")
    st.dataframe(df, use_container_width=True)

    left, right = st.columns(2)
    with left:
        if st.button("Back to Event Setup"):
            go_to(2)
    with right:
        if st.button("Generate Groupings", type="primary"):
            with st.spinner("Solving group assignments..."):
                result_df, solver_used = solve_groupings(df)
            st.session_state["group_results"] = result_df
            st.session_state["solver_used"] = solver_used
            go_to(4)

else:
    st.title("Run and Results")
    render_hero(
        "Generated group assignments",
        "Review and download your grouping results.",
    )
    group_results = st.session_state.get("group_results")
    if group_results is None:
        st.error("No grouping results found. Go back and click Generate Groupings.")
        st.stop()
    solver_used = st.session_state.get("solver_used", "unknown")
    if solver_used == "gurobi":
        st.success("Solved with Gurobi optimizer.")
    else:
        st.warning("Gurobi not available, used built-in greedy solver.")

    display_cols = ["Group", "Participant_ID", "Expertise", "Lived_Experience", "Minnesota"]
    group_results = group_results[display_cols].sort_values(["Group", "Participant_ID"]).reset_index(drop=True)
    st.dataframe(group_results, use_container_width=True)

    csv_data = group_results.to_csv(index=False).encode("utf-8")
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
