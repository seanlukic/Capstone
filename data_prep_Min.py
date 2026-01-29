import gurobipy as gp
import pandas as pd
import numpy as np

# Excel path file location
excel_path = 'C:\\Users\\seanl\\Fall 2025\\Capstone\\Code\\WorldCafeData-Full_Deidentified.xlsx'

# Load the 1st 2 rows as a header
df = pd.read_excel(excel_path, header=[0,1])

# print(df.columns)

# df.columns = [
#     "Person_ID",
    
# ]
#SETS
#Characteristics and data from Maass World cafe data

K = ['Expertise', 'Lived_Experience', 'Minnesota'] #K : Set of student characteristics.

Ak = {
    'Expertise' : ['Social_Science','Computational_Math', 'Real_World'],
    'Lived_Experience': [],
    'Minnesota': []
} #Ak : Set of attributes of characteristic k ∈ K.

if 'Lived_Experience' in df.columns:
    Ak['Lived_Experience'] = df['Lived_Experience'].dropna().unique().tolist()
if 'Minnesota' in df.columns:
    Ak['Minnesota'] = df['Minnesota'].dropna().unique().tolist()

I = range(len(df)) #The 30 people from the world cafe data
F = range (6) #The 6 groups we need without adding the tabel function 

#PARAMETERS
l = 4 # lowerbound on allowed stduents in group

u = 6 #upperbound on allowed students in group 

b = {}
for i in I:
    for k in K:
        for a in Ak[k]:
            b[i,k,a] = 0 #b_iak : set 1 if student i has attribute a of chracteristic k, otherwise 0

# Populate b based on Excel dataframe
for idx, row in df.iterrows():
    i = idx  # Use dataframe index as student ID
    
    # For Expertise (replace 'Expertise' with actual column name)
    if 'Expertise' in df.columns and pd.notna(row['Expertise']):
        if row['Expertise'] in Ak['Expertise']:
            b[i, 'Expertise', row['Expertise']] = 1
    
    # For Lived_Experience (replace with actual column name)
    if 'Lived_Experience' in df.columns and pd.notna(row['Lived_Experience']):
        if row['Lived_Experience'] in Ak['Lived_Experience']:
            b[i, 'Lived_Experience', row['Lived_Experience']] = 1
    
    # For Minnesota (replace with actual column name)
    if 'Minnesota' in df.columns and pd.notna(row['Minnesota']):
        if row['Minnesota'] in Ak['Minnesota']:
            b[i, 'Minnesota', row['Minnesota']] = 1

v = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            v[k,a,f] = 5 # Target number of people with atrribute a for characteristic k in each group

#penalty weights for overuse
w1_bar = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            w1_bar[k,a,f] = 10 #first pentaly for overuse 

w2_bar = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            w2_bar[k,a,f] = 20 #second pentaly for overuse 

#penalty weights for underuse
w1 = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            w1[k,a,f] = 10 #first pentaly for overuse 

w2 = {}
for k in K:
    for a in Ak[k]:
        for f in F:
            w2[k,a,f] = 20 #second pentaly for overuse 

