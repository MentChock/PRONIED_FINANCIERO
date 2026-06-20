import pandas as pd
from sqlalchemy import create_engine
engine = create_engine("mssql+pyodbc://sa:Qazokm2015.@127.0.0.1:1433/PRONIED_FINANCIERO?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=no")
with engine.connect() as conn:
    df = pd.read_sql("SELECT * FROM usuarios WHERE username = 'kevi.zapata3'", conn)
if not df.empty:
    user_row = df.iloc[0]
    is_admin = int(user_row.get('administrador', 0))
    print("Administrador from row:", user_row.get('administrador'))
    print("Parsed is_admin:", is_admin)
    print("Type of is_admin:", type(is_admin))
    print("Row data dict:", user_row.to_dict())
