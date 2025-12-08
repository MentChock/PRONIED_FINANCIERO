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
        
    print(f"📊 Total Filas: {len(df)}")
    
    # Check for null units
    null_units = df[df['unidad_gerencial'].isnull()]
    print(f"🚫 Filas con Unidad NULL: {len(null_units)}")
    
    if not null_units.empty:
        total_null = null_units['monto_compro_enero'].sum() + null_units['monto_compro_febrero'].sum()
        print(f"💰 Monto en filas NULL (Feb): {total_null:,.2f}")
        
    # Check for empty strings
    empty_units = df[df['unidad_gerencial'].astype(str).str.strip() == '']
    print(f"🚫 Filas con Unidad Vacia: {len(empty_units)}")
    if not empty_units.empty:
        total_empty = empty_units['monto_compro_enero'].sum() + empty_units['monto_compro_febrero'].sum()
        print(f"💰 Monto en filas Vacias (Feb): {total_empty:,.2f}")

except Exception as e:
    print("ERROR:", e)
