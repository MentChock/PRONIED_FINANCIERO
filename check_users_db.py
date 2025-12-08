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

def check_users_table():
    try:
        # Intentar leer la tabla usuarios
        query = "SELECT TOP 5 * FROM usuarios"
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        print("--- ESTRUCTURA TABLA USUARIOS ---")
        print(df.columns.tolist())
        print(df.head())
    except Exception as e:
        print("Error al leer tabla usuarios:", e)

if __name__ == "__main__":
    check_users_table()
