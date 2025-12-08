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

def debug_pim():
    query = """
    SELECT *
    FROM ejecucion_financiera
    WHERE ano_ejecucion = 2025 AND monto_pim = 65196272
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    print("--- DETALLE DE LA FILA DE 65M ---")
    # Print as dictionary to see all fields clearly
    if not df.empty:
        row = df.iloc[0]
        for col in df.columns:
            print(f"{col}: {row[col]}")
    else:
        print("No se encontró la fila (¿quizás decimales?). Intentando rango...")

if __name__ == "__main__":
    debug_pim()
