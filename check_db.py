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
    query = "SELECT TOP 1 * FROM ejecucion_financiera"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    print("COLUMNS:", df.columns.tolist())
except Exception as e:
    print("ERROR:", e)
