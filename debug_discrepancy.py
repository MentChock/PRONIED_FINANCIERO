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
    
    query = "SELECT * FROM ejecucion_financiera WHERE ano_ejecucion = 2025 AND unidad_gerencial LIKE '%UGEO%'"
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    print(f"📊 Filas encontradas para UGEO 2025: {len(df)}")
    
    # Mostrar desglose por Programa Presupuestal (si existe la columna)
    if 'programa_presupuestal' in df.columns:
        print("\n--- Desglose por Programa Presupuestal (Enero + Febrero) ---")
        cols = ['programa_presupuestal', 'monto_compro_enero', 'monto_compro_febrero']
        print(df[cols].groupby('programa_presupuestal').sum())
        
        total_enero = df['monto_compro_enero'].sum()
        total_febrero = df['monto_compro_febrero'].sum()
        print(f"\nTOTAL ENERO (Sistema): {total_enero:,.2f}")
        print(f"TOTAL FEBRERO (Sistema): {total_febrero:,.2f}")
        print(f"ACUMULADO FEBRERO: {total_enero + total_febrero:,.2f}")

except Exception as e:
    print("ERROR:", e)
