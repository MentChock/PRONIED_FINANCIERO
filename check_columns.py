import pandas as pd
from sqlalchemy import create_engine

# Configuración de la base de datos
connection_url = (
    "mssql+pyodbc://sa:Qazokm2015.@localhost:1433/PRONIED_FINANCIERO"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&TrustServerCertificate=yes"
    "&Encrypt=no"
)
engine = create_engine(connection_url)

def check_columns():
    try:
        query = "SELECT TOP 1 * FROM ejecucion_financiera"
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        print("--- COLUMNAS EJECUCION_FINANCIERA ---")
        for col in df.columns:
            print(col)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_columns()
