import gurobipy as gp  # Import Gurobi optimization library
import pandas as pd  # Import pandas for data manipulation
import numpy as np  # Import numpy for numerical operations

# Load the Excel file
df = pd.read_excel('/Users/ethan/Desktop/Capstone research /WorldCafeData_Full_Deidentified.xlsx')  # Read student data from Excel

#SETS
#Characteristics and data from Maass World cafe data eventually will be taken directly from user inputted excel 

K = ['Expertise', 'Lived_Experience', 'Minnesota']  # K: Set of student characteristics eventually will be read from excel

Ak = {
    'Expertise': ['Social_Science', 'Computational_Math', 'Real_World'],  # Attributes for Expertise characteristic
    'Lived_Experience': [],  # Attributes for Lived_Experience (populated from data)
    'Minnesota': []  # Attributes for Minnesota (populated from data)
}  # Ak: Set of attributes of characteristic k ∈ K

if 'Lived_Experience' in df.columns:  # Check if Lived_Experience column exists
    Ak['Lived_Experience'] = df['Lived_Experience'].dropna().unique().tolist()  # Get unique non-null values
if 'Minnesota' in df.columns:  # Check if Minnesota column exists
    Ak['Minnesota'] = df['Minnesota'].dropna().unique().tolist()  # Get unique non-null values

I = range(len(df))  # I: The set of people (30 from the world cafe data)
T = range(6)  # T: The set of tables (6 tables needed)
R = range(3)  # R: The set of rounds (change this number based on how many rounds you want)

#PARAMETERS
l = 4  # l: Minimum table size (lower bound on allowed people per table)

u = 6  # u: Maximum table size (upper bound on allowed people per table)

lam = 50  # λ: Penalty weight for people meeting together multiple times across rounds

b = {}  # b_iak: Binary indicator for whether person i has attribute a of characteristic k
for i in I:  # Loop through all people
    for k in K:  # Loop through all characteristics
        for a in Ak[k]:  # Loop through all attributes of characteristic k
            b[i, k, a] = 0  # Initialize to 0 (person i does not have attribute a)

# Populate b based on Excel dataframe
for idx, row in df.iterrows():  # Loop through each row in dataframe 
    #how will this work in a general excel
    i = idx  # Use dataframe index as person ID
    
    # For Expertise 
    if 'Expertise' in df.columns and pd.notna(row['Expertise']):  # Check if column exists and value is not null
        if row['Expertise'] in Ak['Expertise']:  # Check if value is a valid attribute
            b[i, 'Expertise', row['Expertise']] = 1  # Set indicator to 1
    
    # For Lived_Experience
    if 'Lived_Experience' in df.columns and pd.notna(row['Lived_Experience']):  # Check if column exists and value is not null
        if row['Lived_Experience'] in Ak['Lived_Experience']:  # Check if value is a valid attribute
            b[i, 'Lived_Experience', row['Lived_Experience']] = 1  # Set indicator to 1
    
    # For Minnesota
    if 'Minnesota' in df.columns and pd.notna(row['Minnesota']):  # Check if column exists and value is not null
        if row['Minnesota'] in Ak['Minnesota']:  # Check if value is a valid attribute
            b[i, 'Minnesota', row['Minnesota']] = 1  # Set indicator to 1


v = {}  # v_akt: Target number of people with attribute a for characteristic k at table t
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            v[k, a, t] = 5  # Set target to 5 people (adjust as needed)
#code only works with v and vbar commeted out
#  Upper limit 
#v_bar = {}  # v̄_akt: Maximum allowed number of people with attribute a at table t
#for k in K:
 #   for a in Ak[k]:
  #      for t in T:
   #         v_bar[k, a, t] = 6  # Set maximum allowed

#v_under = {}  # v_akt: Minimum required number of people with attribute a at table t
#for k in K:
  #   for a in Ak[k]:
   #      for t in T:
    #         v_under[k, a, t] = 2  # Set minimum required

# Penalty weights for overuse
w1_bar = {}  # w̄1_akt: Penalty weight for overusing attribute a once at table t
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            w1_bar[k, a, t] = 10  # First penalty for overuse

w2_bar = {}  # w̄2_akt: Penalty weight for additional usages beyond first overuse
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            w2_bar[k, a, t] = 20  # Second penalty for overuse

# Penalty weights for underuse
w1 = {}  # w1_akt: Penalty weight for underusing attribute a once at table t
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            w1[k, a, t] = 10  # First penalty for underuse

w2 = {}  # w2_akt: Penalty weight for additional under usages beyond first underuse
for k in K:  # Loop through all characteristics
    for a in Ak[k]:  # Loop through all attributes of characteristic k
        for t in T:  # Loop through all tables
            w2[k, a, t] = 20  # Second penalty for underuse