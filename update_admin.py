from sqlalchemy import create_engine, text

DB_CONNECTION_URL = (
    "mssql+pyodbc://sa:Qazokm2015.@127.0.0.1:1433/PRONIED_FINANCIERO"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&TrustServerCertificate=yes"
    "&Encrypt=no"
    "&LoginTimeout=60"
)

engine = create_engine(DB_CONNECTION_URL)

try:
    with engine.begin() as conn:
        conn.execute(text("UPDATE usuarios SET administrador = 1 WHERE username = 'kevi.zapata3';"))
        print("Privilegios de administrador otorgados a kevi.zapata3 exitosamente.")
except Exception as e:
    print("Error:", e)

