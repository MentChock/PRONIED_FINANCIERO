from sqlalchemy import create_engine, text
engine = create_engine('mssql+pyodbc://sa:Qazokm2015.@127.0.0.1:1433/PRONIED_FINANCIERO?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes')
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE usuarios ADD activo INT DEFAULT 1 NOT NULL;"))
        print("Column 'activo' added successfully.")
except Exception as e:
    print("Error:", e)
