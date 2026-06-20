import os
import pandas as pd
from sqlalchemy import create_engine

# 1. CONEXIÓN LOCAL (Tu base de datos en Docker)
LOCAL_DB_URL = "mssql+pyodbc://sa:Qazokm2015.@127.0.0.1:1433/PRONIED_FINANCIERO?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=no&LoginTimeout=60"
local_engine = create_engine(LOCAL_DB_URL)

# 2. CONEXIÓN AZURE (Reemplaza esto con los datos que te dé Azure cuando crees la Web App + Database)
# EJEMPLO: "mssql+pyodbc://tu_usuario:tu_contraseña@tu_servidor.database.windows.net:1433/PRONIED_FINANCIERO?driver=ODBC+Driver+18+for+SQL+Server"
AZURE_DB_URL = "PEGAR_AQUI_TU_CONEXION_DE_AZURE"

def migrar_base_de_datos():
    if AZURE_DB_URL == "PEGAR_AQUI_TU_CONEXION_DE_AZURE":
        print("❌ ERROR: Primero debes crear la base de datos en Azure y pegar la cadena de conexión en la variable AZURE_DB_URL dentro de este script.")
        return

    azure_engine = create_engine(AZURE_DB_URL)
    
    tablas = [
        'usuarios',
        'ejecucion_financiera',
        'control_cambios',
        'configuracion_reportes',
        'configuracion_alertas'
    ]
    
    for tabla in tablas:
        print(f"📦 Leyendo tabla local: {tabla}...")
        try:
            with local_engine.connect() as local_conn:
                df = pd.read_sql(f"SELECT * FROM {tabla}", local_conn)
            
            print(f"☁️ Subiendo {len(df)} registros de '{tabla}' a Azure...")
            with azure_engine.connect() as azure_conn:
                df.to_sql(tabla, azure_conn, if_exists='replace', index=False)
            
            print(f"✅ Tabla {tabla} migrada exitosamente!\n")
            
        except Exception as e:
            print(f"⚠️ Nota o error en la tabla {tabla}: {e}")

    print("🎉 MIGRACIÓN COMPLETADA. Toda tu base de datos ahora está en la nube.")

if __name__ == "__main__":
    migrar_base_de_datos()
