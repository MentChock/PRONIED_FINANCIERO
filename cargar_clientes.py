import pandas as pd

# Ruta al archivo CSV
ruta_archivo = '/Users/kevizapatafigueroa/Downloads/DD_clientes_dataset.csv'

def cargar_datos():
    try:
        # Cargar el dataset usando pandas
        df_clientes = pd.read_csv(ruta_archivo)
        print("Dataset cargado exitosamente.")
        
        # Mostrar las primeras 5 filas para verificar
        print("\nPrimeras 5 filas del dataset:")
        print(df_clientes.head())
        
        # Mostrar información general del dataset
        print("\nInformación del dataset:")
        df_clientes.info()
        
        return df_clientes
        
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo en la ruta '{ruta_archivo}'.")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado al leer el archivo: {e}")
        return None

if __name__ == "__main__":
    df = cargar_datos()
