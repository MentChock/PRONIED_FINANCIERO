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

def check_risk_data():
    # Consultar PIM y Ejecución Real (Ene-Nov) por Unidad
    query = """
    SELECT 
        unidad_gerencial,
        SUM(monto_pim) as pim_total,
        SUM(monto_devengado_enero + monto_devengado_febrero + monto_devengado_marzo + 
            monto_devengado_abril + monto_devengado_mayo + monto_devengado_junio + 
            monto_devengado_julio + monto_devengado_agosto + monto_devengado_setiembre + 
            monto_devengado_octubre + monto_devengado_noviembre) as ejecucion_ene_nov
    FROM ejecucion_financiera
    WHERE ano_ejecucion = 2025
    GROUP BY unidad_gerencial
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    print("--- DATOS REALES (BD) ---")
    for index, row in df.iterrows():
        unit = row['unidad_gerencial'].strip()
        pim = row['pim_total']
        exec_real = row['ejecucion_ene_nov']
        avance_real = (exec_real / pim * 100) if pim > 0 else 0
        
        print(f"Unidad: {unit}")
        print(f"  PIM: S/ {pim:,.2f}")
        print(f"  Ejecución (Ene-Nov): S/ {exec_real:,.2f}")
        print(f"  Avance Real (a Nov): {avance_real:.2f}%")
        print("-" * 30)

if __name__ == "__main__":
    check_risk_data()
