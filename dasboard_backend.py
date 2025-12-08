import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import calendar
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# --- CONFIGURACIÓN DE SEGURIDAD ---
SECRET_KEY = "pronied_secret_key_2025" # En producción usar variable de entorno
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE DATOS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    full_name: str | None = None

# --- FUNCIONES DE SEGURIDAD ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

# --- RUTAS PRINCIPALES ---
@app.get("/")
async def read_login():
    return FileResponse('login.html')

@app.get("/reporte")
async def reporte_view():
    return FileResponse('reporte_general.html')

@app.get("/analisis-historico")
async def analisis_historico_view():
    return FileResponse('analisis_historico.html')

@app.get("/reporte-ejecutivo")
async def reporte_ejecutivo_view():
    return FileResponse('reporte_ejecutivo.html')

@app.get("/importacion")
async def importacion_view():
    return FileResponse('importacion.html')

@app.get("/dashboard_view")
async def read_dashboard():
    return FileResponse('dasboard_frontend.html')

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Conectar a BD para verificar usuario
    engine = create_engine_connection()
    query = f"SELECT * FROM usuarios WHERE username = '{form_data.username}'"
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_row = df.iloc[0]
    hashed_password_from_db = user_row['hashed_password']
    
    if not verify_password(form_data.password, hashed_password_from_db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_row['username']}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}

from sqlalchemy import create_engine, text

# --- 1. CONFIGURACIÓN Y CONEXIÓN A BASE DE DATOS ---
# Simulamos que hoy es el mes actual del sistema
MES_ACTUAL_SIMULADO = datetime.now().month
MESES_SUFIJOS = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 
                 'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

# Global Database Configuration & Engine (Singleton)
DB_CONNECTION_URL = (
    "mssql+pyodbc://sa:Qazokm2015.@127.0.0.1:1433/PRONIED_FINANCIERO"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&TrustServerCertificate=yes"
    "&Encrypt=no"
    "&LoginTimeout=60"
)

# Initialize Singleton Engine with Connection Pooling
engine = create_engine(
    DB_CONNECTION_URL, 
    pool_pre_ping=True, 
    pool_size=10, 
    max_overflow=20
)

def create_engine_connection():
    """Returns the singleton engine instance."""
    return engine

def setup_database_triggers():
    """Configura la tabla de control de cambios y triggers en la BD."""
    try:
        with engine.connect() as conn:
            # 1. Crear tabla de control si no existe
            conn.execute(text("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='control_cambios' AND xtype='U')
                CREATE TABLE control_cambios (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    tabla_nombre VARCHAR(50),
                    ultima_actualizacion DATETIME
                )
            """))
            conn.commit()

            # 2. Insertar registro inicial para 'ejecucion_financiera' si no existe
            conn.execute(text("""
                IF NOT EXISTS (SELECT * FROM control_cambios WHERE tabla_nombre = 'ejecucion_financiera')
                INSERT INTO control_cambios (tabla_nombre, ultima_actualizacion) 
                VALUES ('ejecucion_financiera', GETDATE())
            """))
            conn.commit()

            # 3. Crear o actualizar Trigger
            # Nota: En SQL Server, para "CREATE OR ALTER" se requiere compatibilidad reciente, 
            # usaremos DROP y CREATE para asegurar compatibilidad.
            conn.execute(text("""
                IF OBJECT_ID('trg_update_last_change', 'TR') IS NOT NULL
                    DROP TRIGGER trg_update_last_change
            """))
            conn.commit()

            conn.execute(text("""
                CREATE TRIGGER trg_update_last_change
                ON ejecucion_financiera
                AFTER INSERT, UPDATE, DELETE
                AS
                BEGIN
                    UPDATE control_cambios
                    SET ultima_actualizacion = GETDATE()
                    WHERE tabla_nombre = 'ejecucion_financiera';
                END
            """))
            conn.commit()
            
            print("✅ Triggers y tabla 'control_cambios' configurados correctamente.")
    except Exception as e:
        print(f"⚠️ Alerta: No se pudieron configurar los triggers automáticos: {e}")

@app.on_event("startup")
async def startup_event():
    setup_database_triggers()

@app.get("/api/last-update")
async def get_last_update():
    """Devuelve la fecha de última actualización de la tabla principal."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT ultima_actualizacion FROM control_cambios WHERE tabla_nombre = 'ejecucion_financiera'"
            )).fetchone()
            
            if result and result[0]:
                # Formato DD/MM/YYYY - HH:MM:SS
                # Ajuste de zona horaria: El servidor DB parece estar en UTC (5 horas adelante de Perú)
                dt = result[0] - timedelta(hours=5)
                formatted_date = dt.strftime("%d/%m/%Y - %H:%M:%S")
                return {"last_updated": f"Última act: {formatted_date}", "timestamp": dt.isoformat()}
                
        # Fallback si no hay registro
        now_peru = datetime.now() - timedelta(hours=5) # Ajuste preventivo por si el host también está en UTC
        return {"last_updated": f"Última act: {now_peru.strftime('%d/%m/%Y - %H:%M:%S')}"}
    except Exception as e:
        print(f"Error obteniendo última actualización: {e}")
        return {"last_updated": datetime.now().strftime("%d/%m/%Y - %H:%M:%S")}


