import gurobipy as gp  # Import Gurobi optimization library
import pandas as pd  # Import pandas for data manipulation


def _prepare_parameters(df: pd.DataFrame) -> dict:
    work_df = df.copy().reset_index(drop=True)  # Work on a copy to avoid mutating user data

    # SETS
    # Characteristics from Maass World Cafe model
    K = ["Expertise", "Lived_Experience", "Minnesota"]
    Ak = {
        "Expertise": ["Social_Science", "Computational_Math", "Real_World"],
        "Lived_Experience": [],
        "Minnesota": [],
    }

    if "Lived_Experience" in work_df.columns:  # Check if Lived_Experience column exists
        Ak["Lived_Experience"] = work_df["Lived_Experience"].dropna().astype(str).unique().tolist()  # Get unique non-null values
    if "Minnesota" in work_df.columns:  # Check if Minnesota column exists
        Ak["Minnesota"] = work_df["Minnesota"].dropna().astype(str).unique().tolist()  # Get unique non-null values

    I = range(len(work_df))  # Set of people
    T = range(6)  # Set of tables
    R = range(3)  # Set of rounds

    # PARAMETERS
    l = 4  # Minimum table size
    u = 6  # Maximum table size
    lam = 50  # Penalty weight for people meeting repeatedly

    b = {}  # b_iak: 1 if person i has attribute a of characteristic k
    for i in I:  # Loop through all people
        for k in K:  # Loop through all characteristics
            for a in Ak[k]:  # Loop through all attributes of characteristic k
                b[i, k, a] = 0

    # Populate b based on uploaded/manual dataframe
    for idx, row in work_df.iterrows():  # Loop through each row in dataframe
        i = idx
        if "Expertise" in work_df.columns and pd.notna(row["Expertise"]):  # For Expertise
            expertise_val = str(row["Expertise"])
            if expertise_val in Ak["Expertise"]:
                b[i, "Expertise", expertise_val] = 1
        if "Lived_Experience" in work_df.columns and pd.notna(row["Lived_Experience"]):  # For Lived_Experience
            lived_val = str(row["Lived_Experience"])
            if lived_val in Ak["Lived_Experience"]:
                b[i, "Lived_Experience", lived_val] = 1
        if "Minnesota" in work_df.columns and pd.notna(row["Minnesota"]):  # For Minnesota
            mn_val = str(row["Minnesota"])
            if mn_val in Ak["Minnesota"]:
                b[i, "Minnesota", mn_val] = 1

    v = {}  # v_akt: target number of people with attribute a at table t
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                v[k, a, t] = 5

    # Penalty weights for overuse and underuse
    w1_bar = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w1_bar[k, a, t] = 10

    w2_bar = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w2_bar[k, a, t] = 20

    w1 = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w1[k, a, t] = 10

    w2 = {}
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                w2[k, a, t] = 20

    return {
        "df": work_df,
        "K": K,
        "Ak": Ak,
        "I": I,
        "T": T,
        "R": R,
        "l": l,
        "u": u,
        "lam": lam,
        "b": b,
        "v": v,
        "w1_bar": w1_bar,
        "w2_bar": w2_bar,
        "w1": w1,
        "w2": w2,
    }


