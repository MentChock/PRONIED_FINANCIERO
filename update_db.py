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
        conn.execute(text("ALTER TABLE usuarios ADD administrador INT DEFAULT 0 NOT NULL;"))
        print("Column 'administrador' added successfully.")
except Exception as e:
    print("Error (possibly column already exists):", e)

try:
    with engine.begin() as conn:
        # Set the first user as admin, or kevin as admin, etc.
        conn.execute(text("UPDATE usuarios SET administrador = 1 WHERE correo LIKE '%kevin%';"))
        print("Set kevin to admin")
except Exception as e:
    print("Error:", e)

