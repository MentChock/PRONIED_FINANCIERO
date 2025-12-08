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
    
    # Analizar TODO 2025
    query = "SELECT * FROM ejecucion_financiera WHERE ano_ejecucion = 2025"
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    print(f"📊 Total Filas 2025: {len(df)}")
    
    # Calcular Acumulado Febrero (Enero + Febrero)
    df['acumulado_feb'] = df['monto_compro_enero'] + df['monto_compro_febrero']
    
    total_sistema = df['acumulado_feb'].sum()
    print(f"💰 Total Acumulado Febrero (Sistema): {total_sistema:,.2f}")
    
    print("\n--- Desglose por UNIDAD GERENCIAL ---")
    print(df.groupby('unidad_gerencial')['acumulado_feb'].sum())
    
    print("\n--- Desglose por GENERICA DE GASTO ---")
    print(df.groupby('generica')['acumulado_feb'].sum())

    print("\n--- Desglose por PROGRAMA PRESUPUESTAL ---")
    print(df.groupby('programa_presupuestal')['acumulado_feb'].sum())

except Exception as e:
    print("ERROR:", e)