def obtener_datos_bd(agrupar=True):
    """
    Conecta a la base de datos SQL Server y descarga la tabla 'ejecucion_financiera'.
    Si agrupar=True, devuelve datos agrupados por Unidad y Año.
    Si agrupar=False, devuelve datos crudos (con todas las columnas).
    """
    try:
        engine = create_engine_connection()
        
        query = "SELECT * FROM ejecucion_financiera"
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            
        print("✅ Conexión exitosa a la base de datos PRONIED_FINANCIERO")
        
        # --- TRANSFORMACIÓN DE COLUMNAS (DB -> APP) ---
        # La BD tiene 'ano_ejecucion', 'monto_pim', 'monto_compro_enero'...
        # La App espera 'ano_de_ejecución', 'MONTO_PIM', 'MONTO_COMPRO_ENERO'...
        
        # 1. Renombrar columnas base
        df = df.rename(columns={
            'ano_ejecucion': 'ano_de_ejecución',
            'monto_pim': 'MONTO_PIM',
            'monto_compro_anual': 'MONTO_COMPRO_ANUAL'
        })
        
        # 2. Renombrar columnas mensuales
        meses_map = {
            'enero': 'ENERO', 'febrero': 'FEBRERO', 'marzo': 'MARZO', 
            'abril': 'ABRIL', 'mayo': 'MAYO', 'junio': 'JUNIO',
            'julio': 'JULIO', 'agosto': 'AGOSTO', 'setiembre': 'SETIEMBRE',
            'octubre': 'OCTUBRE', 'noviembre': 'NOVIEMBRE', 'diciembre': 'DICIEMBRE'
        }
        
        new_cols = {}
        for col in df.columns:
            # Ejemplo: monto_compro_enero -> MONTO_COMPRO_ENERO
            if col.startswith('monto_'):
                parts = col.split('_')
                suffix = parts[-1] # enero, febrero...
                if suffix in meses_map:
                    prefix = "_".join(parts[:-1]).upper() # MONTO_COMPRO
                    new_name = f"{prefix}_{meses_map[suffix]}"
                    new_cols[col] = new_name
        
        df = df.rename(columns=new_cols)
        
        # --- LIMPIEZA DE DATOS ---
        # Asegurar que el año sea numérico
        df['ano_de_ejecución'] = pd.to_numeric(df['ano_de_ejecución'], errors='coerce')
        
        # Quitar espacios en blanco de la unidad gerencial
        if 'unidad_gerencial' in df.columns:
            df['unidad_gerencial'] = df['unidad_gerencial'].astype(str).str.strip()
            
        # Llenar NaNs con 0 para evitar problemas de cálculo
        df = df.fillna(0)
            
        print(f"📊 Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
        
        if not agrupar:
            return df
            
        print(f"📅 Años en BD: {df['ano_de_ejecución'].unique()}")
        print(f"🏢 Unidades en BD: {df['unidad_gerencial'].unique()}")
        
        
        # --- AGREGACIÓN DE DATOS ---
        # La BD tiene múltiples filas por unidad (por proyecto/meta).
        # Debemos agrupar por Unidad y Año para tener una sola fila resumen por unidad.
        
        # Identificar columnas numéricas para sumar
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Asegurar que las columnas de agrupación no estén en la lista de suma (si fueran numéricas)
        if 'ano_de_ejecución' in numeric_cols: numeric_cols.remove('ano_de_ejecución')
        
        # Agrupar y sumar
        df_grouped = df.groupby(['unidad_gerencial', 'ano_de_ejecución'])[numeric_cols].sum().reset_index()
        
        print(f"📊 Datos Agrupados: {df_grouped.shape[0]} filas (Resumen por Unidad/Año)")
        return df_grouped
        
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        print("⚠️ Usando datos sintéticos de respaldo...")
        return generar_datos_sinteticos_backup()

def generar_datos_sinteticos_backup():
    """
    Respaldo: Simula la tabla 'ejecucion_financiera' si falla la BD.
    """
    unidades = ["UG Educativa Lima", "UG Salud Norte", "UG Infraestructura Sur", "UG Mantenimiento Central"]
    anios = [2022, 2023, 2024, 2025]
    data = []
    
    for anio in anios:
        for ug in unidades:
            # PIM aleatorio entre 5M y 15M
            pim = np.random.randint(5000000, 15000000)
            
            row = {
                "unidad_gerencial": ug,
                "programa_presupuestal": "MEJORAMIENTO INFRAESTRUCTURA",
                "ano_de_ejecución": anio,
                "MONTO_PIM": pim,
                # Compromiso suele ser entre 90% y 99% del PIM
                "MONTO_COMPRO_ANUAL": pim * np.random.uniform(0.90, 0.99),
            }
            
            # Generar columnas mensuales
            for i, mes in enumerate(MESES_SUFIJOS):
                mes_num = i + 1
                
                # Distribución del compromiso (meta)
                compro_mes = (row["MONTO_COMPRO_ANUAL"] / 12) * np.random.uniform(0.8, 1.2)
                row[f"MONTO_CERTIFICADO_{mes}"] = pim / 12
                row[f"MONTO_COMPRO_{mes}"] = compro_mes
                
                # Generar Devengado (Gasto Real)
                if anio < 2025:
                    # Años pasados: Dato histórico completo
                    dev_mes = compro_mes * np.random.uniform(0.90, 1.0) 
                elif anio == 2025:
                    if mes_num < MES_ACTUAL_SIMULADO: 
                        # Ene - Jul (Cerrados): Dato real histórico
                        dev_mes = compro_mes * np.random.uniform(0.85, 0.98)
                    elif mes_num == MES_ACTUAL_SIMULADO: 
                        # Agosto (En curso): Dato parcial (ej. día 15)
                        dev_mes = compro_mes * np.random.uniform(0.3, 0.5) 
                    else: 
                        # Set - Dic (Futuro): Aún no existe devengado
                        dev_mes = 0 
                
                row[f"MONTO_DEVENGADO_{mes}"] = dev_mes

            data.append(row)
            
    return pd.DataFrame(data)

# Cargar datos al iniciar
df_global = obtener_datos_bd()

# --- 2. LÓGICA DE MACHINE LEARNING (Random Forest) ---

def entrenar_y_predecir(unidad_filtro=None):
    df = df_global.copy()
    
    # Filtro por Unidad Gerencial
    if unidad_filtro and unidad_filtro != "Todas":
        df = df[df["unidad_gerencial"] == unidad_filtro]

    # --- Preprocesamiento: Transformar a formato para ML ---
    ml_data = []
    for index, row in df.iterrows():
        for i, mes in enumerate(MESES_SUFIJOS):
            mes_num = i + 1
            
            # REGLA ML: Entrenar SOLO con meses cerrados.
            # No entrenamos con Agosto 2025 porque es parcial y ensuciaría el modelo.
            es_mes_cerrado = (row['ano_de_ejecución'] < 2025) or (row['ano_de_ejecución'] == 2025 and mes_num < MES_ACTUAL_SIMULADO)
            
            if es_mes_cerrado:
                ml_data.append({
                    'anio': row['ano_de_ejecución'],
                    'mes': mes_num,
                    'pim_total': row['MONTO_PIM'],
                    'compromiso_mes': row[f'MONTO_COMPRO_{mes}'],
                    'devengado_mes': row[f'MONTO_DEVENGADO_{mes}'], # Target
                    'unidad': row['unidad_gerencial']
                })
            
    train_df = pd.DataFrame(ml_data)
    
    # Entrenar Modelo
    features = ['mes', 'pim_total', 'compromiso_mes']
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(train_df[features], train_df['devengado_mes'])
    
    # --- 3. GENERAR RESULTADOS Y PREDICCIONES 2025 ---
    df_2025 = df[df['ano_de_ejecución'] == 2025]
    unidades_unicas = df_2025['unidad_gerencial'].unique()
    
    # Estructura de respuesta Global
    resumen_total = {
        "pim_total": 0, "proyeccion_cierre": 0, "saldo_presupuestal": 0, "devengado_acumulado": 0
    }
    
    # KPI Específico del Mes Actual (Agosto)
    kpi_mes_actual = {
        "mes_nombre": MESES_SUFIJOS[MES_ACTUAL_SIMULADO - 1], # "AGOSTO"
        "meta_compromiso": 0,
        "ejecutado_real": 0,
        "prediccion_cierre": 0
    }

    detalle_unidades = []

    for ug in unidades_unicas:
        row_ug = df_2025[df_2025['unidad_gerencial'] == ug].iloc[0]
        
        data_compromiso = []
        data_devengado_real = [] # Para gráfico (tendrá nulls en futuro)
        data_devengado_pred = [] # Para gráfico (curva completa)
        
        proyeccion_anual_ug = 0
        devengado_acumulado_ug = 0 

        for i, mes_nom in enumerate(MESES_SUFIJOS):
            mes_num = i + 1
            compro = row_ug[f'MONTO_COMPRO_{mes_nom}']
            real = row_ug[f'MONTO_DEVENGADO_{mes_nom}']
            
            data_compromiso.append(compro)
            
            # Predecir con el modelo entrenado
            X_input = pd.DataFrame([[mes_num, row_ug['MONTO_PIM'], compro]], columns=features)
            pred_raw = rf_model.predict(X_input)[0]
            
            # REGLA DE NEGOCIO: Predicción no puede ser mayor al compromiso
            pred_ajustada = min(pred_raw, compro) 

            # Lógica Temporal
            if mes_num < MES_ACTUAL_SIMULADO:
                # PASADO: El dato real manda
                data_devengado_real.append(float(real))
                data_devengado_pred.append(float(real)) # En pasado, la predicción es la realidad
                proyeccion_anual_ug += real
                devengado_acumulado_ug += real
                
            elif mes_num == MES_ACTUAL_SIMULADO:
                # MES ACTUAL (Noviembre):
                # Real = Lo gastado hasta hoy
                # Predicción = Lo que la IA dice que gastaremos a fin de mes
                data_devengado_real.append(float(real)) 
                data_devengado_pred.append(float(pred_ajustada)) 
                
                # CORRECCIÓN: Para la proyección anual, usamos el MAYOR entre Real y Predicción.
                # Si ya gastamos más de lo que la IA predijo, usamos lo real.
                proyeccion_anual_ug += max(real, pred_ajustada)
                
                # Sumar al KPI Global del Mes
                kpi_mes_actual["meta_compromiso"] += compro
                kpi_mes_actual["ejecutado_real"] += real
                kpi_mes_actual["prediccion_cierre"] += pred_ajustada
                
            else:
                # FUTURO: Solo existe la IA
                data_devengado_real.append(None) # No dibujar línea real
                data_devengado_pred.append(float(pred_ajustada))
                proyeccion_anual_ug += pred_ajustada

        # Calcular KPIs por Unidad
        pim_ug = row_ug['MONTO_PIM']
        saldo = pim_ug - proyeccion_anual_ug # Lo que va a sobrar
        avance_pct = (proyeccion_anual_ug / pim_ug) * 100
        
        # Semáforo de Riesgo
        riesgo = "BAJO"
        color = "green"
        if avance_pct < 85: riesgo, color = "ALTO", "red"
        elif avance_pct < 95: riesgo, color = "MEDIO", "yellow"

        # Acumular Totales
        resumen_total["pim_total"] += pim_ug
        resumen_total["proyeccion_cierre"] += proyeccion_anual_ug
        resumen_total["saldo_presupuestal"] += saldo
        resumen_total["devengado_acumulado"] += devengado_acumulado_ug

        detalle_unidades.append({
            "unidad": ug,
            "riesgo": riesgo,
            "color": color,
            "pim": float(pim_ug),
            "proyeccion_cierre": float(proyeccion_anual_ug),
            "grafico": {
                "labels": MESES_SUFIJOS,
                "compromiso": [float(x) for x in data_compromiso],
                "real": data_devengado_real,
                "prediccion_curva": data_devengado_pred
            }
        })

    # Final conversion for global objects
    for k in resumen_total:
        resumen_total[k] = float(resumen_total[k])
        
    kpi_mes_actual["meta_compromiso"] = float(kpi_mes_actual["meta_compromiso"])
    kpi_mes_actual["ejecutado_real"] = float(kpi_mes_actual["ejecutado_real"])
    kpi_mes_actual["prediccion_cierre"] = float(kpi_mes_actual["prediccion_cierre"])

    return {
        "global": resumen_total,
        "kpi_mes_actual": kpi_mes_actual,
        "unidades": detalle_unidades,
        "mes_actual_index": MES_ACTUAL_SIMULADO - 1 # 0-based index for frontend
    }

# --- 4. ENDPOINTS API ---

@app.get("/api/dashboard")
def get_dashboard_data(unidad: str = "Todas", current_user: str = Depends(get_current_user)):
    try:
        data = entrenar_y_predecir(unidad)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 5. ENDPOINTS IMPORTACIÓN ---
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import io

# Columnas exactas del Excel "DATASET PRESUPUESTO_V6"
TEMPLATE_COLUMNS = [
    "UNIDAD_GERENCIAL", "ANO_EJECUCION", "sector", "pliego", "u_ejecutora", "sec_ejec", 
    "programa_presupuestal", "tipo_prod_proy", "producto_proyecto", "tipo_act_obra_ac", 
    "activ_obra_accinv", "funcion", "division_fn", "grupo_fn", "meta", "finalidad", 
    "unidad_medida", "cant_meta_anual", "cant_meta_sem", "avan_fisico_anual", 
    "avan_fisico_sem", "sec_func", "departamento_meta", "provincia_meta", "distrito_meta", 
    "fuente_financ", "rubro", "categoria_gasto", "tipo_transaccion", "generica", 
    "subgenerica", "subgenerica_det", "especifica", "especifica_det", "tipo_recurso", 
    "MONTO_PIA", "mto_modificaciones", "MONTO_PIM", "MONTO_CERTIFICADO", 
    "MONTO_COMPRO_ANUAL", "MONTO_COMPRO_ENERO", "MONTO_COMPRO_FEBRERO", "MONTO_COMPRO_MARZO", 
    "MONTO_COMPRO_ABRIL", "MONTO_COMPRO_MAYO", "MONTO_COMPRO_JUNIO", "MONTO_COMPRO_JULIO", 
    "MONTO_COMPRO_AGOSTO", "MONTO_COMPRO_SETIEMBRE", "MONTO_COMPRO_OCTUBRE", 
    "MONTO_COMPRO_NOVIEMBRE", "MONTO_COMPRO_DICIEMBRE", "MONTO_DEVENGADO_ENERO", 
    "MONTO_DEVENGADO_FEBRERO", "MONTO_DEVENGADO_MARZO", "MONTO_DEVENGADO_ABRIL", 
    "MONTO_DEVENGADO_MAYO", "MONTO_DEVENGADO_JUNIO", "MONTO_DEVENGADO_JULIO", 
    "MONTO_DEVENGADO_AGOSTO", "MONTO_DEVENGADO_SETIEMBRE", "MONTO_DEVENGADO_OCTUBRE", 
    "MONTO_DEVENGADO_NOVIEMBRE", "MONTO_DEVENGADO_DICIEMBRE", "MONTO_TOTAL_DEVENGADO_ANUAL", 
    "mto_girado_01", "mto_girado_02", "mto_girado_03", "mto_girado_04", "mto_girado_05", 
    "mto_girado_06", "mto_girado_07", "mto_girado_08", "mto_girado_09", "mto_girado_10", 
    "mto_girado_11", "mto_girado_12", "mto_pagado_01", "mto_pagado_02", "mto_pagado_03", 
    "mto_pagado_04", "mto_pagado_05", "mto_pagado_06", "mto_pagado_07", "mto_pagado_08", 
    "mto_pagado_09", "mto_pagado_10", "mto_pagado_11", "mto_pagado_12"
]

@app.get("/api/template")
def get_template(current_user: str = Depends(get_current_user)):
    try:
        # Crear DataFrame vacío con las columnas exactas
        df = pd.DataFrame(columns=TEMPLATE_COLUMNS)
        
        # Crear Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Plantilla')
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=plantilla_pronied.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando plantilla: {str(e)}")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Use Excel o CSV.")
            
        # Validar columnas contra la plantilla oficial
        uploaded_cols = df.columns.tolist()
        
        # Verificar si faltan columnas
        missing_cols = [c for c in TEMPLATE_COLUMNS if c not in uploaded_cols]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"Faltan columnas requeridas: {', '.join(missing_cols)}")
            
        # Verificar si sobran columnas
        extra_cols = [c for c in uploaded_cols if c not in TEMPLATE_COLUMNS]
        if extra_cols:
            raise HTTPException(status_code=400, detail=f"Columnas no permitidas: {', '.join(extra_cols)}")
            
        # Normalizar nombres de columnas a minúsculas para coincidir con BD
        df.columns = df.columns.str.lower()
        
        # Insertar en BD
        engine = create_engine_connection()
        
        # Usamos 'append' para agregar datos. 
        rows = df.to_sql('ejecucion_financiera', engine, if_exists='append', index=False)
        
        return {"message": "Archivo procesado correctamente", "rows_processed": len(df)}
        
    except Exception as e:
        print(f"Error upload: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")