def _build_model(params: dict) -> tuple[gp.Model, dict, dict]:
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
    w1_bar = params["w1_bar"]
    w2_bar = params["w2_bar"]
    w1 = params["w1"]
    w2 = params["w2"]

    m = gp.Model("Maass_data")  # Create Gurobi model object
    m.Params.OutputFlag = 0

    # DECISION VARIABLES
    # Y_itr: 1 if person i is at table t in round r
    Y = {}  # Y_itr: Assignment variables
    for i in I:  # Loop through all people
        for t in T:  # Loop through all tables
            for r in R:  # Loop through all rounds
                Y[i, t, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"Y_{i}_{t}_{r}")  # 1 if person i is at table t in round r

    W = {}  # W_tr: Table usage variables
    for t in T:  # Loop through all tables
        for r in R:  # Loop through all rounds
            W[t, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"W_{t}_{r}")  # 1 if table t is used in round r

    E1_bar = {}  # E1_bar_aktr: Binary variable for first overuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E1_bar[k, a, t, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"E1_bar_{k}_{a}_{t}_{r}")  # 1 if attribute a is overused once

    E2_bar = {}  # E2_bar_aktr: Number of additional uses beyond first overuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E2_bar[k, a, t, r] = m.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f"E2_bar_{k}_{a}_{t}_{r}")  # Number of additional overuses

    E1 = {}  # E1_aktr: Binary variable for first underuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E1[k, a, t, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"E1_{k}_{a}_{t}_{r}")  # 1 if attribute a is underused once

    E2 = {}  # E2_aktr: Number of additional under uses beyond first underuse
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    E2[k, a, t, r] = m.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f"E2_{k}_{a}_{t}_{r}")  # Number of additional underuses

    P = {}  # P_ijr: 1 if persons i and j are at same table in round r
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only create for j > i to avoid duplicates
                for r in R:  # Loop through all rounds
                    P[i, j, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"P_{i}_{j}_{r}")  # 1 if i and j meet in round r

    H = {}  # H_ij: 1 if persons i and j have ever been together across all rounds
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only create for j > i to avoid duplicates
                H[i, j] = m.addVar(vtype=gp.GRB.BINARY, name=f"H_{i}_{j}")  # 1 if i and j have ever met

    m.update()  # Update model to integrate new variables

    # CONSTRAINTS
    # Constraint 1: Lower bound on table size if table is used
    for t in T:  # Loop through all tables
        for r in R:  # Loop through all rounds
            m.addConstr(l * W[t, r] <= sum([Y[i, t, r] for i in I]), name=f"lower_bound_t{t}_r{r}")  # Minimum l people if table used

    # Constraint 2: Upper bound on table size
    for t in T:  # Loop through all tables
        for r in R:  # Loop through all rounds
            m.addConstr(sum([Y[i, t, r] for i in I]) <= u * W[t, r], name=f"upper_bound_t{t}_r{r}")  # Maximum u people per table

    # Constraint 3: Each person assigned to exactly one table per round
    for i in I:  # Loop through all people
        for r in R:  # Loop through all rounds
            m.addConstr(sum(Y[i, t, r] for t in T) == 1, name=f"assign_table_{i}_r{r}")  # Each person at exactly one table

    # Constraint 4: Anchor first person for faster solving
    if len(params["df"]) > 0:
        m.addConstr(Y[0, 0, 0] == 1, name="anchor")  # Person 0 at table 0 in round 0 (reduces alternate optimal solutions)

    # Constraint 5: Symmetry breaking for table usage
    for t in range(len(T) - 1):  # Loop through all tables except last
        for r in R:  # Loop through all rounds
            m.addConstr(W[t, r] >= W[t + 1, r], name=f"order_tables_{t}_r{r}")  # Table t must be used before table t+1

    # Constraint 6: Tracks deviations from target attribute levels
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    m.addConstr(
                        sum(b[i, k, a] * Y[i, t, r] for i in I)
                        - E1_bar[k, a, t, r]
                        - E2_bar[k, a, t, r]
                        + E1[k, a, t, r]
                        + E2[k, a, t, r]
                        == v[k, a, t],
                        name=f"deviation_{k}_{a}_{t}_{r}",
                    )  # Actual count +/- deviations = target

    # Constraint 7: First overuse limited to 1
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    m.addConstr(E1_bar[k, a, t, r] <= 1, name=f"E1_bar_limit_{k}_{a}_{t}_{r}")  # Binary constraint on first overuse

    # Constraints 8-11: Non-negativity constraints
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    m.addConstr(E1_bar[k, a, t, r] >= 0, name=f"E1_bar_nonneg_{k}_{a}_t{t}_r{r}")  # E1_bar non-negative
                    m.addConstr(E2_bar[k, a, t, r] >= 0, name=f"E2_bar_nonneg_{k}_{a}_t{t}_r{r}")  # E2_bar non-negative
                    m.addConstr(E1[k, a, t, r] >= 0, name=f"E1_nonneg_{k}_{a}_t{t}_r{r}")  # E1 non-negative
                    m.addConstr(E2[k, a, t, r] >= 0, name=f"E2_nonneg_{k}_{a}_t{t}_r{r}")  # E2 non-negative

    # Code only works when constraints 12 and 13 are commented out in original model.
    # Constraint 12: Hard upper bound on attribute count (left out by design)
    # Constraint 13: Hard lower bound on attribute count (left out by design)

    # Constraint 14: Pair meeting linearization
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only for j > i to avoid duplicates
                for t in T:  # Loop through all tables
                    for r in R:  # Loop through all rounds
                        m.addConstr(P[i, j, r] >= Y[i, t, r] + Y[j, t, r] - 1, name=f"pair_meet_{i}_{j}_{t}_{r}")  # If both at table t, then P = 1

    # Constraint 15: Ever-met indicator across rounds
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only for j > i to avoid duplicates
                for r in R:  # Loop through all rounds
                    m.addConstr(H[i, j] >= P[i, j, r], name=f"ever_met_{i}_{j}_{r}")  # If met in round r, then H = 1

    m.update()  # Update model to integrate all constraints

    # OBJECTIVE
    # Sum deviation penalties for all characteristics, attributes, tables, and rounds
    obj = gp.LinExpr()
    for r in R:  # Loop through all rounds
        for k in K:  # Loop through all characteristics
            for a in Ak[k]:  # Loop through all attributes of characteristic k
                for t in T:  # Loop through all tables
                    obj += w1_bar[k, a, t] * E1_bar[k, a, t, r]  # Add first overuse penalty
                    obj += w2_bar[k, a, t] * E2_bar[k, a, t, r]  # Add additional overuse penalty
                    obj += w1[k, a, t] * E1[k, a, t, r]  # Add first underuse penalty
                    obj += w2[k, a, t] * E2[k, a, t, r]  # Add additional underuse penalty

    # Add penalty for people meeting multiple times across rounds
    for i in I:  # Loop through all people
        for j in I:  # Loop through all people
            if j > i:  # Only for j > i to avoid duplicates
                obj += lam * H[i, j]  # Add penalty for i and j having ever met

    # Set objective to minimize total penalties
    m.setObjective(obj, gp.GRB.MINIMIZE)
    m.update()

    return m, Y, W


def solve_solver_v2(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    params = _prepare_parameters(df)
    model, Y, W = _build_model(params)
    model.optimize()  # Solve the model

    # Extract solution (same pattern as SolverV2 notebook)
    if model.status != gp.GRB.OPTIMAL:
        raise RuntimeError(f"Optimization failed with status {model.status}")

    work_df = params["df"].copy()
    I = params["I"]
    T = params["T"]
    R = params["R"]

    row_assignments = {}
    round_table_rows = []
    for r in R:  # Loop through all rounds
        for t in T:  # Loop through all tables
            if W[t, r].X > 0.5:  # If table t is used in round r
                people_in_t = [i for i in I if Y[i, t, r].X > 0.5]  # Get people assigned to table t in round r
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

    return work_df, schedule_df, float(model.objVal)
