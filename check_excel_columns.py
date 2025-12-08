import pandas as pd

file_path = "DATASET PRESUPUESTO_V6.xlsx"

try:
    df = pd.read_excel(file_path, nrows=0) # Read only header
    print("--- COLUMNAS EXCEL ---")
    for col in df.columns:
        print(col)
except Exception as e:
    print("Error:", e)
