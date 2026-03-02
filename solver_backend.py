import highspy  # HiGHS optimization library (highspy)
import numpy as np  # Numerical arrays for HiGHS row building
import pandas as pd  # Import pandas for data manipulation


def _extract_attribute_values(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )
    values = values[values.ne("")]
    return values.drop_duplicates().tolist()


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
) -> dict:
    work_df = df.copy().reset_index(drop=True)  # Work on a copy to avoid mutating user data

    # SETS
    # Characteristics from Maass World Cafe model
    K = ["Expertise", "Lived_Experience", "Minnesota"]
    Ak = {k: _extract_attribute_values(work_df, k) for k in K}

    I = range(len(work_df))  # Set of people
    T = range(6)  # Set of tables
    R = range(3)  # Set of rounds

    # PARAMETERS
    l = 4  # Minimum table size
    u = 6  # Maximum table size
    w1_bar_default = float(w1_value if w1_bar_value is None else w1_bar_value)
    w2_bar_default = float(w2_value if w2_bar_value is None else w2_bar_value)

    b = {}  # b_iak: 1 if person i has attribute a of characteristic k
    for i in I:  # Loop through all people
        for k in K:  # Loop through all characteristics
            for a in Ak[k]:  # Loop through all attributes of characteristic k
                b[i, k, a] = 0

    # Populate b based on uploaded/manual dataframe
    for idx, row in work_df.iterrows():  # Loop through each row in dataframe
        i = idx
        for k in K:
            if k in work_df.columns and pd.notna(row[k]):
                val = str(row[k]).strip()
                if val in Ak[k]:
                    b[i, k, val] = 1

    v = {}  # v_akt: target number of people with attribute a at table t
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                v[k, a, t] = float(v_target)

    # Optional hard bounds: off by default unless explicitly provided.
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

    # Penalty weights for overuse and underuse
    w1_bar = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w1_bar[k, a, t] = w1_bar_default

    w2_bar = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w2_bar[k, a, t] = w2_bar_default

    w1 = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w1[k, a, t] = float(w1_value)

    w2 = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w2[k, a, t] = float(w2_value)

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

