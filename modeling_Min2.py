import gurobipy as gp  # Import Gurobi optimization library
from data_prep_Min import *  # Import all parameters and sets from first part
import pandas as pd  # Import pandas for data manipulation
import numpy as np  # Import numpy for numerical operations

m = gp.Model("Maass_data")  # Create Gurobi model object

#DECISION VARIABLES
Y = {}  # Y_itr: Assignment variables
for i in I:  # Loop through all people
    for t in T:  # Loop through all tables
        for r in R:  # Loop through all rounds
            Y[i, t, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"Y_{i}_{t}_{r}")  # 1 if person i is at table t in round r

W = {}  # W_tr: Table usage variables
for t in T:  # Loop through all tables
    for r in R:  # Loop through all rounds
        W[t, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"W_{t}_{r}")  # 1 if table t is used in round r

E1_bar = {}  # Ē1_aktr: Binary variable for first overuse
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            for r in R:  # Loop through all rounds
                E1_bar[k, a, t, r] = m.addVar(vtype=gp.GRB.BINARY, name=f"E1_bar_{k}_{a}_{t}_{r}")  # 1 if attribute a is overused once

E2_bar = {}  # Ē2_aktr: Number of additional uses beyond first overuse
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

#CONSTRAINTS
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
m.addConstr(Y[0, 0, 0] == 1, name=f"anchor")  # Person 0 at table 0 in round 0 (reduces alternate optimal solutions)

# Constraint 5: Symmetry breaking - ensures tables are filled sequentially
for t in range(len(T) - 1):  # Loop through all tables except last
    for r in R:  # Loop through all rounds
        m.addConstr(W[t, r] >= W[t + 1, r], name=f"order_tables_{t}_r{r}")  # Table t must be used before table t+1

# Constraint 6: Tracks deviations from target attribute levels
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            for r in R:  # Loop through all rounds
                m.addConstr(sum(b[i, k, a] * Y[i, t, r] for i in I) 
                           - E1_bar[k, a, t, r] - E2_bar[k, a, t, r] + E1[k, a, t, r] + E2[k, a, t, r]
                           == v[k, a, t], name=f"deviation_{k}_{a}_{t}_{r}")  # Actual count +/- deviations = target

# Constraint 7: First overuse limited to 1
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            for r in R:  # Loop through all rounds
                m.addConstr(E1_bar[k, a, t, r] <= 1, name=f"E1_bar_limit_{k}_{a}_{t}_{r}")  # Binary constraint on first overuse

# Constraints 8-11: Non-negativity constraints (implicitly handled by lb=0 in variable definition)
# Additional explicit constraints for completeness
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            for r in R:  # Loop through all rounds
                m.addConstr(E1_bar[k, a, t, r] >= 0, name=f"E1_bar_nonneg_{k}_{a}_t{t}_r{r}")  # E1_bar non-negative
                m.addConstr(E2_bar[k, a, t, r] >= 0, name=f"E2_bar_nonneg_{k}_{a}_t{t}_r{r}")  # E2_bar non-negative
                m.addConstr(E1[k, a, t, r] >= 0, name=f"E1_nonneg_{k}_{a}_t{t}_r{r}")  # E1 non-negative
                m.addConstr(E2[k, a, t, r] >= 0, name=f"E2_nonneg_{k}_{a}_t{t}_r{r}")  # E2 non-negative

#code only works when 12 and 13 are commeted out
# Constraint 12: Hard upper bound on attribute count
#for k in K:
#         for t in T:
#            for r in R:
 #                m.addConstr(sum(b[i, k, a] * Y[i, t, r] for i in I) <= v_bar[k, a, t], 
 #                           name=f"hard_upper_{k}_{a}_{t}_{r}")  # No more than v_bar people with attribute a

#Constraint 13: Hard lower bound on attribute count 
#for k in K:
 #    for a in Ak[k]:
  #       for t in T:
  #           for r in R:
  #               m.addConstr(sum(b[i, k, a] * Y[i, t, r] for i in I) >= v_under[k, a, t] * W[t, r], 
 #                           name=f"hard_lower_{k}_{a}_{t}_{r}")  # At least v_under people with attribute a if table used

# Constraint 14: P_ijr = 1 if both person i and j are at same table in round r (linearization)
for i in I:  # Loop through all people
    for j in I:  # Loop through all people
        if j > i:  # Only for j > i to avoid duplicates
            for t in T:  # Loop through all tables
                for r in R:  # Loop through all rounds
                    m.addConstr(P[i, j, r] >= Y[i, t, r] + Y[j, t, r] - 1, 
                               name=f"pair_meet_{i}_{j}_{t}_{r}")  # If both at table t, then P = 1

# Constraint 15: H_ij = 1 if persons i and j have ever been together in any round
for i in I:  # Loop through all people
    for j in I:  # Loop through all people
        if j > i:  # Only for j > i to avoid duplicates
            for r in R:  # Loop through all rounds
                m.addConstr(H[i, j] >= P[i, j, r], name=f"ever_met_{i}_{j}_{r}")  # If met in round r, then H = 1

m.update()  # Update model to integrate all constraints

#OBJECTIVE
obj = gp.LinExpr()  # Create the objective function expression

# Sum deviation penalties for all characteristics, attributes, tables, and rounds
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

m.setObjective(obj, gp.GRB.MINIMIZE)  # Set objective to minimize total penalties
m.update()  # Update model with objective function
m.write("diversity_model.lp")  # Write model to file for inspection