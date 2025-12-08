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

def check_global_kpis():
    # Consultar Totales Globales
    # PIM Total
    # Ejecución Real Total (Ene-Nov)
    # Ejecución Real Total (Ene-Dic) - por si acaso
    query = """
    SELECT 
        SUM(monto_pim) as pim_total,
        SUM(monto_devengado_enero + monto_devengado_febrero + monto_devengado_marzo + 
            monto_devengado_abril + monto_devengado_mayo + monto_devengado_junio + 
            monto_devengado_julio + monto_devengado_agosto + monto_devengado_setiembre + 
            monto_devengado_octubre + monto_devengado_noviembre) as ejecucion_ene_nov,
        SUM(monto_devengado_diciembre) as ejecucion_dic
    FROM ejecucion_financiera
    WHERE ano_ejecucion = 2025
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    pim_total = df['pim_total'].iloc[0]
    exec_ene_nov = df['ejecucion_ene_nov'].iloc[0]
    exec_dic = df['ejecucion_dic'].iloc[0]
    
    print("--- DATOS GLOBALES REALES (BD) ---")
    print(f"PIM TOTAL ANUAL: S/ {pim_total:,.2f}")
    print(f"Ejecución Real (Ene-Nov): S/ {exec_ene_nov:,.2f}")
    print(f"Ejecución Real (Dic): S/ {exec_dic:,.2f}")
    print(f"Ejecución Real Total (Ene-Dic): S/ {(exec_ene_nov + exec_dic):,.2f}")
    
    # Nota sobre la proyección
    print("\n--- NOTA SOBRE PROYECCIÓN ---")
    print("La 'Proyección Anual' en el Dashboard es: Ejecución Real (Ene-Oct) + Predicción IA (Nov-Dic)")
    print("Si el mes actual es Noviembre, usa Predicción para Nov y Dic.")

if __name__ == "__main__":
    check_global_kpis()
