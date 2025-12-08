from sqlalchemy import create_engine
import pandas as pd

try:
    connection_url = (
        "mssql+pyodbc://sa:Qazokm2015.@localhost:1433/PRONIED_FINANCIERO"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&TrustServerCertificate=yes"
        "&Encrypt=no"
    )
    engine = create_engine(connection_url)
    
    query = "SELECT * FROM ejecucion_financiera WHERE ano_ejecucion = 2025"
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    df['acumulado_feb'] = df['monto_compro_enero'] + df['monto_compro_febrero']
    
    # Buscar filas con ~40M
    print("--- Buscando filas con acumulado ~40M ---")
    matches = df[(df['acumulado_feb'] > 39000000) & (df['acumulado_feb'] < 41000000)]
    if not matches.empty:
        print(matches[['unidad_gerencial', 'acumulado_feb', 'generica', 'programa_presupuestal']])
    else:
        print("No se encontró una fila única de 40M.")
        
    # Buscar grupos que sumen 40M
    print("\n--- Buscando grupos que sumen ~40M ---")
    print(df.groupby('unidad_gerencial')['acumulado_feb'].sum())

except Exception as e:
    print("ERROR:", e)
