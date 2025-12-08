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
    
    query = "SELECT SUM(monto_compro_noviembre) as total_comp_nov, SUM(monto_devengado_noviembre) as total_dev_nov FROM ejecucion_financiera WHERE ano_ejecucion = 2025"
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    print(f"💰 Total Compromiso Noviembre 2025: {df['total_comp_nov'].iloc[0]}")
    print(f"💰 Total Devengado Noviembre 2025: {df['total_dev_nov'].iloc[0]}")

except Exception as e:
    print("ERROR:", e)
