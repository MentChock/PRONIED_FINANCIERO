from sqlalchemy import create_engine
import pandas as pd
import numpy as np

try:
    connection_url = (
        "mssql+pyodbc://sa:Qazokm2015.@localhost:1433/PRONIED_FINANCIERO"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&TrustServerCertificate=yes"
        "&Encrypt=no"
    )
    engine = create_engine(connection_url)
    
    query = "SELECT TOP 100 * FROM ejecucion_financiera WHERE ano_ejecucion = 2025"
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    print("--- DTYPES ---")
    print(df.dtypes)
    
    # Check if monto columns are numeric
    monto_cols = [c for c in df.columns if 'monto_' in c]
    print("\n--- MONTO COLUMNS ---")
    print(df[monto_cols].dtypes)

except Exception as e:
    print("ERROR:", e)
