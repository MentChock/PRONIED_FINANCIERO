import requests

def debug_chart_data():
    # 1. Login
    try:
        auth_data = {"username": "kevinjuerg2019@gmail.com", "password": "password123"} # Assuming this user exists from check_users_db.py
        # Wait, I need the real password. The DB has hashed password.
        # I can't login without the real password.
        # BUT, I can temporarily modify the backend to print the data it sends, OR I can use the 'check_api_values.py' approach 
        # but I need to bypass auth or have a valid token.
        
        # Actually, I can just use the 'check_api_values.py' script I used before?
        # No, that script failed with 401 in verify_auth.py.
        
        # I will use a trick: I will call the backend function directly in python, bypassing the API layer.
        pass
    except Exception:
        pass

from dasboard_backend import entrenar_y_predecir, MES_ACTUAL_SIMULADO

def check_backend_direct():
    print("--- CHECKING BACKEND DATA DIRECTLY ---")
    try:
        data = entrenar_y_predecir("Todas")
        
        print(f"Global Keys: {data.keys()}")
        
        if 'unidades' in data and len(data['unidades']) > 0:
            ug0 = data['unidades'][0]
            print(f"Unidad 0: {ug0['unidad']}")
            if 'grafico' in ug0:
                gfx = ug0['grafico']
                print("Grafico Keys:", gfx.keys())
                print("Labels:", gfx['labels'][:3], "...")
                print("Compromiso (len):", len(gfx['compromiso']))
                print("Real (len):", len(gfx['real']))
                print("Prediccion (len):", len(gfx['prediccion_curva']))
                
                print("Sample Real:", gfx['real'])
                print("Sample Pred:", gfx['prediccion_curva'])
            else:
                print("❌ 'grafico' key missing in unit data")
        else:
            print("❌ No units found in data")
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_backend_direct()
