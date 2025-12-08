import pandas as pd
from sqlalchemy import create_engine

def create_engine_connection():
    connection_url = (
        "mssql+pyodbc://sa:Qazokm2015.@localhost:1433/PRONIED_FINANCIERO"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&TrustServerCertificate=yes"
        "&Encrypt=no"
    )
    return create_engine(connection_url)

def debug_ranking():
    engine = create_engine_connection()
    query_rank = """
    SELECT unidad_gerencial as unidad, SUM(monto_pim) as pim, SUM(monto_total_devengado_anual) as devengado
    FROM ejecucion_financiera
    GROUP BY unidad_gerencial
    """
    
    with engine.connect() as conn:
        df_rank = pd.read_sql(query_rank, conn)
        
    print("DEBUG RANKING COLS:", df_rank.columns)
    print("DEBUG RANKING HEAD:\n", df_rank.head())
    print("DEBUG RANKING TO DICT:\n", df_rank.to_dict('records'))

if __name__ == "__main__":
    debug_ranking()
