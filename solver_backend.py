import highspy # Imports HiGHS 
import numpy as np 
import pandas as pd

# Helper functions for data extraction, cleaning, and model preparation. 
# These functions handle the transformation of raw input data into the structured format required by the optimization model, 
# as well as building the model itself using the HiGHS library.
def _extract_attribute_values(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return values.drop_duplicates().tolist()


def _clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_trait_dict(raw: dict | None) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    if not raw:
        return out

    for key, value in raw.items():
        if isinstance(key, tuple) and len(key) == 2:
            characteristic = _clean_text(key[0])
            trait = _clean_text(key[1])
        else:
            text_key = _clean_text(key)
            if "|" not in text_key:
                continue
            characteristic, trait = [part.strip() for part in text_key.split("|", 1)]

        if not characteristic or not trait:
            continue

        try:
            numeric_value = float(value)
        except Exception:
            continue

        out[(characteristic, trait)] = numeric_value

    return out


def _prepare_parameters(
    df: pd.DataFrame,
    *,
    v_target: float = 5.0,
    lam: float = 50.0,
    w1_value: float = 10.0,
    w2_value: float = 20.0,
    w1_bar_value: float | None = None,
    w2_bar_value: float | None = None,
    v_bar: dict | None = None,
    v_under: dict | None = None,
    characteristics: list[str] | None = None,
    num_tables: int = 6,
    num_rounds: int = 3,
    min_people_per_table: int = 4,
    max_people_per_table: int = 6,
    trait_targets: dict | None = None,
    trait_max_allowed: dict | None = None,
    trait_min_required: dict | None = None,
    locked_tables: dict | None = None,
    separation_pairs: list | None = None,
) -> dict:
    work_df = df.copy().reset_index(drop=True)

    if "Participant_ID" not in work_df.columns:
        work_df["Participant_ID"] = [f"AUTO_{i + 1}" for i in range(len(work_df))]

    if "Name" not in work_df.columns:
        work_df["Name"] = ""

    provided_characteristics = []
    if characteristics:
        for col in characteristics:
            text = _clean_text(col)
            if text and text not in provided_characteristics:
                provided_characteristics.append(text)

    if provided_characteristics:
        K = provided_characteristics
    else:
        excluded = {"participant_id", "name", "person_index"}
        K = []
        for col in work_df.columns:
            col_name = str(col)
            lowered = col_name.strip().lower()
            if lowered in excluded:
                continue
            if lowered.startswith("round_") and lowered.endswith("_table"):
                continue
            if lowered.startswith("locked_table"):
                continue
            K.append(col_name)

    for k in K:
        if k not in work_df.columns:
            work_df[k] = ""

    trait_targets_map = _normalize_trait_dict(trait_targets)
    trait_max_map = _normalize_trait_dict(trait_max_allowed)
    trait_min_map = _normalize_trait_dict(trait_min_required)

    Ak = {k: _extract_attribute_values(work_df, k) for k in K}
    for characteristic, trait in list(trait_targets_map.keys()) + list(trait_max_map.keys()) + list(trait_min_map.keys()):
        if characteristic in Ak and trait not in Ak[characteristic]:
            Ak[characteristic].append(trait)

    I = range(len(work_df)) # Number of participant indices
    T = range(max(1, int(num_tables))) # Number of tables
    R = range(max(1, int(num_rounds))) # Number of rounds

    l = max(1, int(min_people_per_table))
    u = max(1, int(max_people_per_table))
    if l > u:
        raise ValueError(f"Invalid table size bounds: min={l} > max={u}")

    w1_bar_default = float(w1_value if w1_bar_value is None else w1_bar_value)
    w2_bar_default = float(w2_value if w2_bar_value is None else w2_bar_value)

    b = {}
    for i in I:
        for k in K:
            for a in Ak[k]:
                b[i, k, a] = 0

    for idx, row in work_df.iterrows():
        i = idx
        for k in K:
            if k in work_df.columns and pd.notna(row[k]):
                val = str(row[k]).strip()
                if val in Ak[k]:
                    b[i, k, val] = 1

    v = {}
    for k in K:
        for a in Ak[k]:
            target_value = float(trait_targets_map.get((k, a), v_target))
            for t in T:
                v[k, a, t] = target_value

    v_bar_dict = None
    if v_bar is not None:
        v_bar_dict = {}
        for k in K:
            for a in Ak[k]:
                for t in T:
                    key = (k, a, t)
                    if key not in v_bar:
                        raise ValueError(f"Missing hard upper bound for {key}")
                    v_bar_dict[key] = float(v_bar[key])

    if trait_max_map:
        if v_bar_dict is None:
            v_bar_dict = {}
        for (k, a), max_allowed in trait_max_map.items():
            if k not in Ak or a not in Ak[k]:
                continue
            for t in T:
                v_bar_dict[k, a, t] = float(max_allowed)

    v_under_dict = None
    if v_under is not None:
        v_under_dict = {}
        for k in K:
            for a in Ak[k]:
                for t in T:
                    key = (k, a, t)
                    if key not in v_under:
                        raise ValueError(f"Missing hard lower bound for {key}")
                    v_under_dict[key] = float(v_under[key])

    if trait_min_map:
        if v_under_dict is None:
            v_under_dict = {}
        for (k, a), min_required in trait_min_map.items():
            if k not in Ak or a not in Ak[k]:
                continue
            for t in T:
                v_under_dict[k, a, t] = float(min_required)

    w1_bar = {}
    w2_bar = {}
    w1 = {}
    w2 = {}
    for k in K:
        for a in Ak[k]:
            for t in T:
                w1_bar[k, a, t] = w1_bar_default
                w2_bar[k, a, t] = w2_bar_default
                w1[k, a, t] = float(w1_value)
                w2[k, a, t] = float(w2_value)

    locked_indices = {}
    # Map Participant_ID to index for locked tables and separation pairs
    id_to_index = {
        _clean_text(work_df.at[i, "Participant_ID"]): i
        for i in I
    }

    separation_indices = set()
    if separation_pairs:
        # separation_pairs expected as an iterable of pairs: [(id1, id2), ...]
        for pair in separation_pairs:
            try:
                a_id, b_id = pair
            except Exception:
                # skip invalid entries
                continue
            a_pid = _clean_text(a_id)
            b_pid = _clean_text(b_id)
            if not a_pid or not b_pid or a_pid == b_pid:
                continue
            if a_pid not in id_to_index or b_pid not in id_to_index:
                continue
            i = id_to_index[a_pid]
            j = id_to_index[b_pid]
            if i == j:
                continue
            if i > j:
                i, j = j, i
            separation_indices.add((i, j))

    if locked_tables:
        id_to_index = {
            _clean_text(work_df.at[i, "Participant_ID"]): i
            for i in I
        }
        for participant_id, table_value in locked_tables.items():
            pid = _clean_text(participant_id)
            if not pid:
                continue
            if pid not in id_to_index:
                continue
            try:
                table_number = int(float(table_value))
            except Exception:
                continue
            if table_number < 1 or table_number > len(T):
                continue
            locked_indices[id_to_index[pid]] = table_number - 1
    # include separation indices in returned params
    
    return {
        "df": work_df,
        "K": K,
        "Ak": Ak,
        "I": I,
        "T": T,
        "R": R,
        "l": l,
        "u": u,
        "lam": float(lam),
        "b": b,
        "v": v,
        "v_bar": v_bar_dict,
        "v_under": v_under_dict,
        "w1_bar": w1_bar,
        "w2_bar": w2_bar,
        "w1": w1,
        "w2": w2,
        "locked_indices": locked_indices,
        "separation_pairs_indices": separation_indices,
    }


def _add_var(
    model: highspy.Highs,
    lb: float,
    ub: float,
    cost: float = 0.0,
    integrality: highspy.HighsVarType = highspy.HighsVarType.kContinuous,
) -> int:
    idx = model.getNumCol()
    model.addVar(lb, ub)
    if cost != 0.0:
        model.changeColCost(idx, cost)
    if integrality != highspy.HighsVarType.kContinuous:
        model.changeColIntegrality(idx, integrality)
    return idx

# Helper function to add a constraint row to the model. This function takes the model, the lower and upper bounds of the constraint,
def _add_row(model: highspy.Highs, lower: float, upper: float, indices: list[int], values: list[float]) -> None:
    num_nz = len(indices)
    idx = np.array(indices, dtype=np.int32)
    val = np.array(values, dtype=np.float64)
    model.addRow(lower, upper, num_nz, idx, val)

# Builds the optimization model using the HiGHS library. This function takes the prepared parameters and constructs the decision variables, objective function, and constraints according to the problem formulation.
def _build_model(params: dict) -> tuple[highspy.Highs, dict, dict]:
    K = params["K"]
    Ak = params["Ak"]
    I = params["I"]
    T = params["T"]
    R = params["R"]
    l = params["l"]
    u = params["u"]
    lam = params["lam"]
    b = params["b"]
    v = params["v"]
    v_bar = params["v_bar"]
    v_under = params["v_under"]
    w1_bar = params["w1_bar"]
    w2_bar = params["w2_bar"]
    w1 = params["w1"]
    w2 = params["w2"]
    locked_indices = params["locked_indices"]
    separation_pairs_indices = params["separation_pairs_indices"]

    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
    model.changeObjectiveSense(highspy.ObjSense.kMinimize)

    inf = highspy.kHighsInf

# Decision variables:
    Y = {}
    for i in I:
        for t in T:
            for r in R:
                Y[i, t, r] = _add_var(
                    model,
                    lb=0.0,
                    ub=1.0,
                    integrality=highspy.HighsVarType.kInteger,
                )

    W = {}
    for t in T:
        for r in R:
            W[t, r] = _add_var(
                model,
                lb=0.0,
                ub=1.0,
                integrality=highspy.HighsVarType.kInteger,
            )

    E1_bar = {}
    for k in K:
        for a in Ak[k]:
            for t in T:
                for r in R:
                    E1_bar[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=1.0,
                        cost=w1_bar[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )

    E2_bar = {}
    for k in K:
        for a in Ak[k]:
            for t in T:
                for r in R:
                    E2_bar[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=inf,
                        cost=w2_bar[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )

    E1 = {}
    for k in K:
        for a in Ak[k]:
            for t in T:
                for r in R:
                    E1[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=1.0,
                        cost=w1[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )

    E2 = {}
    for k in K:
        for a in Ak[k]:
            for t in T:
                for r in R:
                    E2[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=inf,
                        cost=w2[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )

    P = {}
    for i in I:
        for j in I:
            if j > i:
                for r in R:
                    P[i, j, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=1.0,
                        integrality=highspy.HighsVarType.kInteger,
                    )

    H = {}
    for i in I:
        for j in I:
            if j > i:
                H[i, j] = _add_var(
                    model,
                    lb=0.0,
                    ub=1.0,
                    cost=lam,
                    integrality=highspy.HighsVarType.kInteger,
                )

    for t in T:
        for r in R:
            indices = [Y[i, t, r] for i in I] + [W[t, r]]
            values = [1.0 for _ in I] + [-float(l)]
            _add_row(model, 0.0, inf, indices, values)

    for t in T:
        for r in R:
            indices = [Y[i, t, r] for i in I] + [W[t, r]]
            values = [1.0 for _ in I] + [-float(u)]
            _add_row(model, -inf, 0.0, indices, values)

    for i in I:
        for r in R:
            indices = [Y[i, t, r] for t in T]
            values = [1.0 for _ in T]
            _add_row(model, 1.0, 1.0, indices, values)

    for i, locked_table_idx in locked_indices.items():
        for r in R:
            _add_row(model, 1.0, 1.0, [Y[i, locked_table_idx, r]], [1.0])

    if len(params["df"]) > 0 and 0 not in locked_indices:
        _add_row(model, 1.0, 1.0, [Y[0, 0, 0]], [1.0])

    for i, j in separation_pairs_indices:
        for t in T:
            for r in R:
                _add_row(model, -highspy.kHighsInf, 1.0, [Y[i, t, r], Y[j, t, r]], [1.0, 1.0])

    for t in range(len(T) - 1):
        for r in R:
            indices = [W[t, r], W[t + 1, r]]
            values = [1.0, -1.0]
            _add_row(model, 0.0, inf, indices, values)

    for k in K:
        for a in Ak[k]:
            for t in T:
                for r in R:
                    indices = []
                    values = []
                    for i in I:
                        if b[i, k, a] != 0:
                            indices.append(Y[i, t, r])
                            values.append(float(b[i, k, a]))
                    indices.extend([E1_bar[k, a, t, r], E2_bar[k, a, t, r], E1[k, a, t, r], E2[k, a, t, r]])
                    values.extend([-1.0, -1.0, 1.0, 1.0])
                    _add_row(model, float(v[k, a, t]), float(v[k, a, t]), indices, values)

    if v_bar is not None:
        for k in K:
            for a in Ak[k]:
                for t in T:
                    for r in R:
                        indices = []
                        values = []
                        for i in I:
                            if b[i, k, a] != 0:
                                indices.append(Y[i, t, r])
                                values.append(float(b[i, k, a]))
                        if indices:
                            _add_row(model, -inf, float(v_bar[k, a, t]), indices, values)

    if v_under is not None:
        for k in K:
            for a in Ak[k]:
                for t in T:
                    for r in R:
                        indices = []
                        values = []
                        for i in I:
                            if b[i, k, a] != 0:
                                indices.append(Y[i, t, r])
                                values.append(float(b[i, k, a]))
                        if indices:
                            _add_row(model, float(v_under[k, a, t]), inf, indices, values)

    for i in I:
        for j in I:
            if j > i:
                for t in T:
                    for r in R:
                        indices = [P[i, j, r], Y[i, t, r], Y[j, t, r]]
                        values = [1.0, -1.0, -1.0]
                        _add_row(model, -1.0, inf, indices, values)

    for i in I:
        for j in I:
            if j > i:
                for r in R:
                    indices = [H[i, j], P[i, j, r]]
                    values = [1.0, -1.0]
                    _add_row(model, 0.0, inf, indices, values)

    return model, Y, W


def solve_solver_v2(
    df: pd.DataFrame,
    debug: bool = False,
    time_limit_seconds: float | None = None,
    v_target: float = 5.0,
    lam: float = 50.0,
    w1_value: float = 10.0,
    w2_value: float = 20.0,
    w1_bar_value: float | None = None,
    w2_bar_value: float | None = None,
    v_bar: dict | None = None,
    v_under: dict | None = None,
    characteristics: list[str] | None = None,
    num_tables: int = 6,
    num_rounds: int = 3,
    min_people_per_table: int = 4,
    max_people_per_table: int = 6,
    trait_targets: dict | None = None,
    trait_max_allowed: dict | None = None,
    trait_min_required: dict | None = None,
    locked_tables: dict | None = None,
    separation_pairs: list | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float | None]:
    params = _prepare_parameters(
        df,
        v_target=v_target,
        lam=lam,
        w1_value=w1_value,
        w2_value=w2_value,
        w1_bar_value=w1_bar_value,
        w2_bar_value=w2_bar_value,
        v_bar=v_bar,
        v_under=v_under,
        characteristics=characteristics,
        num_tables=num_tables,
        num_rounds=num_rounds,
        min_people_per_table=min_people_per_table,
        max_people_per_table=max_people_per_table,
        trait_targets=trait_targets,
        trait_max_allowed=trait_max_allowed,
        trait_min_required=trait_min_required,
        locked_tables=locked_tables,
        separation_pairs=separation_pairs,
    )
    model, Y, W = _build_model(params)
    model.setOptionValue("output_flag", bool(debug))
    if time_limit_seconds is not None:
        model.setOptionValue("time_limit", float(time_limit_seconds))
    model.run()

    status = model.getModelStatus()
    info = model.getInfo()
    if status != highspy.HighsModelStatus.kOptimal:
        if (
            status == highspy.HighsModelStatus.kTimeLimit
            and info.primal_solution_status == highspy.SolutionStatus.kSolutionStatusFeasible
        ):
            pass
        else:
            raise RuntimeError(f"Optimization failed with status {status}")

    solution = model.getSolution()
    col_value = solution.col_value

    work_df = params["df"].copy()
    I = params["I"]
    T = params["T"]
    R = params["R"]
    work_df["Person_Index"] = list(I)

    row_assignments = {}
    round_table_rows = []
    for r in R:
        for t in T:
            if col_value[W[t, r]] > 0.5:
                people_in_t = [i for i in I if col_value[Y[i, t, r]] > 0.5]
                people_in_t.sort()
                for i in people_in_t:
                    row_assignments[(i, r)] = t + 1
                    round_table_rows.append(
                        {
                            "Round": r + 1,
                            "Table": t + 1,
                            "Person_Index": i,
                            "Participant_ID": work_df.at[i, "Participant_ID"],
                        }
                    )

    for r in R:
        col = f"Round_{r + 1}_Table"
        work_df[col] = [row_assignments.get((i, r), None) for i in I]

    schedule_df = pd.DataFrame(round_table_rows)
    if not schedule_df.empty:
        schedule_df = schedule_df.sort_values(["Round", "Table", "Participant_ID"], kind="stable")

    objective = getattr(info, "objective_function_value", None)
    if objective is None:
        objective = 0.0

    mip_gap = getattr(info, "mip_gap", None)
    gap_value = None if mip_gap is None else float(mip_gap)

    return work_df, schedule_df, float(objective), gap_value
