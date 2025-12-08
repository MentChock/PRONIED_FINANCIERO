import requests
import pandas as pd

def check_api():
    try:
        # 2. Get Dashboard Data
        response = requests.get("http://localhost:8000/api/dashboard")
        
        if response.status_code != 200:
            print("Error API:", response.text)
            return

        data = response.json()
        
        global_kpis = data['global']
        kpi_mes = data['kpi_mes_actual']
        
        print("--- DATOS DEL DASHBOARD (API) ---")
        print(f"PIM Total: S/ {global_kpis['pim_total']:,.2f}")
        print(f"Proyección Cierre: S/ {global_kpis['proyeccion_cierre']:,.2f}")
        
        print("\n--- KPI MES ACTUAL ---")
        print(f"Mes: {kpi_mes['mes_nombre']}")
        print(f"Meta Compromiso: S/ {kpi_mes['meta_compromiso']:,.2f}")
        print(f"Ejecutado Real: S/ {kpi_mes['ejecutado_real']:,.2f}")
        print(f"Predicción Cierre: S/ {kpi_mes['prediccion_cierre']:,.2f}")
        
        print("\n--- COMPARACIÓN CON BD (Valores conocidos) ---")
        print("PIM BD: S/ 939,697,141.00")
        print("Devengado BD (Ene-Nov): S/ 587,735,878.81")
        
        diff_pim = global_kpis['pim_total'] - 939697141.00
        diff_dev = global_kpis['devengado_acumulado'] - 587735878.81
        
        print(f"\nDiferencia PIM: {diff_pim:,.2f}")
        print(f"Diferencia Devengado: {diff_dev:,.2f}")
        
    except Exception as e:
        print("Error al conectar con API:", e)

if __name__ == "__main__":
    check_api()
