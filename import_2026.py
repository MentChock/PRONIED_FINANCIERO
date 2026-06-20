import pandas as pd
from sqlalchemy import create_engine
import sys
import time

def importar_datos():
    file_path = 'PROYECTO.xlsx'
    
    print(f"Cargando archivo: {file_path}")
    try:
        df = pd.read_excel(file_path)
        print(f"Archivo cargado correctamente. Filas: {len(df)}")
    except Exception as e:
        print(f"Error al leer el archivo Excel: {e}")
        sys.exit(1)

    # Eliminar columna id si existe para que SQL Server la autogenere (asumiendo que es IDENTITY)
    if 'id' in df.columns:
        df = df.drop(columns=['id'])

    print("Conectando a la base de datos...")
    # Cadena de conexión obtenida de tu código
    db_url = (
        "mssql+pyodbc://sa:Qazokm2015.@127.0.0.1:1433/PRONIED_FINANCIERO"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&TrustServerCertificate=yes"
        "&Encrypt=no"
    )
    
    try:
        engine = create_engine(db_url)
        # Probamos conexión
        with engine.connect() as conn:
            print("Conexión exitosa a PRONIED_FINANCIERO.")
    except Exception as e:
        print(f"Error de conexión a la BD: {e}")
        sys.exit(1)

    print("Insertando datos en 'ejecucion_financiera' (esto puede tardar unos minutos)...")
    start_time = time.time()
    
    try:
        # Insertar datos en bloques para no saturar memoria
        df.to_sql('ejecucion_financiera', con=engine, if_exists='append', index=False, chunksize=1000)
        elapsed_time = time.time() - start_time
        print(f"✅ ¡Datos insertados correctamente en {elapsed_time:.2f} segundos!")
        print(f"Total de registros nuevos agregados: {len(df)}")
    except Exception as e:
        print(f"❌ Error al insertar datos en la base de datos: {e}")

if __name__ == '__main__':
    importar_datos()