# --- 6. ENDPOINTS REPORTE EJECUTIVO ---
from pydantic import BaseModel

class ReporteFilter(BaseModel):
    ano: str
    unidad: str
    mes: str

@app.post("/api/reporte-ejecutivo/resumen")
def get_reporte_resumen(filters: ReporteFilter, current_user: str = Depends(get_current_user)):
    try:
        engine = create_engine_connection()
        query = "SELECT * FROM ejecucion_financiera WHERE 1=1"
        params = []
        
        if filters.ano != "Todos":
            query += " AND ano_ejecucion = ?"
            params.append(filters.ano)
            
        if filters.unidad != "Todas":
            query += " AND unidad_gerencial = ?"
            params.append(filters.unidad)
            
        # Ejecutar query base
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params=tuple(params))
            
        # Calcular métricas
        total_registros = len(df)
        total_pim = df['monto_pim'].sum() if 'monto_pim' in df.columns else 0
        
        # Calcular devengado según mes seleccionado
        if filters.mes == "Todos":
            total_devengado = df['monto_total_devengado_anual'].sum() if 'monto_total_devengado_anual' in df.columns else 0
        else:
            col_mes = f"monto_devengado_{filters.mes.lower()}"
            if col_mes in df.columns:
                total_devengado = df[col_mes].sum()
            else:
                total_devengado = 0
                
        return {
            "total_registros": int(total_registros),
            "total_pim": float(total_pim),
            "total_devengado": float(total_devengado)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte-ejecutivo/download")
def download_reporte_excel(
    ano: str, unidad: str, mes: str, 
    current_user: str = Depends(get_current_user)
):
    try:
        engine = create_engine_connection()
        query = "SELECT * FROM ejecucion_financiera WHERE 1=1"
        params = []
        
        if ano != "Todos":
            query += " AND ano_ejecucion = ?"
            params.append(ano)
            
        if unidad != "Todas":
            query += " AND unidad_gerencial = ?"
            params.append(unidad)
            
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params=tuple(params))
            
        # Crear Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # --- HOJA 1: RESUMEN EJECUTIVO ---
            # 1. Resumen Global (Fila 0)
            total_pim = df['monto_pim'].sum() if 'monto_pim' in df.columns else 0
            if mes == "Todos":
                total_devengado = df['monto_total_devengado_anual'].sum() if 'monto_total_devengado_anual' in df.columns else 0
            else:
                col_mes = f"monto_devengado_{mes.lower()}"
                total_devengado = df[col_mes].sum() if col_mes in df.columns else 0
                
            summary_data = {
                'Concepto': ['Total de Proyectos', 'Costo Total (PIM)', 'Devengado Total', 'Saldo por Ejecutar', '% Avance Global'],
                'Valor': [
                    len(df),
                    total_pim,
                    total_devengado,
                    total_pim - total_devengado,
                    (total_devengado / total_pim * 100) if total_pim > 0 else 0
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Resumen Ejecutivo', startrow=0, index=False)
            
            # Obtener worksheet para escribir títulos
            worksheet = writer.sheets['Resumen Ejecutivo']
            
            # 2. Resumen por Año (Fila 8)
            if 'ano_ejecucion' in df.columns:
                df_year = df.groupby('ano_ejecucion').agg({
                    'monto_pim': 'sum',
                    'monto_total_devengado_anual': 'sum'
                }).reset_index()
                df_year.columns = ['Año', 'PIM Total', 'Devengado Anual']
                df_year['% Avance'] = (df_year['Devengado Anual'] / df_year['PIM Total'] * 100).fillna(0)
                
                worksheet.write(7, 0, "RESUMEN POR AÑO")
                df_year.to_excel(writer, sheet_name='Resumen Ejecutivo', startrow=8, index=False)
                next_row = 8 + len(df_year) + 3
            else:
                next_row = 8
                
            # 3. Resumen por Unidad Gerencial (Fila dinámica)
            if 'unidad_gerencial' in df.columns:
                df_unit = df.groupby('unidad_gerencial').agg({
                    'monto_pim': 'sum',
                    'monto_total_devengado_anual': 'sum'
                }).reset_index()
                df_unit.columns = ['Unidad Gerencial', 'PIM Total', 'Devengado Anual']
                df_unit['% Avance'] = (df_unit['Devengado Anual'] / df_unit['PIM Total'] * 100).fillna(0)
                
                worksheet.write(next_row - 1, 0, "RESUMEN POR UNIDAD GERENCIAL")
                df_unit.to_excel(writer, sheet_name='Resumen Ejecutivo', startrow=next_row, index=False)
                next_row = next_row + len(df_unit) + 3
                
            # 4. Resumen por Mes (Solo si hay columnas de meses)
            meses_cols = [c for c in df.columns if c.startswith('monto_devengado_') and c != 'monto_total_devengado_anual']
            if meses_cols:
                mes_data = []
                for col in meses_cols:
                    mes_nombre = col.replace('monto_devengado_', '').capitalize()
                    monto = df[col].sum()
                    mes_data.append({'Mes': mes_nombre, 'Devengado Total': monto})
                
                df_month = pd.DataFrame(mes_data)
                worksheet.write(next_row - 1, 0, "RESUMEN POR MES (DEVENGADO)")
                df_month.to_excel(writer, sheet_name='Resumen Ejecutivo', startrow=next_row, index=False)
            
            # --- HOJA 2: RESUMEN PREDICCIÓN (Por Unidad Gerencial) ---
            if 'unidad_gerencial' in df.columns:
                # Agrupar por Unidad
                pred_df = df.groupby('unidad_gerencial').agg({
                    'monto_pim': 'sum',
                    'monto_total_devengado_anual': 'sum' # Usamos anual para la predicción general
                }).reset_index()
                
                # Calcular métricas
                pred_df['Saldo por Ejecutar'] = pred_df['monto_pim'] - pred_df['monto_total_devengado_anual']
                pred_df['% Avance'] = (pred_df['monto_total_devengado_anual'] / pred_df['monto_pim'] * 100).fillna(0)
                
                # Renombrar columnas
                pred_df.columns = ['Unidad Gerencial', 'PIM Total', 'Devengado Acumulado', 'Saldo por Ejecutar', '% Avance']
                pred_df.to_excel(writer, sheet_name='Resumen Predicción', index=False)
            else:
                pd.DataFrame({'Info': ['No hay columna unidad_gerencial']}).to_excel(writer, sheet_name='Resumen Predicción', index=False)
            
            # --- HOJA 3: DETALLE DE PROYECTOS ---
            df.to_excel(writer, sheet_name='Detalle de Proyectos', index=False)
            
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Reporte_Ejecutivo.xlsx"}
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/historical-analysis")
async def get_historical_analysis(current_user: str = Depends(get_current_user)):
    try:
        engine = create_engine_connection()
        
        # 1. Historical Evolution (All available years)
        query_hist = """
        SELECT ano_ejecucion, SUM(monto_pim) as pim, SUM(monto_total_devengado_anual) as devengado
        FROM ejecucion_financiera
        GROUP BY ano_ejecucion
        ORDER BY ano_ejecucion
        """
        
        # 2. Seasonality (Average % per month over all years)
        query_season = """
        SELECT 
            SUM(monto_devengado_enero) as ene, SUM(monto_devengado_febrero) as feb,
            SUM(monto_devengado_marzo) as mar, SUM(monto_devengado_abril) as abr,
            SUM(monto_devengado_mayo) as may, SUM(monto_devengado_junio) as jun,
            SUM(monto_devengado_julio) as jul, SUM(monto_devengado_agosto) as ago,
            SUM(monto_devengado_setiembre) as sep, SUM(monto_devengado_octubre) as oct,
            SUM(monto_devengado_noviembre) as nov, SUM(monto_devengado_diciembre) as dic,
            SUM(monto_total_devengado_anual) as total_anual
        FROM ejecucion_financiera
        """
        
        # 3. Regional Ranking (Efficiency - All years) -> Now by Unidad Gerencial
        query_rank = """
        SELECT unidad_gerencial as unidad, SUM(monto_pim) as pim, SUM(monto_total_devengado_anual) as devengado
        FROM ejecucion_financiera
        GROUP BY unidad_gerencial
        """
        
        with engine.connect() as conn:
            df_hist = pd.read_sql(query_hist, conn)
            df_season = pd.read_sql(query_season, conn)
            df_rank = pd.read_sql(query_rank, conn)
            
        print("DEBUG RANKING COLS:", df_rank.columns)
        print("DEBUG RANKING HEAD:", df_rank.head())
            
        # Process Historical
        historical_data = []
        for _, row in df_hist.iterrows():
            pim = row['pim']
            dev = row['devengado']
            eficacia = (dev / pim * 100) if pim > 0 else 0
            historical_data.append({
                'anio': str(int(row['ano_ejecucion'])),
                'pim': pim,
                'devengado': dev,
                'eficacia': round(eficacia, 1)
            })
            
        # Process Seasonality
        seasonality_data = []
        if not df_season.empty:
            total = df_season.iloc[0]['total_anual']
            meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
            nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            
            for i, mes_col in enumerate(meses):
                monto_mes = df_season.iloc[0][mes_col]
                promedio = (monto_mes / total * 100) if total > 0 else 0
                
                intensidad = 'baja'
                if promedio > 10: intensidad = 'muy-alta'
                elif promedio > 8: intensidad = 'alta'
                elif promedio > 6: intensidad = 'media'
                
                seasonality_data.append({
                    'mes': nombres[i],
                    'promedio': round(promedio, 1),
                    'intensidad': intensidad
                })
                
        # Process Ranking
        ranking_data = []
        for _, row in df_rank.iterrows():
            pim = row['pim']
            dev = row['devengado']
            eficacia = (dev / pim * 100) if pim > 0 else 0
            ranking_data.append({
                'unidad': row['unidad'],
                'eficacia_promedio': round(eficacia, 1),
                'tendencia': 'stable' 
            })
            
        # Sort ranking by efficiency
        ranking_data.sort(key=lambda x: x['eficacia_promedio'], reverse=True)
        ranking_data = ranking_data[:5] # Top 5
        
        return {
            "historical": historical_data,
            "seasonality": seasonality_data,
            "ranking": ranking_data
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/regiones")
def get_regiones(current_user: str = Depends(get_current_user)):
    try:
        engine = create_engine_connection()
        query = "SELECT DISTINCT departamento_meta FROM ejecucion_financiera WHERE departamento_meta IS NOT NULL ORDER BY departamento_meta"
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df['departamento_meta'].tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Ejecutar servidor
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/api/reporte-general-data")
async def get_reporte_data(
    unidad: str = "Todas",
    anio: str = "2025",
    current_user: str = Depends(get_current_user)
):
    df = obtener_datos_bd(agrupar=False)
    
    # Obtener listas únicas para filtros (antes de filtrar)
    programas_list = sorted(df['programa_presupuestal'].dropna().unique().tolist()) if 'programa_presupuestal' in df.columns else []
    anios_list = sorted(df['ano_de_ejecución'].dropna().unique().astype(int).tolist(), reverse=True) if 'ano_de_ejecución' in df.columns else [2025]

    # --- FILTROS ---
    if unidad != "Todas":
        df = df[df['unidad_gerencial'] == unidad]
    
    if 'ano_de_ejecución' in df.columns and anio != "Todos":
        try:
            anio_int = int(anio)
            df = df[df['ano_de_ejecución'] == anio_int]
        except ValueError:
            pass # Si no es un número válido, no filtramos

    # --- CÁLCULOS ---
    
    # 1. KPIs Globales
    col_pim = 'MONTO_PIM' if 'MONTO_PIM' in df.columns else 'monto_pim'
    col_cert = 'monto_certificado' 
    col_comp = 'MONTO_COMPRO_ANUAL' if 'MONTO_COMPRO_ANUAL' in df.columns else 'monto_compro_anual'
    col_dev = 'monto_total_devengado_anual' 
    
    pim_total = df[col_pim].sum() if col_pim in df.columns else 0
    cert_total = df[col_cert].sum() if col_cert in df.columns else 0
    comp_total = df[col_comp].sum() if col_comp in df.columns else 0
    dev_total = df[col_dev].sum() if col_dev in df.columns else 0
    
    cert_pct = round((cert_total / pim_total * 100), 1) if pim_total > 0 else 0
    comp_pct = round((comp_total / pim_total * 100), 1) if pim_total > 0 else 0
    dev_pct = round((dev_total / pim_total * 100), 1) if pim_total > 0 else 0
    
    # 2. Ejecución por Unidad
    if 'unidad_gerencial' in df.columns:
        grp_unidad = df.groupby('unidad_gerencial')[[col_pim, col_dev]].sum().reset_index()
        unidades_labels = grp_unidad['unidad_gerencial'].tolist()
        unidades_pim = grp_unidad[col_pim].tolist()
        unidades_dev = grp_unidad[col_dev].tolist()
    else:
        unidades_labels = []
        unidades_pim = []
        unidades_dev = []
        
    # 3. Saldo por Ejecutar
    saldo_dev = pim_total - dev_total
    saldo_ca = pim_total - comp_total
    saldo_cert = pim_total - cert_total
    
    # 4. Devengado Trimestral & 5. Mensual Comp vs Dev
    trimestres = [0, 0, 0, 0]
    mensual_comp = []
    mensual_dev = []
    
    meses_suffix = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 
                   'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    
    for i, mes in enumerate(meses_suffix):
        col_d = f"MONTO_DEVENGADO_{mes}"
        col_c = f"MONTO_COMPRO_{mes}"
        
        val_d = df[col_d].sum() if col_d in df.columns else 0
        val_c = df[col_c].sum() if col_c in df.columns else 0
        
        mensual_dev.append(val_d)
        mensual_comp.append(val_c)
        
        # Trimestres
        if i < 3: trimestres[0] += val_d
        elif i < 6: trimestres[1] += val_d
        elif i < 9: trimestres[2] += val_d
        else: trimestres[3] += val_d

    return {
        "filtros_disponibles": {
            "programas": programas_list,
            "anios": anios_list
        },
        "pim": pim_total,
        "devengado": dev_total,
        "certificado_pct": cert_pct,
        "compromiso_pct": comp_pct,
        "devengado_pct": dev_pct,
        "unidades": {
            "labels": unidades_labels,
            "pim": unidades_pim,
            "devengado": unidades_dev
        },
        "global": {
            "labels": ["PIM", "Certificado", "Compromiso", "Devengado"],
            "values": [pim_total, cert_total, comp_total, dev_total]
        },
        "saldo": {
            "labels": ["Saldo x DEV", "Saldo x CA", "Saldo x CERT"],
            "values": [saldo_dev, saldo_ca, saldo_cert]
        },
        "trimestre": {
            "labels": ["Trimestre 1", "Trimestre 2", "Trimestre 3", "Trimestre 4"],
            "values": trimestres
        },
        "mensual": {
            "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"],
            "compromiso": mensual_comp,
            "devengado": mensual_dev
        }
    }