def _add_row(model: highspy.Highs, lower: float, upper: float, indices: list[int], values: list[float]) -> None:
    num_nz = len(indices)
    idx = np.array(indices, dtype=np.int32)
    val = np.array(values, dtype=np.float64)
    model.addRow(lower, upper, num_nz, idx, val)


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

    model = highspy.Highs()  # Create HiGHS model object
    model.setOptionValue("output_flag", False)
    model.changeObjectiveSense(highspy.ObjSense.kMinimize)

    inf = highspy.kHighsInf

    # DECISION VARIABLES
    # Y_itr: 1 if person i is at table t in round r
    Y = {}  # Y_itr: Assignment variables
    for i in I:  # Loop through all people
        for t in T:  # Loop through all tables
            for r in R:  # Loop through all rounds
                Y[i, t, r] = _add_var(
                    model,
                    lb=0.0,
                    ub=1.0,
                    integrality=highspy.HighsVarType.kInteger,
                )  # 1 if person i is at table t in round r

    W = {}  # W_tr: Table usage variables
    for t in T:  # Loop through all tables
        for r in R:  # Loop through all rounds
            W[t, r] = _add_var(
                model,
                lb=0.0,
                ub=1.0,
                integrality=highspy.HighsVarType.kInteger,
            )  # 1 if table t is used in round r

    E1_bar = {}  # E1_bar_aktr: Binary variable for first overuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E1_bar[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=1.0,
                        cost=w1_bar[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )  # 1 if attribute a is overused once

    E2_bar = {}  # E2_bar_aktr: Number of additional uses beyond first overuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E2_bar[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=inf,
                        cost=w2_bar[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )  # Number of additional overuses

    E1 = {}  # E1_aktr: Binary variable for first underuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E1[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=1.0,
                        cost=w1[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )  # 1 if attribute a is underused once

    E2 = {}  # E2_aktr: Number of additional under uses beyond first underuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E2[k, a, t, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=inf,
                        cost=w2[k, a, t],
                        integrality=highspy.HighsVarType.kInteger,
                    )  # Number of additional underuses

    P = {}  # P_ijr: 1 if persons i and j are at same table in round r
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only create for j > i to avoid duplicates
                for r in R:  # Loop through all rounds
                    P[i, j, r] = _add_var(
                        model,
                        lb=0.0,
                        ub=1.0,
                        integrality=highspy.HighsVarType.kInteger,
                    )  # 1 if i and j meet in round r

    H = {}  # H_ij: 1 if persons i and j have ever been together across all rounds
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only create for j > i to avoid duplicates
                H[i, j] = _add_var(
                    model,
                    lb=0.0,
                    ub=1.0,
                    cost=lam,
                    integrality=highspy.HighsVarType.kInteger,
                )  # 1 if i and j have ever met

    # CONSTRAINTS
    # Constraint 1: Lower bound on table size if table is used
    for t in T:  # Loop through all tables
        for r in R:  # Loop through all rounds
            indices = [Y[i, t, r] for i in I] + [W[t, r]]
            values = [1.0 for _ in I] + [-float(l)]
            _add_row(model, 0.0, inf, indices, values)  # Minimum l people if table used

    # Constraint 2: Upper bound on table size
    for t in T:  # Loop through all tables
        for r in R:  # Loop through all rounds
            indices = [Y[i, t, r] for i in I] + [W[t, r]]
            values = [1.0 for _ in I] + [-float(u)]
            _add_row(model, -inf, 0.0, indices, values)  # Maximum u people per table

    # Constraint 3: Each person assigned to exactly one table per round
    for i in I:  # Loop through all people
        for r in R:  # Loop through all rounds
            indices = [Y[i, t, r] for t in T]
            values = [1.0 for _ in T]
            _add_row(model, 1.0, 1.0, indices, values)  # Each person at exactly one table

    # Constraint 4: Anchor first person for faster solving
    if len(params["df"]) > 0:
        _add_row(model, 1.0, 1.0, [Y[0, 0, 0]], [1.0])  # Person 0 at table 0 in round 0

    # Constraint 5: Symmetry breaking for table usage
    for t in range(len(T) - 1):  # Loop through all tables except last
        for r in R:  # Loop through all rounds
            indices = [W[t, r], W[t + 1, r]]
            values = [1.0, -1.0]
            _add_row(model, 0.0, inf, indices, values)  # Table t must be used before table t+1

    # Constraint 6: Tracks deviations from target attribute levels
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    indices = []
                    values = []
                    for i in I:
                        if b[i, k, a] != 0:
                            indices.append(Y[i, t, r])
                            values.append(float(b[i, k, a]))
                    indices.extend([E1_bar[k, a, t, r], E2_bar[k, a, t, r], E1[k, a, t, r], E2[k, a, t, r]])
                    values.extend([-1.0, -1.0, 1.0, 1.0])
                    _add_row(model, float(v[k, a, t]), float(v[k, a, t]), indices, values)  # Actual count +/- deviations = target

    # Optional hard bounds from updated model spec; disabled unless provided.
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
                        _add_row(model, float(v_under[k, a, t]), inf, indices, values)

    # Constraint 14: Pair meeting linearization
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only for j > i to avoid duplicates
                for t in T:  # Loop through all tables
                    for r in R:  # Loop through all rounds
                        indices = [P[i, j, r], Y[i, t, r], Y[j, t, r]]
                        values = [1.0, -1.0, -1.0]
                        _add_row(model, -1.0, inf, indices, values)  # If both at table t, then P = 1

    # Constraint 15: Ever-met indicator across rounds
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only for j > i to avoid duplicates
                for r in R:  # Loop through all rounds
                    indices = [H[i, j], P[i, j, r]]
                    values = [1.0, -1.0]
                    _add_row(model, 0.0, inf, indices, values)  # If met in round r, then H = 1

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
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
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
    )
    model, Y, W = _build_model(params)
    model.setOptionValue("output_flag", bool(debug))
    if time_limit_seconds is not None:
        model.setOptionValue("time_limit", float(time_limit_seconds))
    model.run()  # Solve the model

    # Extract solution (same pattern as SolverV2 notebook)
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
    for r in R:  # Loop through all rounds
        for t in T:  # Loop through all tables
            if col_value[W[t, r]] > 0.5:  # If table t is used in round r
                people_in_t = [i for i in I if col_value[Y[i, t, r]] > 0.5]  # Get people assigned to table t in round r
                people_in_t.sort()  # Sort IDs for cleaner output
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

    schedule_df = pd.DataFrame(round_table_rows).sort_values(
        ["Round", "Table", "Participant_ID"], kind="stable"
    )

    return work_df, schedule_df, float(info.objective_function_value)
