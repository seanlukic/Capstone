import gurobipy as gp
from data_prep_Min import *
import pandas as pd
import numpy as np
m = gp.Model("Maass_data") 

#DECISION VARIABLES

Y = {}
for i in I:
    for f in F:
        Y[i,f] = m.addVar(vtype=gp.GRB.BINARY, name=f"Y_{i}_{f}") # 1 if student i is in family f 

W = {}
for f in F:
    W[f] = m.addVar(vtype=gp.GRB.BINARY, name=f"W_{f}") # 1 if familiy has more than 0 students

E1_bar = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            E1_bar[k,a,f] = m.addVar(vtype=gp.GRB.BINARY, name=f"E1)bar_{k}_{a}_{f}") #Binary variable for first overuse

E2_bar = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            E2_bar[k,a,f] = m.addVar(vtype=gp.GRB.INTEGER, lb = 0, name = f"E2_bar_{k}_{a}_{f}") #number of aditional uses beyond the first


E1 = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            E1[k,a,f] = m.addVar(vtype=gp.GRB.BINARY,name=f"E1_{k}_{a}_{f}") #Binary Varibale for first underuse

E2 = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            E2[k,a,f] = m.addVar(vtype = gp.GRB.INTEGER, lb=0, name=f"E2_{k}_{a}_{f}") #number of additional under uses 

m.update()

#CONSTRAINTS

for f in F:
    m.addConstr(l * W[f] <= sum([Y[i,f]for i in I]),name=f"lower_bound_f{f}") #Constraint 13

for f in F:
    m.addConstr(sum([Y[i,f]for i in I]) <= u * W[f], name=f"upper_bound_f{f}") #Constraint 14 

for i in I:
    m.addConstr(sum(Y[i,f] for f in F) == 1, name=f"assign_gorup_{i}" ) #Constraint 15

m.addConstr(Y[0,0] == 1, name=f"anchor") #Constraint 16 reduces # of alt optimal solutions by anchoring first person into the first grouping

for f in range(len(F)-1):
    m.addConstr(W[f] >= W[f+1], name=f"order_groupings_{f}") #Constraint 17 

for k in K:
    for a in Ak[k]:
        for f in F:
            m.addConstr(sum(b[i,k,a] * Y[i,f] for i in I) 
            - E1_bar[k,a,f] - E2_bar[k,a,f] + E1[k,a,f] + E2[k,a,f]
            == v[k,a,f], name=f"deviation_{k}_{a}_{f}" ) # constraint 18

for k in K:
    for a in Ak[k]:
        for f in F:
            m.addConstr(E1_bar[k,a,f] <= 1, name=f"E1_bar_limit_{k}_{a}_{f}") #Constraint 19

for k in K:
    for a in Ak[k]:
        for f in F:
            m.addConstr(E1[k,a,f] <= 1, name=f"E1_limit_{k}_{a}_{f}") #Constraint 20

for k in K:
    for a in Ak[k]:
        for f in F:
            m.addConstr(E1_bar[k,a,f] >= 0, name=f"E1_bar_nonneg_{k}_{a}_f{f}")
            m.addConstr(E2_bar[k,a,f] >= 0, name=f"E2_bar_nonneg_{k}_{a}_f{f}")
            m.addConstr(E1[k,a,f] >= 0, name=f"E1_nonneg_{k}_{a}_f{f}")
            m.addConstr(E2[k,a,f] >= 0, name=f"E2_nonneg_{k}_{a}_f{f}")

m.update()

#OBJECTIVE

obj = gp.LinExpr() #create the objective function

#sum for all k in K, a in Ak, and f in F
for k in K:
    for a in Ak[k]:
        for f in F:
            obj += w1_bar[k,a,f] * E1_bar[k,a,f]
            obj += w2_bar[k,a,f] * E2_bar[k,a,f]
            obj += w1[k,a,f] * E1[k,a,f]
            obj += w2[k,a,f] * E2[k,a,f]

m.setObjective(obj, gp.GRB.MINIMIZE)
m.update()
m.write("diversity_model.lp")