import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
import calendar
import os
import io
import traceback
import xlsxwriter
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import openai
from email.mime.image import MIMEImage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# --- CONFIGURACIÓN DE SEGURIDAD ---
SECRET_KEY = "pronied_secret_key_2025" # En producción usar variable de entorno
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# pwd_context removed, using bcrypt directly
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
    administrador: int | None = None
    nombres: str | None = None
    apellidos: str | None = None

class User(BaseModel):
    username: str
    full_name: str | None = None

# --- FUNCIONES DE SEGURIDAD ---
def verify_password(plain_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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
    return FileResponse('login.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/reporte")
async def reporte_view():
    return FileResponse('reporte_general.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/analisis-historico")
async def analisis_historico_view():
    return FileResponse('analisis_historico.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/reporte-ejecutivo")
async def reporte_ejecutivo_view():
    return FileResponse('reporte_ejecutivo.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/importacion")
async def importacion_view():
    return FileResponse('importacion.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/dashboard_view")
async def read_dashboard():
    return FileResponse('dasboard_frontend.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/usuarios")
async def usuarios_view():
    return FileResponse('usuarios.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

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
    
    # Validar si está activo
    if 'activo' in df.columns and user_row['activo'] == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacte al administrador.",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
    
    is_admin = int(user_row.get('administrador', 0))
    nombres = user_row.get('nombres', '')
    apellidos = user_row.get('apellidos', '')
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "administrador": is_admin,
        "nombres": nombres,
        "apellidos": apellidos
    }

@app.get("/api/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    engine = create_engine_connection()
    query = f"SELECT * FROM usuarios WHERE username = '{current_user}'"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    if not df.empty:
        user_row = df.iloc[0].to_dict()
        user_row.pop('hashed_password', None)
        return user_row
    return {"username": current_user}

from sqlalchemy import create_engine, text

# --- 1. CONFIGURACIÓN Y CONEXIÓN A BASE DE DATOS ---
# Simulamos que hoy es el mes actual del sistema
MES_ACTUAL_SIMULADO = 5
MESES_SUFIJOS = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 
                 'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

# Global Database Configuration & Engine (Singleton)
import os
DB_CONNECTION_URL = os.getenv("DB_CONNECTION_URL", (
    "postgresql+psycopg2://proniedadmin:Qazokm2020$$@pronied-db-server.postgres.database.azure.com:5432/postgres"
))

# Initialize Singleton Engine with Connection Pooling
engine = create_engine(
    DB_CONNECTION_URL, 
    pool_pre_ping=True, 
    pool_size=10, 
    max_overflow=20,
    connect_args={'connect_timeout': 5}
)

def create_engine_connection():
    """Returns the singleton engine instance."""
    return engine

def migrate_from_csv():
    import os
    import pandas as pd
    from sqlalchemy import inspect
    
    csv_dir = "migration_data"
    if not os.path.exists(csv_dir):
        return
        
    tablas = ['usuarios', 'ejecucion_financiera', 'control_cambios', 'configuracion_reportes', 'configuracion_alertas']
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        with engine.connect() as conn:
            for tabla in tablas:
                csv_path = os.path.join(csv_dir, f"{tabla}.csv")
                if not os.path.exists(csv_path):
                    continue
                    
                # Si la tabla ya existe y tiene datos, no sobreescribir
                if tabla in existing_tables:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
                    if count > 0:
                        continue
                        
                print(f"Migrando {tabla} desde CSV...")
                df = pd.read_csv(csv_path)
                df.to_sql(tabla, conn, if_exists='append', index=False)
                print(f"Tabla {tabla} poblada con {len(df)} registros.")
    except Exception as e:
        print(f"Error en migracion CSV: {e}")

def setup_database_triggers():
    """Configura la tabla de control de cambios y triggers en la BD."""
    migrate_from_csv()
    return
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
            

            # 4. Crear tabla de configuración de reportes si no existe
            conn.execute(text('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='configuracion_reportes' AND xtype='U')
                CREATE TABLE configuracion_reportes (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    username VARCHAR(50) NOT NULL,
                    dia_semana VARCHAR(10) NOT NULL,
                    hora VARCHAR(2) NOT NULL,
                    minuto VARCHAR(2) NOT NULL,
                    activo BIT NOT NULL
                )
            '''))
            conn.commit()

            # Insertar configuración por defecto para admin (si está vacía)
            conn.execute(text('''
                IF NOT EXISTS (SELECT * FROM configuracion_reportes)
                INSERT INTO configuracion_reportes (username, dia_semana, hora, minuto, activo) 
                VALUES ('admin', 'fri', '17', '00', 1)
            '''))
            conn.commit()
            
            # Migración: Agregar columna username si la tabla existe pero le falta la columna
            conn.execute(text('''
                IF EXISTS (SELECT * FROM sysobjects WHERE name='configuracion_reportes' AND xtype='U')
                AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('configuracion_reportes') AND name = 'username')
                BEGIN
                    ALTER TABLE configuracion_reportes ADD username VARCHAR(50) NULL;
                    EXEC('UPDATE configuracion_reportes SET username = ''admin'' WHERE username IS NULL');
                    ALTER TABLE configuracion_reportes ALTER COLUMN username VARCHAR(50) NOT NULL;
                END
            '''))
            conn.commit()
            conn.commit()
            
            # 5. Crear tabla de configuración de alertas (HU004) si no existe
            conn.execute(text('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='configuracion_alertas' AND xtype='U')
                CREATE TABLE configuracion_alertas (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    username VARCHAR(50) NOT NULL,
                    dia_semana VARCHAR(10) NOT NULL,
                    hora VARCHAR(2) NOT NULL,
                    minuto VARCHAR(2) NOT NULL,
                    activo BIT NOT NULL
                )
            '''))
            conn.commit()

            # Insertar configuración por defecto para admin si está vacía
            conn.execute(text('''
                IF NOT EXISTS (SELECT * FROM configuracion_alertas)
                INSERT INTO configuracion_alertas (username, dia_semana, hora, minuto, activo) 
                VALUES ('admin', '*', '09', '39', 1)
            '''))
            conn.commit()

            # Migración: Agregar columna username si la tabla existe pero le falta la columna
            conn.execute(text('''
                IF EXISTS (SELECT * FROM sysobjects WHERE name='configuracion_alertas' AND xtype='U')
                AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('configuracion_alertas') AND name = 'username')
                BEGIN
                    ALTER TABLE configuracion_alertas ADD username VARCHAR(50) NULL;
                    EXEC('UPDATE configuracion_alertas SET username = ''admin'' WHERE username IS NULL');
                    ALTER TABLE configuracion_alertas ALTER COLUMN username VARCHAR(50) NOT NULL;
                END
            '''))
            conn.commit()
            # 6. Validar si la tabla usuarios tiene la columna dni, si no agregarla
            conn.execute(text('''
                IF EXISTS (SELECT * FROM sysobjects WHERE name='usuarios' AND xtype='U')
                AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('usuarios') AND name = 'dni')
                BEGIN
                    ALTER TABLE usuarios ADD dni VARCHAR(15) NULL;
                END
            '''))
            conn.commit()
            
            print("✅ Triggers y tablas adicionales configurados correctamente.")

    except Exception as e:
        print(f"⚠️ Alerta: No se pudieron configurar los triggers automáticos: {e}")

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    setup_database_triggers()
    
    # HU004 funciona como un "Scheduler" formal (Cron)
    try:
        with engine.connect() as conn:
            configs_alertas = conn.execute(text("SELECT username, dia_semana, hora, minuto, activo FROM configuracion_alertas")).fetchall()
            for config_alerta in configs_alertas:
                username, dia_semana, hora, minuto, activo = config_alerta
                if activo:
                    kwargs = {'hour': int(hora), 'minute': int(minuto), 'id': f"alerta_retrasos_{username}", 'replace_existing': True, 'args': [username]}
                    if dia_semana != '*':
                        kwargs['day_of_week'] = dia_semana
                    scheduler.add_job(ejecutar_alertas_h004, 'cron', **kwargs)
                    print(f"✅ HU004 programada para {username}: {dia_semana} a las {hora}:{minuto}")
                else:
                    print(f"ℹ️ HU004 (Alerta de Retrasos) desactivada para {username}.")
    except Exception as e:
        print(f"⚠️ Error cargando configuración de alertas: {e}")
        
    # HU011 funciona como un "Scheduler" formal (Cron)
    try:
        with engine.connect() as conn:
            configs_reportes = conn.execute(text("SELECT username, dia_semana, hora, minuto, activo FROM configuracion_reportes")).fetchall()
            for config in configs_reportes:
                username, dia_semana, hora, minuto, activo = config
                if activo:
                    scheduler.add_job(
                        enviar_resumen_semanal_h011, 
                        'cron', 
                        day_of_week=dia_semana, 
                        hour=int(hora), 
                        minute=int(minuto), 
                        id=f"reporte_semanal_{username}", 
                        replace_existing=True,
                        args=[username]
                    )
                    print(f"✅ HU011 programada para {username}: {dia_semana} a las {hora}:{minuto}")
                else:
                    print(f"ℹ️ HU011 (Resumen Semanal) desactivado para {username}.")
    except Exception as e:
        print(f"⚠️ Error cargando configuración de reportes: {e}")
    
    # Tarea de prueba para que se envíe en el minuto actual o pronto:
    # scheduler.add_job(enviar_resumen_semanal_h011, 'cron', hour=22, minute=58)
    
    scheduler.start()
    print("✅ Scheduler (APScheduler) iniciado correctamente para la HU011.")

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

# --- 2. LÓGICA DE MACHINE LEARNING Y TAREAS (Random Forest) ---
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def ejecutar_alertas_h004(username):
    """
    Historia de Usuario 004: Tarea programada que ejecuta la predicción
    y envía correo al usuario suscrito si detecta riesgo > 80%
    """
    # 1. Ejecutar predicción para obtener las unidades simuladas
    data = entrenar_y_predecir("Todas", flag_alerta=False)
    
    unidades_en_riesgo = []
    # 2. Filtrar cuáles están en riesgo de incumplimiento (Aplica la nueva lógica de negocio)
    for unidad in data['unidades']:
        # Calculamos el % que SI se va a usar
        avance_pct = (unidad['proyeccion_cierre'] / unidad['pim']) * 100 if unidad['pim'] > 0 else 0
        
        # Si el avance proyectado cae por debajo del 80%, es una alerta roja
        if avance_pct < 80:
            unidades_en_riesgo.append({
                "nombre": unidad['unidad'],
                "pct": avance_pct
            })
            
    if not unidades_en_riesgo:
        print("✅ [H004] Revisión completada. Ninguna unidad supera el 80% de riesgo proyectado.")
        return
        
    # 3. Obtener usuario enrolado desde la BD
    engine = create_engine_connection()
    try:
        query_usuarios = f"SELECT correo FROM usuarios WHERE username = '{username}'"
        with engine.connect() as conn:
            df_usuarios = pd.read_sql(query_usuarios, conn)
            destinatarios = df_usuarios['correo'].dropna().tolist()
    except Exception as e:
        print(f"⚠️ Error obteniendo correo para {username}: {e}")
        destinatarios = [] # Si falla la consulta, vaciamos la lista

    if not destinatarios:
        print(f"⚠️ [H004] Hay proyectos en riesgo, pero el usuario {username} no tiene correo configurado.")
        return

    # 4. Enviar un correo consolidado (o individual) a los destinatarios
    remitente = "kevinjuerg2019@gmail.com"
    password = "rjxoukdkcephfnqp"
    
    for dest in destinatarios:
        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = dest
        msg['Subject'] = f"🚨 PRONIED – Retrasos en unidades gerenciales"

        html_cuerpo = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    border: 1px solid #e0e0e0;
                }}
                .header {{
                    background-color: #d32f2f;
                    color: white;
                    padding: 20px;
                    display: flex;
                    align-items: center;
                }}
                .header-icon {{
                    font-size: 28px;
                    margin-right: 15px;
                }}
                .header-text h1 {{
                    margin: 0;
                    font-size: 22px;
                    font-weight: bold;
                    letter-spacing: 1px;
                }}
                .header-text p {{
                    margin: 5px 0 0 0;
                    font-size: 13px;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 30px;
                    color: #333333;
                    line-height: 1.6;
                }}
                .content h2 {{
                    margin-top: 0;
                    font-size: 18px;
                    color: #333;
                }}
                .highlight {{
                    background-color: #fdeaea;
                    color: #c62828;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 25px;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    overflow: hidden;
                }}
                th {{
                    background-color: #f5f5f5;
                    color: #757575;
                    font-size: 12px;
                    font-weight: bold;
                    text-align: left;
                    padding: 15px 20px;
                    border-bottom: 1px solid #e0e0e0;
                }}
                th.right {{
                    text-align: right;
                }}
                td {{
                    padding: 15px 20px;
                    border-bottom: 1px solid #e0e0e0;
                }}
                tr:last-child td {{
                    border-bottom: none;
                }}
                .unit-name {{
                    font-weight: bold;
                    font-size: 16px;
                    color: #333;
                }}
                .red-dot {{
                    color: #d32f2f;
                    margin-right: 8px;
                    font-size: 14px;
                }}
                .projection {{
                    color: #d32f2f;
                    font-weight: bold;
                    font-size: 18px;
                    text-align: right;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 13px;
                    color: #757575;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <span class="header-icon">🚨</span>
                    <div class="header-text">
                        <h1>ALERTA CRÍTICA DE EJECUCIÓN</h1>
                        <p>Sistema de Inteligencia PRONIED</p>
                    </div>
                </div>
                <div class="content">
                    <h2>Estimado Equipo de Gestión,</h2>
                    <p>Proyecto: Plataforma de análisis predictivo para la programación y ejecución presupuestal mediante Data Analytics y los modelos de Random Forest con XGBoost en la infraestructura educativa a nivel nacional.</p>
                    <p>El <strong>modelo predictivo</strong> ha detectado un riesgo crítico en la trayectoria de gasto presupuestal. Las siguientes unidades gerenciales cerrarán el año <span class="highlight">por debajo del umbral mínimo (80%)</span> si no se toman medidas correctivas.</p>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>UNIDAD GERENCIAL</th>
                                <th class="right">PROYECCIÓN IA</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for u in unidades_en_riesgo:
            html_cuerpo += f"""
                            <tr>
                                <td class="unit-name"><span class="red-dot">🔴</span> {u['nombre']}</td>
                                <td class="projection">{u['pct']:.2f}%</td>
                            </tr>
            """
            
        html_cuerpo += """
                        </tbody>
                    </table>
                    
                    <p class="footer">Por favor, tomar acciones correctivas inmediatas.<br><br>Atentamente,<br>Sistema de Inteligencia PRONIED.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_cuerpo, 'html'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)
            server.quit()
            print(f"📧 ALERTA H004 ENVIADA FÍSICAMENTE a {dest} por {len(unidades_en_riesgo)} caso(s).")
        except Exception as e:
            print(f"⚠️ Error enviando correo: {e}")



def enviar_resumen_semanal_h011(username):
    """
    Historia de Usuario 011: Envía un resumen semanal automático por correo al usuario.
    """
    print("⏳ [H011] Generando datos para el resumen semanal automático...")
    try:
        data = entrenar_y_predecir("Todas", flag_alerta=False)
    except Exception as e:
        print(f"⚠️ [H011] Error al generar predicciones: {e}")
        return

    global_data = data.get("global", {})
    kpi_mes = data.get("kpi_mes_actual", {})
    unidades = data.get("unidades", [])

    pim_total = global_data.get("pim_total", 0)
    ejec_acum = global_data.get("devengado_acumulado", 0)
    
    saldo_riesgo = 0
    unidades_riesgo_count = 0
    unidades_html = ""
    
    for u in sorted(unidades, key=lambda x: (x["proyeccion_cierre"]/x["pim"] if x["pim"]>0 else 0), reverse=True):
        avance_pct = (u["proyeccion_cierre"] / u["pim"]) * 100 if u["pim"] > 0 else 0
        is_risk = avance_pct < 80
        
        if is_risk:
            saldo_riesgo += (u["pim"] - u["proyeccion_cierre"])
            unidades_riesgo_count += 1
            riesgo_badge = '<span class="badge badge-alto">ALTO</span>'
        elif avance_pct < 90:
            riesgo_badge = '<span class="badge badge-medio">MEDIO</span>'
        else:
            riesgo_badge = '<span class="badge badge-bajo">BAJO</span>'
            
        unidades_html += f"""
        <tr>
            <td>{u['unidad']}</td>
            <td>{avance_pct:.1f}%</td>
            <td>{riesgo_badge}</td>
        </tr>
        """

    # Corrección para el cálculo de Ejecución vs Meta (PIM)
    ejec_vs_meta = (ejec_acum / pim_total) * 100 if pim_total > 0 else 0
    
    # Desviación crítica
    peor_unidad = min(unidades, key=lambda x: (x["proyeccion_cierre"]/x["pim"]) if x["pim"] > 0 else float('inf')) if unidades else None
    peor_pct = ((peor_unidad["proyeccion_cierre"]/peor_unidad["pim"])*100) if peor_unidad and peor_unidad["pim"] > 0 else 0
    
    global_proy_pct = (global_data.get("proyeccion_cierre", 0) / pim_total) * 100 if pim_total > 0 else 0
    desviacion_pp = (global_proy_pct - peor_pct) if peor_unidad else 0

    # Generar Gráfico con Matplotlib
    try:
        global_compromiso = [0] * 12
        global_real = [0] * 12
        global_prediccion = [0] * 12
        
        for u in unidades:
            grafico = u.get("grafico", {})
            comp = grafico.get("compromiso", [])
            real = grafico.get("real", [])
            pred = grafico.get("prediccion_curva", [])
            
            for i in range(12):
                if i < len(comp) and comp[i] is not None: global_compromiso[i] += comp[i]
                if i < len(real) and real[i] is not None: global_real[i] += real[i]
                if i < len(pred) and pred[i] is not None: global_prediccion[i] += pred[i]
        
        real_plot = []
        for i in range(12):
            if i < len(unidades[0]["grafico"]["real"]) and unidades[0]["grafico"]["real"][i] is not None:
                real_plot.append(global_real[i])
            else:
                real_plot.append(np.nan)

        fig, ax = plt.subplots(figsize=(7, 3.5))
        meses = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SET', 'OCT', 'NOV', 'DIC']
        
        ax.plot(meses, global_compromiso, linestyle='--', color='#9ca3af', label='Meta (Compromiso)', linewidth=1.5)
        ax.plot(meses, real_plot, marker='o', color='#4f46e5', label='Ejecutado Real', linewidth=2, markersize=5)
        ax.plot(meses, global_prediccion, linestyle=':', marker='x', color='#f59e0b', label='Proyección IA', linewidth=2, markersize=5)
        
        # Formatear eje Y en millones para que sea más legible
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
        
        ax.set_ylabel('Soles (S/)', fontsize=9, color='#6b7280')
        ax.tick_params(axis='x', labelsize=8, colors='#6b7280')
        ax.tick_params(axis='y', labelsize=8, colors='#6b7280')
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e5e7eb')
        ax.spines['bottom'].set_color('#e5e7eb')
        ax.grid(True, linestyle='--', alpha=0.3)
        
        fig.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120)
        plt.close(fig)
        buf.seek(0)
        img_data = buf.read()
    except Exception as e:
        print(f"⚠️ Error generando gráfico: {e}")
        img_data = None


    engine = create_engine_connection()
    try:
        query_usuarios = f"SELECT correo FROM usuarios WHERE username = '{username}'"
        with engine.connect() as conn:
            df_usuarios = pd.read_sql(query_usuarios, conn)
            destinatarios = df_usuarios['correo'].dropna().tolist()
    except Exception as e:
        print(f"⚠️ Error obteniendo usuarios para correo de {username}: {e}")
        destinatarios = []
        
    if not destinatarios:
        print(f"⚠️ [H011] No hay correo configurado para el usuario {username}.")
        return

    remitente = "kevinjuerg2019@gmail.com"
    password = "rjxoukdkcephfnqp"
    
    ahora = datetime.now()
    semana_actual = ahora.isocalendar()[1]
    fecha_inicio = (ahora - timedelta(days=ahora.weekday())).strftime("%d/%m/%Y")
    fecha_fin = (ahora + timedelta(days=6-ahora.weekday())).strftime("%d/%m/%Y")

    for dest in destinatarios:
        msg = MIMEMultipart('related')
        msg['From'] = remitente
        msg['To'] = dest
        msg['Subject'] = f"📊 PRONIED – Resumen Semanal de Ejecución (Semana {semana_actual})"

        html_cuerpo = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f5f7; margin: 0; padding: 20px; color: #333; }}
                .wrapper {{ max-width: 700px; margin: 0 auto; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden; }}
                .header {{ background-color: #1a2035; color: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; }}
                .header-logo {{ font-size: 22px; font-weight: bold; letter-spacing: 1px; float: left; margin-top: 5px; }}
                .header-right {{ text-align: right; float: right; }}
                .header-right .title {{ font-weight: bold; font-size: 15px; margin-bottom: 2px; }}
                .header-right .date {{ font-size: 11px; color: #a0a5b5; }}
                .clearfix::after {{ content: ""; clear: both; display: table; }}
                
                .content {{ padding: 30px; }}
                .greeting {{ font-size: 18px; font-weight: bold; color: #1a2035; margin-top: 0; margin-bottom: 5px; }}
                .subtitle {{ font-size: 13px; color: #666; margin-bottom: 25px; }}
                
                .section-title {{ color: #4252d6; font-size: 15px; font-weight: bold; margin-bottom: 15px; margin-top: 30px; }}
                
                .kpi-container {{ width: 100%; border-spacing: 10px; margin-left: -10px; display: table; }}
                .kpi-card {{ display: table-cell; width: 25%; border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; text-align: left; background: #fff; }}
                .kpi-title {{ font-size: 11px; color: #6c757d; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; }}
                .kpi-value {{ font-size: 16px; font-weight: bold; color: #1a2035; }}
                
                .grid-2 {{ width: 100%; border-spacing: 15px; margin-left: -15px; display: table; margin-top: 10px; }}
                .col-half {{ display: table-cell; width: 50%; vertical-align: top; }}
                
                .box {{ border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; background: #fff; height: 200px; }}
                .box-title {{ font-size: 13px; font-weight: bold; color: #333; margin-top: 0; margin-bottom: 15px; }}
                
                .chart-mock {{ background-color: #f8f9fa; border-radius: 6px; height: 130px; display: flex; align-items: center; justify-content: center; text-align: center; border: 1px dashed #ced4da; margin-bottom: 10px; }}
                .chart-mock p {{ color: #4252d6; font-weight: bold; font-size: 14px; margin: auto; padding-top: 50px; }}
                
                table.unit-table {{ width: 100%; border-collapse: collapse; }}
                table.unit-table th {{ text-align: left; font-size: 10px; color: #6c757d; padding-bottom: 10px; border-bottom: 1px solid #e9ecef; }}
                table.unit-table td {{ font-size: 12px; font-weight: bold; color: #333; padding: 8px 0; border-bottom: 1px solid #f8f9fa; }}
                .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; }}
                .badge-alto {{ background: #fdeaea; color: #d32f2f; }}
                .badge-medio {{ background: #fff8e1; color: #f57f17; }}
                .badge-bajo {{ background: #e8f5e9; color: #2e7d32; }}
                
                .alert-box {{ background-color: #fffafb; border-left: 4px solid #d32f2f; padding: 12px 15px; border-radius: 4px; margin-bottom: 10px; display: block; }}
                .alert-box.warning {{ background-color: #fffdf5; border-left: 4px solid #f59e0b; }}
                .alert-title {{ margin: 0 0 3px 0; font-size: 12px; color: #8b0000; font-weight: bold; }}
                .alert-box.warning .alert-title {{ color: #b45309; }}
                .alert-desc {{ margin: 0; font-size: 11px; color: #d32f2f; line-height: 1.4; }}
                .alert-box.warning .alert-desc {{ color: #b45309; }}
                
                .month-table {{ width: 100%; border-collapse: collapse; }}
                .month-table td {{ padding: 10px; border-bottom: 1px solid #e9ecef; font-size: 12px; font-weight: bold; color: #333; }}
                .month-table td.trend {{ text-align: right; color: #d32f2f; font-weight: normal; }}
                
                .footer {{ text-align: center; margin-top: 40px; margin-bottom: 20px; }}
                .footer p {{ font-size: 12px; color: #6c757d; margin-bottom: 15px; }}
                .btn {{ display: inline-block; padding: 10px 20px; font-size: 13px; font-weight: bold; text-decoration: none; border-radius: 6px; margin: 0 5px; border: 1px solid #4252d6; }}
                .btn-primary {{ background-color: #4252d6; color: white; }}
                .btn-outline {{ background-color: white; color: #4252d6; }}
            </style>
        </head>
        <body>
            <div class="wrapper">
                <div class="header clearfix">
                    <div class="header-logo">PRONIED</div>
                    <div class="header-right">
                        <div class="title">📅 Resumen Semanal</div>
                        <div class="date">Semana {semana_actual}: {fecha_inicio} al {fecha_fin}</div>
                    </div>
                </div>
                <div class="content">
                    <h2 class="greeting">Hola, Director(a)</h2>
                    <p class="subtitle">Te compartimos el resumen automático de la ejecución al cierre de semana.</p>
                    
                    <div class="section-title">Resumen Ejecutivo</div>
                    <div class="kpi-container">
                        <div class="kpi-card">
                            <div class="kpi-title">PIM TOTAL</div>
                            <div class="kpi-value">S/ {pim_total:,.0f}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-title">EJECUC. ACUM.</div>
                            <div class="kpi-value">S/ {ejec_acum:,.0f}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-title">⚠️ SALDO RIESGO</div>
                            <div class="kpi-value">S/ {saldo_riesgo:,.0f}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-title">🎯 EJEC vs META</div>
                            <div class="kpi-value">{ejec_vs_meta:.1f}%</div>
                        </div>
                    </div>
                    
                    <div class="grid-2">
                        <div class="col-half">
                            <div class="box">
                                <h3 class="box-title">Ejecución vs Meta (Acumulado)</h3>
                                <div style="text-align: center; margin-bottom: 10px;">
                                    <img src="cid:curva_s" alt="Gráfico Curva S" style="max-width: 100%; border-radius: 6px; border: 1px solid #e9ecef;">
                                </div>
                                <div style="text-align: center; font-size: 10px; color: #666;">
                                    <span style="color: #9ca3af; font-weight: bold;">--</span> Meta &nbsp;&nbsp; 
                                    <span style="color: #4f46e5; font-size: 14px;">●</span> Ejecutado Real &nbsp;&nbsp; 
                                    <span style="color: #f59e0b; font-weight: bold;">x</span> Proyección IA
                                </div>
                            </div>
                        </div>
                        <div class="col-half">
                            <div class="box" style="overflow-y: auto;">
                                <h3 class="box-title">Ejecución por Unidad</h3>
                                <table class="unit-table">
                                    <tr>
                                        <th>UNIDAD</th>
                                        <th>EJEC%</th>
                                        <th>RIESGO</th>
                                    </tr>
                                    {unidades_html}
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="grid-2">
                        <div class="col-half">
                            <div class="section-title" style="margin-top:0;">Alertas y Riesgos</div>
                            <div class="alert-box">
                                <h4 class="alert-title">🚨 Desviación Crítica</h4>
                                <p class="alert-desc">{peor_unidad['unidad'] if peor_unidad else 'N/A'} presenta ejecución {desviacion_pp:.1f} pp debajo de la meta.</p>
                            </div>
                            <div class="alert-box warning">
                                <h4 class="alert-title">⚠️ Riesgo de Incumplimiento</h4>
                                <p class="alert-desc">{unidades_riesgo_count} proyectos con avance menor al 80%.</p>
                            </div>
                        </div>
                        <div class="col-half">
                            <div class="section-title" style="margin-top:0;">Estacionalidad (3 meses)</div>
                            <table class="month-table">
                                <tr><td>SEPTIEMBRE</td><td class="trend">5.7% ↓</td></tr>
                                <tr><td>OCTUBRE</td><td class="trend">5.1% ↓</td></tr>
                                <tr><td>NOVIEMBRE</td><td class="trend">4.1% ↓</td></tr>
                            </table>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>Accede a los reportes completos para mayor detalle</p>
                        <a href="http://localhost:8005/" class="btn btn-primary">Ver Reporte General</a>
                        <a href="http://localhost:8005/" class="btn btn-outline">Ver Análisis Histórico</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_cuerpo, 'html'))
        
        if img_data:
            image = MIMEImage(img_data)
            image.add_header('Content-ID', '<curva_s>')
            image.add_header('Content-Disposition', 'inline', filename='curva_s.png')
            msg.attach(image)

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)
            server.quit()
            print(f"📧 [H011] Resumen Semanal ENVIADO a {dest}.")
        except Exception as e:
            print(f"⚠️ [H011] Error enviando correo a {dest}: {e}")

def entrenar_y_predecir(unidad_filtro=None, flag_alerta=False):
    df = df_global.copy()
    
    # Filtro por Unidad Gerencial
    if unidad_filtro and unidad_filtro != "Todas":
        df = df[df["unidad_gerencial"] == unidad_filtro]

    # --- Preprocesamiento: Transformar a formato para ML ---
    unidad_map = {u: idx for idx, u in enumerate(df['unidad_gerencial'].unique())}
    
    ml_data = []
    for index, row in df.iterrows():
        devengado_acumulado_previo = 0
        for i, mes in enumerate(MESES_SUFIJOS):
            mes_num = i + 1
            
            # REGLA ML: Entrenar SOLO con meses cerrados.
            # No entrenamos con Agosto 2026 porque es parcial y ensuciaría el modelo.
            es_mes_cerrado = (row['ano_de_ejecución'] < 2026) or (row['ano_de_ejecución'] == 2026 and mes_num < MES_ACTUAL_SIMULADO)
            
            pim = row['MONTO_PIM']
            devengado_actual = row[f'MONTO_DEVENGADO_{mes}']
            compromiso_actual = row[f'MONTO_COMPRO_{mes}']
            
            devengado_anterior = 0
            if i > 0:
                mes_ant = MESES_SUFIJOS[i-1]
                devengado_anterior = row[f'MONTO_DEVENGADO_{mes_ant}']
            
            pct_avance_previo = (devengado_acumulado_previo / pim) if pim > 0 else 0
            saldo_restante = pim - devengado_acumulado_previo
            
            # NUEVOS FEATURES ESCALADOS (PORCENTAJES)
            compromiso_pct_mes = (compromiso_actual / pim) if pim > 0 else 0
            devengado_anterior_pct = (devengado_anterior / pim) if pim > 0 else 0
            saldo_restante_pct = (saldo_restante / pim) if pim > 0 else 0
            devengado_pct_mes = (devengado_actual / pim) if pim > 0 else 0 # TARGET REAL
            
            # --- NUEVAS VARIABLES DE CONTEXTO (Bajar el MAE) ---
            es_trimestre_cierre = 1 if mes_num >= 10 else 0
            es_pandemia = 1 if row['ano_de_ejecución'] == 2020 else 0
            presion_gasto = saldo_restante_pct * mes_num
            
            if es_mes_cerrado:
                ml_data.append({
                    'anio': row['ano_de_ejecución'],
                    'mes': mes_num,
                    'pim_total': pim,
                    'compromiso_mes': compromiso_actual,
                    'compromiso_pct_mes': compromiso_pct_mes,
                    'devengado_anterior': devengado_anterior,
                    'devengado_anterior_pct': devengado_anterior_pct,
                    'pct_avance_previo': pct_avance_previo,
                    'saldo_restante': saldo_restante,
                    'saldo_restante_pct': saldo_restante_pct,
                    'unidad_encoded': unidad_map[row['unidad_gerencial']],
                    'devengado_mes': devengado_actual,
                    'devengado_pct_mes': devengado_pct_mes,
                    'es_trimestre_cierre': es_trimestre_cierre,
                    'es_pandemia': es_pandemia,
                    'presion_gasto': presion_gasto
                })
                
            devengado_acumulado_previo += devengado_actual
            
    train_df = pd.DataFrame(ml_data)
    
    # Entrenar Modelo
    features = ['anio', 'mes', 'pim_total', 'compromiso_pct_mes', 'devengado_anterior_pct', 'pct_avance_previo', 'saldo_restante_pct', 'unidad_encoded', 'es_trimestre_cierre', 'es_pandemia', 'presion_gasto']
    
    # 1. Definir los Modelos Base (Tuning de Hiperparámetros)
    rf_proto = RandomForestRegressor(n_estimators=150, max_depth=10, min_samples_leaf=2, random_state=42)
    xgb_proto = xgb.XGBRegressor(n_estimators=150, max_depth=5, learning_rate=0.05, random_state=42, objective='reg:squarederror')
    
    # 2. Crear el Ensamble Multimodelo (Voting Regressor)
    # Combina el promedio ponderado de ambos cerebros para tener más precisión
    ensemble_model = VotingRegressor(estimators=[
        ('rf', rf_proto),
        ('xgb', xgb_proto)
    ])
    
    # 3. Entrenar el Ensamble
    # --- EVALUACIÓN DEL MODELO ---
    # Separación temporal: Train (datos históricos < 2026) y Test (año actual 2026, meses cerrados)
    train_eval_df = train_df[train_df['anio'] < 2026]
    test_eval_df = train_df[train_df['anio'] == 2026]
    
    if len(train_eval_df) > 0 and len(test_eval_df) > 0:
        # Entrenar en el set de evaluación usando PORCENTAJE
        ensemble_model.fit(train_eval_df[features], train_eval_df['devengado_pct_mes'])
        y_pred_pct_eval = ensemble_model.predict(test_eval_df[features])
        
        # Reconversión a MONTO ABSOLUTO para medir el MAE real
        y_pred_eval = y_pred_pct_eval * test_eval_df['pim_total'].values
        
        # Calcular métricas usando el año 2026 como test
        mae_score = mean_absolute_error(test_eval_df['devengado_mes'], y_pred_eval)
        r2_score_val = r2_score(test_eval_df['devengado_mes'], y_pred_eval)
        promedio_real = test_eval_df['devengado_mes'].mean()
        mae_pct = (mae_score / promedio_real * 100) if promedio_real > 0 else 0
    else:
        # Fallback si no hay suficientes años
        X_train_eval, X_test_eval = train_test_split(train_df, test_size=0.2, random_state=42)
        
        ensemble_model.fit(X_train_eval[features], X_train_eval['devengado_pct_mes'])
        y_pred_pct_eval = ensemble_model.predict(X_test_eval[features])
        
        y_pred_eval = y_pred_pct_eval * X_test_eval['pim_total'].values
        mae_score = mean_absolute_error(X_test_eval['devengado_mes'], y_pred_eval)
        r2_score_val = r2_score(X_test_eval['devengado_mes'], y_pred_eval)
        promedio_real = X_test_eval['devengado_mes'].mean()
        mae_pct = (mae_score / promedio_real * 100) if promedio_real > 0 else 0
    
    print("="*50)
    print("📊 RESULTADOS EVALUACIÓN DEL MODELO (RF + XGBoost)")
    print(f"✅ MAE (Margen de Error): {mae_score:,.2f} soles (equivale a un {mae_pct:.2f}% de error sobre el promedio)")
    print(f"✅ R² (Efectividad/Varianza explicada): {r2_score_val:.4f} ({(r2_score_val*100):.2f}%)")
    print("="*50)

    # Re-entrenar con TODOS los datos históricos disponibles para producción
    ensemble_model.fit(train_df[features], train_df['devengado_pct_mes'])
    
    # --- 3. GENERAR RESULTADOS Y PREDICCIONES 2026 ---
    df_2026 = df[df['ano_de_ejecución'] == 2026]
    unidades_unicas = df_2026['unidad_gerencial'].unique()
    
    # Estructura de respuesta Global
    resumen_total = {
        "pim_total": 0, "proyeccion_cierre": 0, "saldo_presupuestal": 0, "devengado_acumulado": 0,
        "mae_modelo": round(mae_score, 2), "r2_modelo": round(r2_score_val, 4)
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
        row_ug = df_2026[df_2026['unidad_gerencial'] == ug].iloc[0]
        
        data_compromiso = []
        data_devengado_real = [] # Para gráfico (tendrá nulls en futuro)
        data_devengado_pred = [] # Para gráfico (curva completa)
        
        proyeccion_anual_ug = 0
        devengado_acumulado_ug = 0 
        
        devengado_acumulado_previo = 0
        devengado_anterior = 0
        unidad_encoded = unidad_map.get(ug, 0)

        for i, mes_nom in enumerate(MESES_SUFIJOS):
            mes_num = i + 1
            compro = row_ug[f'MONTO_COMPRO_{mes_nom}']
            real = row_ug[f'MONTO_DEVENGADO_{mes_nom}']
            pim_ug = row_ug['MONTO_PIM']
            
            data_compromiso.append(compro)
            
            # FEATURES SCALADOS EN INFERENCIA
            pct_avance_previo = (devengado_acumulado_previo / pim_ug) if pim_ug > 0 else 0
            saldo_restante = pim_ug - devengado_acumulado_previo
            saldo_restante_pct = (saldo_restante / pim_ug) if pim_ug > 0 else 0
            compromiso_pct_mes = (compro / pim_ug) if pim_ug > 0 else 0
            devengado_anterior_pct = (devengado_anterior / pim_ug) if pim_ug > 0 else 0
            
            # NUEVAS VARIABLES DE CONTEXTO EN INFERENCIA (2026)
            es_trimestre_cierre = 1 if mes_num >= 10 else 0
            es_pandemia = 0 # 2026 no es pandemia
            presion_gasto = saldo_restante_pct * mes_num
            
            # Hacer predicción usando el Ensamble Combinado (RF + XGB)
            X_input = pd.DataFrame([[2026, mes_num, pim_ug, compromiso_pct_mes, devengado_anterior_pct, pct_avance_previo, saldo_restante_pct, unidad_encoded, es_trimestre_cierre, es_pandemia, presion_gasto]], columns=features)
            pred_pct_raw = ensemble_model.predict(X_input)[0]
            
            # Reconversión a valor absoluto
            pred_raw = pred_pct_raw * pim_ug
            
            # REGLA DE NEGOCIO: Predicción no puede ser mayor al compromiso ni menor a 0
            pred_ajustada = max(0, min(pred_raw, compro)) 

            # Lógica Temporal
            if mes_num < MES_ACTUAL_SIMULADO:
                # PASADO: El dato real manda
                data_devengado_real.append(float(real))
                data_devengado_pred.append(float(real)) # En pasado, la predicción es la realidad
                proyeccion_anual_ug += real
                devengado_acumulado_ug += real
                
                devengado_anterior = real
                devengado_acumulado_previo += real
                
            elif mes_num == MES_ACTUAL_SIMULADO:
                # MES ACTUAL (Agosto/Noviembre):
                # Real = Lo gastado hasta hoy
                # Predicción = Lo que la IA dice que gastaremos a fin de mes
                data_devengado_real.append(None) # No dibujar línea real incompleta porque el mes no ha cerrado
                data_devengado_pred.append(float(pred_ajustada)) 
                
                # CORRECCIÓN: Para la proyección anual, usamos el MAYOR entre Real y Predicción.
                proyeccion_anual_ug += max(real, pred_ajustada)
                
                # Sumar al KPI Global del Mes
                kpi_mes_actual["meta_compromiso"] += compro
                kpi_mes_actual["ejecutado_real"] += real
                kpi_mes_actual["prediccion_cierre"] += pred_ajustada
                
                devengado_real_final_mes = max(real, pred_ajustada)
                devengado_anterior = devengado_real_final_mes
                devengado_acumulado_previo += devengado_real_final_mes
                
            else:
                # FUTURO: Solo existe la IA
                data_devengado_real.append(None) # No dibujar línea real
                data_devengado_pred.append(float(pred_ajustada))
                proyeccion_anual_ug += pred_ajustada
                
                devengado_anterior = pred_ajustada
                devengado_acumulado_previo += pred_ajustada

        # Calcular KPIs por Unidad
        pim_ug = row_ug['MONTO_PIM']
        saldo = pim_ug - proyeccion_anual_ug # Lo que va a sobrar
        avance_pct = (proyeccion_anual_ug / pim_ug) * 100 if pim_ug > 0 else 0
        
        # Semáforo de Riesgo Unificado con Alertas Inteligentes
        riesgo = "BAJO"
        color = "green"
        if avance_pct < 80: 
            riesgo, color = "ALTO", "red"
        elif avance_pct < 90: 
            riesgo, color = "MEDIO", "yellow"

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
        output = io.BytesIO()
        # Usamos pure xlsxwriter para evitar conflictos y corrupción
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # --- DEFINICIÓN DE FORMATOS ---
        
        # Estilos Globales
        header_fmt = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 
            'fg_color': '#002060', 'font_color': '#FFFFFF', 'border': 1, 'align': 'center'
        })
        cell_fmt = workbook.add_format({'border': 1})
        # Currency fmt ahora es para texto alineado a la derecha
        currency_fmt = workbook.add_format({'border': 1, 'align': 'right'})
        percent_fmt = workbook.add_format({'num_format': '0.0%', 'border': 1, 'align': 'center'})
        title_fmt = workbook.add_format({'bold': True, 'size': 14, 'font_color': '#002060'})
        subtitle_fmt = workbook.add_format({'bold': True, 'size': 12, 'font_color': '#002060', 'underline': True})
        
        # Helper function para escribir tablas manualmente
        def write_table_manually(ws, start_row, start_col, df, title=None, currency_cols=None, percent_cols=None):
            current_row = start_row
            if title:
                ws.write(current_row, start_col, title, title_fmt if start_row == 0 else subtitle_fmt)
                current_row += 1
            
            # Encabezados
            headers = df.columns.tolist()
            for i, h in enumerate(headers):
                ws.write(current_row, start_col + i, h, header_fmt)
            current_row += 1
            
            # Datos
            for _, row in df.iterrows():
                for i, val in enumerate(row):
                    fmt = cell_fmt
                    final_val = val
                    
                    if currency_cols and headers[i] in currency_cols:
                        fmt = currency_fmt
                        # FORCE TEXT FORMATTING: S/ 1,234.56
                        if pd.notna(val) and isinstance(val, (int, float)):
                            final_val = f"S/ {val:,.2f}"
                        else:
                            final_val = ""
                            
                    elif percent_cols and headers[i] in percent_cols:
                        fmt = percent_fmt
                        if pd.isna(val): final_val = ""
                    
                    # Handle NaNs generic
                    if pd.isna(final_val):
                        final_val = ""
                        
                    ws.write(current_row, start_col + i, final_val, fmt)
                current_row += 1
            
            # Auto-adjust columns (simple heuristic)
            for i, h in enumerate(headers):
                ws.set_column(start_col + i, start_col + i, max(len(str(h)), 15) + 2)
            
            return current_row + 2 # Retorna siguiente fila disponible (+espacio)

        # ==========================================
        # HOJA 1: REPORTE GENERAL
        # ==========================================
        worksheet_gen = workbook.add_worksheet('Reporte General')
        
        # Data Fetching
        query_gen = "SELECT * FROM ejecucion_financiera WHERE 1=1"
        params_gen = []
        if ano != "Todos":
            query_gen += " AND ano_ejecucion = ?"
            params_gen.append(ano)
        if unidad != "Todas":
            query_gen += " AND unidad_gerencial = ?"
            params_gen.append(unidad)
            
        with engine.connect() as conn:
            df_gen = pd.read_sql(query_gen, conn, params=tuple(params_gen))
            
        # 1.1 KPIs
        data_kpi = {
            'Indicador': ['Total Proyectos', 'PIM Total', 'Certificado Anual', 'Compromiso Anual', 'Devengado Anual', 'Saldo por Ejecutar', '% Avance'],
            'Valor': [
                len(df_gen),
                df_gen['monto_pim'].sum() if 'monto_pim' in df_gen.columns else 0,
                df_gen['monto_certificado'].sum() if 'monto_certificado' in df_gen.columns else 0,
                df_gen['monto_compro_anual'].sum() if 'monto_compro_anual' in df_gen.columns else 0,
                df_gen['monto_total_devengado_anual'].sum() if 'monto_total_devengado_anual' in df_gen.columns else 0,
                0, 0
            ]
        }
        data_kpi['Valor'][5] = data_kpi['Valor'][1] - data_kpi['Valor'][4]
        data_kpi['Valor'][6] = (data_kpi['Valor'][4] / data_kpi['Valor'][1]) if data_kpi['Valor'][1] > 0 else 0
        df_kpi = pd.DataFrame(data_kpi)

        row_ptr = 0
        row_ptr = write_table_manually(worksheet_gen, row_ptr, 1, df_kpi, "RESUMEN EJECUTIVO (KPIs GLOBALES)", 
                                       currency_cols=['Valor'], percent_cols=[]) # 'Valor' mixed type handled poorly by strict check, but fine here
        # Override format for specific cells if needed, but for simplicity let's stick to simple.
        # Actually for 'Valor', we have int, currency, percent. Better to format 'Valor' specifically? 
        # Let's simple write manually for KPI since it's transposed data.
        # Re-writing KPI specifically for better look:
        worksheet_gen.write(1, 1, "Indicador", header_fmt)
        worksheet_gen.write(1, 2, "Valor", header_fmt)
        
        kpi_formats = [cell_fmt, currency_fmt, currency_fmt, currency_fmt, currency_fmt, currency_fmt, percent_fmt]
        for i, (ind, val) in enumerate(zip(data_kpi['Indicador'], data_kpi['Valor'])):
            worksheet_gen.write(2+i, 1, ind, cell_fmt)
            worksheet_gen.write(2+i, 2, val, kpi_formats[i])
        row_ptr = 2 + len(data_kpi['Indicador']) + 2

        # 1.2 Mensual
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'setiembre', 'octubre', 'noviembre', 'diciembre']
        data_mensual = {'Mes': [m.capitalize() for m in meses], 'Compromiso': [], 'Devengado': []}
        for m in meses:
            col_c = f"monto_compro_{m}"
            col_d = f"monto_devengado_{m}"
            data_mensual['Compromiso'].append(df_gen[col_c].sum() if col_c in df_gen.columns else 0)
            data_mensual['Devengado'].append(df_gen[col_d].sum() if col_d in df_gen.columns else 0)
        df_mensual = pd.DataFrame(data_mensual)
        
        row_ptr = write_table_manually(worksheet_gen, row_ptr, 1, df_mensual, "EJECUCIÓN MENSUAL", 
                                       currency_cols=['Compromiso', 'Devengado'])
                                       
        # 1.3 Resumen por Unidad (Reemplazo de Detalle)
        if 'unidad_gerencial' in df_gen.columns and 'ano_ejecucion' in df_gen.columns:
            df_resumen = df_gen.groupby(['unidad_gerencial', 'ano_ejecucion']).agg({
                'monto_pim': 'sum', 'monto_certificado': 'sum', 
                'monto_compro_anual': 'sum', 'monto_total_devengado_anual': 'sum'
            }).reset_index()
            df_resumen.columns = ['Unidad Gerencial', 'Año de Ejecución', 'Monto PIM', 'Monto Certificado', 'Monto Total Comprometido', 'Monto Total de Devengado']
        else:
            df_resumen = pd.DataFrame(columns=['Unidad Gerencial', 'Año de Ejecución', 'Monto PIM', 'Monto Certificado', 'Monto Total Comprometido', 'Monto Total de Devengado'])
            
        row_ptr = write_table_manually(worksheet_gen, row_ptr, 1, df_resumen, "RESUMEN POR UNIDAD Y AÑO", 
                                       currency_cols=['Monto PIM', 'Monto Certificado', 'Monto Total Comprometido', 'Monto Total de Devengado'])


        # ==========================================
        # HOJA 2: ANÁLISIS HISTÓRICO
        # ==========================================
        worksheet_hist = workbook.add_worksheet('Analisis Historico')
        
        query_hist = "SELECT * FROM ejecucion_financiera WHERE 1=1"
        params_hist = []
        if unidad != "Todas":
            query_hist += " AND unidad_gerencial = ?"
            params_hist.append(unidad)
        with engine.connect() as conn:
            df_hist_raw = pd.read_sql(query_hist, conn, params=tuple(params_hist))
            
        # 2.1 Evolución
        df_evolucion = df_hist_raw.groupby('ano_ejecucion').agg({'monto_pim': 'sum', 'monto_total_devengado_anual': 'sum'}).reset_index()
        df_evolucion['% Eficacia'] = (df_evolucion['monto_total_devengado_anual'] / df_evolucion['monto_pim']).fillna(0)
        
        row_ptr = 0
        row_ptr = write_table_manually(worksheet_hist, row_ptr, 1, df_evolucion, "EVOLUCIÓN HISTÓRICA ANUAL", 
                                       currency_cols=['monto_pim', 'monto_total_devengado_anual'], percent_cols=['% Eficacia'])
                                       
        # 2.2 Estacionalidad
        vals_mensuales = []
        total_hist_dev = df_hist_raw['monto_total_devengado_anual'].sum()
        for m in meses:
            col_d = f"monto_devengado_{m}"
            suma_mes = df_hist_raw[col_d].sum() if col_d in df_hist_raw.columns else 0
            pct = (suma_mes / total_hist_dev) if total_hist_dev > 0 else 0
            vals_mensuales.append({'Mes': m.capitalize(), '% Peso Anual': pct})
        df_season = pd.DataFrame(vals_mensuales)
        
        start_row_season = row_ptr
        worksheet_hist.write(start_row_season, 1, "ESTACIONALIDAD DEL GASTO (HEATMAP)", workbook.add_format({'bold': True, 'size': 12, 'font_color': '#002060'}))
        row_ptr += 1
        row_ptr = write_table_manually(worksheet_hist, row_ptr, 1, df_season, None, 
                                       percent_cols=['% Peso Anual'])
        
        # Heatmap
        if len(df_season) > 0:
            season_range = f"C{start_row_season + 3}:C{start_row_season + 2 + len(df_season)}"
            worksheet_hist.conditional_format(season_range, {'type': '3_color_scale', 'min_color': "#F8696B", 'mid_color': "#FFEB84", 'max_color': "#63BE7B"})
        
        # 2.3 Ranking
        if 'unidad_gerencial' in df_hist_raw.columns:
            df_rank = df_hist_raw.groupby('unidad_gerencial').agg({'monto_pim': 'sum', 'monto_total_devengado_anual': 'sum'}).reset_index()
            df_rank['% Eficacia Promedio'] = (df_rank['monto_total_devengado_anual'] / df_rank['monto_pim']).fillna(0)
            df_rank = df_rank.sort_values('% Eficacia Promedio', ascending=False)
            df_rank.columns = ['Unidad Gerencial', 'PIM Histórico', 'Devengado Histórico', '% Eficacia']
            
            start_row_rank = row_ptr
            worksheet_hist.write(start_row_rank, 1, "RANKING DE EFICIENCIA HISTÓRICA", workbook.add_format({'bold': True, 'size': 12, 'font_color': '#002060'}))
            row_ptr += 1
            row_ptr = write_table_manually(worksheet_hist, row_ptr, 1, df_rank, None, 
                                           currency_cols=['PIM Histórico', 'Devengado Histórico'], percent_cols=['% Eficacia'])
            
            if len(df_rank) > 0:
                rank_range = f"E{start_row_rank + 3}:E{start_row_rank + 2 + len(df_rank)}"
                worksheet_hist.conditional_format(rank_range, {'type': 'data_bar', 'bar_color': '#63C384'})


        # ==========================================
        # HOJA 3: PREDICCIÓN
        # ==========================================
        worksheet_pred = workbook.add_worksheet('Prediccion')
        try:
            pred_data = entrenar_y_predecir(unidad_filtro=unidad)
            
            # 3.1 Resumen
            kpi_pred = pred_data['global']
            data_pred_resumen = {
                'Indicador': ['PIM 2025', 'Proyección Cierre (IA)', 'Saldo Presupuestal Estimado', 'Devengado Acumulado a la Fecha'],
                'Monto (S/)': [kpi_pred['pim_total'], kpi_pred['proyeccion_cierre'], kpi_pred['saldo_presupuestal'], kpi_pred['devengado_acumulado']]
            }
            df_pred_resumen = pd.DataFrame(data_pred_resumen)
            row_ptr = 0
            row_ptr = write_table_manually(worksheet_pred, row_ptr, 1, df_pred_resumen, "PROYECCIÓN DE CIERRE 2025 (IA)", 
                                           currency_cols=['Monto (S/)'])
            
            # 3.2 Riesgos
            unidades_pred = pred_data['unidades']
            rows_riesgo = []
            for u in unidades_pred:
                rows_riesgo.append({
                    'Unidad Gerencial': u['unidad'], 'PIM': u['pim'], 'Proyección Cierre': u['proyeccion_cierre'],
                    'Riesgo Detectado': u['riesgo'], '% Avance Proyectado': (u['proyeccion_cierre']/u['pim']) if u['pim'] > 0 else 0
                })
            df_riesgo = pd.DataFrame(rows_riesgo)
            row_ptr = write_table_manually(worksheet_pred, row_ptr, 1, df_riesgo, "ANÁLISIS DE RIESGO POR UNIDAD", 
                                           currency_cols=['PIM', 'Proyección Cierre'], percent_cols=['% Avance Proyectado'])
            
            # 3.3 Curva
            agg_comp, agg_real, agg_pred = [0.0]*12, [0.0]*12, [0.0]*12
            for u in unidades_pred:
                g = u['grafico']
                for i in range(12):
                    agg_comp[i] += g['compromiso'][i] if i < len(g['compromiso']) else 0
                    val_r = g['real'][i] if i < len(g['real']) and g['real'][i] is not None else 0
                    agg_real[i] += val_r
                    agg_pred[i] += g['prediccion_curva'][i] if i < len(g['prediccion_curva']) else 0
            
            meses_labels = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre']
            
            # Logic to filter "Mes Cerrado" for Past Months
            from datetime import datetime
            current_month_index = datetime.now().month - 1 # 0-indexed (Jan=0, Dec=11)
            
            # Apply filter: Past months -> "Mes Cerrado", Current/Future -> Value
            final_agg_pred = []
            for i in range(12):
                if i < current_month_index:
                    final_agg_pred.append("Mes Cerrado")
                else:
                    final_agg_pred.append(agg_pred[i])

            data_curva = {'Mes': meses_labels, 'Compromiso (Plan)': agg_comp, 'Ejecutado Real': agg_real, 'Proyección IA': final_agg_pred}
            df_curva = pd.DataFrame(data_curva)
            row_ptr = write_table_manually(worksheet_pred, row_ptr, 1, df_curva, "CURVA DE PROYECCIÓN MENSUAL (AGREGADO)", 
                                           currency_cols=['Compromiso (Plan)', 'Ejecutado Real', 'Proyección IA'])
                                           
        except Exception as e:
            traceback.print_exc()
            worksheet_pred.write(1, 1, f"Error generando predicción: {str(e)}")

        workbook.close()
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=Reporte_PRONIED_{ano}_{unidad}.xlsx"}
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


# --- 7. CHATBOT INTELIGENTE LLM (GPT-4o-mini) ---

class ChatMessage(BaseModel):
    message: str

@app.post("/api/chatbot/chat")
async def chat_with_assistant(chat_req: ChatMessage, current_user: str = Depends(get_current_user)):
    try:
        # 1. Obtener la FOTO ACTUAL de las predicciones de Machine Learning (Backend)
        # Usamos flag_alerta=False para no gatillar correos por accidente
        context_data = entrenar_y_predecir("Todas", flag_alerta=False)
        
        # 2. Filtrar únicamente la información ejecutiva clave para ahorrar tokens y mejorar precisión
        contexto_ejecutivo = {
            "Global": context_data.get('global', {}),
            "Mes_Actual": context_data.get('kpi_mes_actual', {}),
            "Unidades": []
        }
        
        for u in context_data.get('unidades', []):
            historico = []
            if 'grafico' in u:
                labels = u['grafico'].get('labels', [])
                real_data = u['grafico'].get('real', [])
                compro_data = u['grafico'].get('compromiso', [])
                
                for idx, mes in enumerate(labels):
                    if idx < len(real_data) and real_data[idx] is not None:
                        historico.append(f"{mes}: Meta={round(compro_data[idx],2)} Logro={round(real_data[idx],2)}")
                        
            contexto_ejecutivo['Unidades'].append({
                "unidad": u['unidad'],
                "riesgo_estado": u['riesgo'], # Alto, Medio, Bajo
                "presupuesto_pim": u['pim'],
                "gasto_proyectado_cierre": u['proyeccion_cierre'],
                "ejecucion_mensual_historica": " | ".join(historico)
            })
            
        # 2.5 Añadir historial de años anteriores completos (Pre-calculado para evitar alucinaciones)
        historico_anios = {}
        df_hist = df_global[df_global['ano_de_ejecución'] < 2026]
        
        for anio_val, df_anio in df_hist.groupby('ano_de_ejecución'):
            anio = str(int(anio_val))
            pim_global = round(df_anio['MONTO_PIM'].sum() / 1000000, 2)
            
            logro_global = 0
            for mes in ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']:
                col = f"MONTO_DEVENGADO_{mes}"
                if col in df_anio.columns:
                    logro_global += df_anio[col].sum()
            logro_global = round(logro_global / 1000000, 2)
            saldo_global = round(pim_global - logro_global, 2)
            
            historico_anios[anio] = {
                "Resumen_Global_Institucional": f"PIM Total: {pim_global}M | Gasto Real (Logro): {logro_global}M | Saldo Final (Sobrante): {saldo_global}M",
                "Detalle_Unidades": {}
            }
            
            for _, row in df_anio.iterrows():
                unidad = row['unidad_gerencial']
                pim_u = round(row.get('MONTO_PIM', 0) / 1000000, 2)
                logro_u = 0
                detalles_meses = []
                for mes in ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']:
                    col_compro = f"MONTO_COMPRO_{mes}"
                    col_dev = f"MONTO_DEVENGADO_{mes}"
                    if col_compro in row and col_dev in row:
                        compro = round(row[col_compro] / 1000000, 2)
                        dev = round(row[col_dev] / 1000000, 2)
                        logro_u += dev
                        if compro > 0 or dev > 0:
                            detalles_meses.append(f"{mes[:3]}: Meta={compro}M Logro={dev}M")
                
                saldo_u = round(pim_u - logro_u, 2)
                historico_anios[anio]["Detalle_Unidades"][unidad] = f"[PIM: {pim_u}M | Logro: {round(logro_u, 2)}M | Saldo: {saldo_u}M] -> Meses: " + " | ".join(detalles_meses)
            
        contexto_ejecutivo["Historial_Anos_Anteriores"] = historico_anios
        
        context_str = json.dumps(contexto_ejecutivo, indent=2)

        # 3. Prompting Dinámico con RAG Automático
        prompt_del_sistema = f"""
        Eres el Asistente Financiero Ejecutivo del PRONIED (Programa Nacional de Infraestructura Educativa del Perú).
        Tu trabajo es responder las dudas de directores usando de manera ESTRICTA, PRECISA y EXCLUSIVA los datos de ejecución y predicciones.
        
        INSTRUCCIONES CLAVES Y GLOSARIO:
        1. "AÑO ACTUAL": Todos los datos que estás viendo en la sección 'Global' y 'Unidades' corresponden al año fiscal 2026.
        2. "META": La meta financiera anual es el "PIM".
        3. "CUMPLIMIENTO": Para saber si "llegarán a la meta", compara "gasto_proyectado_cierre" versus "presupuesto_pim". Si es casi igual, llegarán; si es mucho menor, no llegarán (Riesgo Alto).
        4. "MESES HISTÓRICOS 2026": La data de meses pasados del 2026 está en "ejecucion_mensual_historica".
        5. "AÑOS CERRADOS": Si el usuario pregunta por años anteriores (ej. 2024, 2025), utiliza obligatoriamente la data provista en la sección "Historial_Anos_Anteriores", donde se detalla la Meta y el Logro mensual de cada unidad en ese año.
        6. SOLO responde basado en el bloque de DATOS ACTUALES proporcionado abajo.
        7. No inventes cifras. Puedes formatear los números a millones (ej. 150M) para lectura humana, pero mantén la veracidad matemática.
        8. Responde de forma cálida, ejecutiva y directa.
        
        [DATOS DE EJECUCIÓN (AÑO 2026 + HISTORIAL) Y PREDICCIONES]:
        {context_str}
        """

        # 4. Invocación a OpenAI usando tu API Key
        import os
        api_key = os.getenv("OPENAI_API_KEY", "TU_API_KEY_AQUI")
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini", # El modelo ágil, rápido y perfecto que pediste
            messages=[
                {"role": "system", "content": prompt_del_sistema},
                {"role": "user", "content": chat_req.message}
            ],
            temperature=0.1 # Temperatura súper baja para que nunca "allucine" datos financieros falsos
        )
        
        respuesta_ia = response.choices[0].message.content
        return {"response": respuesta_ia}
        
    except Exception as e:
        print(f"Error en ChatGPT Backend: {str(e)}")
        raise HTTPException(status_code=500, detail="Error conectando con el servicio de Inteligencia Artificial")

# --- CONFIGURACIÓN DE REPORTES (HU011) ---
class ConfigReporte(BaseModel):
    dia_semana: str
    hora: str
    minuto: str
    activo: bool

@app.get("/api/config-reportes")
async def get_config_reportes(current_user: str = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            config = conn.execute(text(f"SELECT TOP 1 dia_semana, hora, minuto, activo FROM configuracion_reportes WHERE username = '{current_user}'")).fetchone()
            if config:
                return {
                    "dia_semana": config[0],
                    "hora": config[1],
                    "minuto": config[2],
                    "activo": bool(config[3])
                }
            return {"dia_semana": "fri", "hora": "17", "minuto": "00", "activo": True}
    except Exception as e:
        print(f"Error obteniendo configuración: {e}")
        raise HTTPException(status_code=500, detail="Error en base de datos")

@app.post("/api/config-reportes")
async def update_config_reportes(config: ConfigReporte, current_user: str = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            # UPSERT en BD
            existing = conn.execute(text(f"SELECT id FROM configuracion_reportes WHERE username = '{current_user}'")).fetchone()
            if existing:
                conn.execute(text(f'''
                    UPDATE configuracion_reportes 
                    SET dia_semana = '{config.dia_semana}', 
                        hora = '{config.hora}', 
                        minuto = '{config.minuto}', 
                        activo = {1 if config.activo else 0}
                    WHERE username = '{current_user}'
                '''))
            else:
                conn.execute(text(f'''
                    INSERT INTO configuracion_reportes (username, dia_semana, hora, minuto, activo)
                    VALUES ('{current_user}', '{config.dia_semana}', '{config.hora}', '{config.minuto}', {1 if config.activo else 0})
                '''))
            conn.commit()

            # Sincronizar campo visual envio_correo en la tabla usuarios
            if config.activo:
                conn.execute(text(f"UPDATE usuarios SET envio_correo = 1 WHERE username = '{current_user}'"))
                conn.commit()

        # Actualizar Scheduler en memoria
        job_id = f"reporte_semanal_{current_user}"
        if config.activo:
            scheduler.add_job(
                enviar_resumen_semanal_h011, 
                'cron', 
                day_of_week=config.dia_semana, 
                hour=int(config.hora), 
                minute=int(config.minuto), 
                id=job_id, 
                replace_existing=True,
                args=[current_user]
            )
            print(f"✅ Scheduler actualizado ({current_user}): {config.dia_semana} a las {config.hora}:{config.minuto}")
        else:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                print(f"ℹ️ Scheduler de Resumen Semanal desactivado ({current_user}).")
                
        return {"message": "Configuración actualizada correctamente"}
    except Exception as e:
        print(f"Error actualizando configuración: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar configuración")

# --- CONFIGURACIÓN DE ALERTAS (HU004) ---
@app.get("/api/config-alertas")
async def get_config_alertas(current_user: str = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            config = conn.execute(text(f"SELECT TOP 1 dia_semana, hora, minuto, activo FROM configuracion_alertas WHERE username = '{current_user}'")).fetchone()
            if config:
                return {
                    "dia_semana": config[0],
                    "hora": config[1],
                    "minuto": config[2],
                    "activo": bool(config[3])
                }
            return {"dia_semana": "*", "hora": "09", "minuto": "39", "activo": True}
    except Exception as e:
        print(f"Error obteniendo configuración alertas: {e}")
        raise HTTPException(status_code=500, detail="Error en base de datos")

@app.post("/api/config-alertas")
async def update_config_alertas(config: ConfigReporte, current_user: str = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            # UPSERT en BD
            existing = conn.execute(text(f"SELECT id FROM configuracion_alertas WHERE username = '{current_user}'")).fetchone()
            if existing:
                conn.execute(text(f'''
                    UPDATE configuracion_alertas 
                    SET dia_semana = '{config.dia_semana}', 
                        hora = '{config.hora}', 
                        minuto = '{config.minuto}', 
                        activo = {1 if config.activo else 0}
                    WHERE username = '{current_user}'
                '''))
            else:
                conn.execute(text(f'''
                    INSERT INTO configuracion_alertas (username, dia_semana, hora, minuto, activo)
                    VALUES ('{current_user}', '{config.dia_semana}', '{config.hora}', '{config.minuto}', {1 if config.activo else 0})
                '''))
            conn.commit()
            
            # Sincronizar campo visual envio_correo en la tabla usuarios
            if config.activo:
                conn.execute(text(f"UPDATE usuarios SET envio_correo = 1 WHERE username = '{current_user}'"))
                conn.commit()

        # Actualizar Scheduler en memoria
        job_id = f"alerta_retrasos_{current_user}"
        if config.activo:
            scheduler.add_job(
                ejecutar_alertas_h004, 
                'cron', 
                day_of_week=config.dia_semana, 
                hour=int(config.hora), 
                minute=int(config.minuto), 
                id=job_id, 
                replace_existing=True,
                args=[current_user]
            )
            print(f"✅ Scheduler alertas actualizado ({current_user}): {config.dia_semana} a las {config.hora}:{config.minuto}")
        else:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                print(f"ℹ️ Scheduler de Alertas desactivado ({current_user}).")
                
        return {"message": "Configuración de alertas actualizada correctamente"}
    except Exception as e:
        print(f"Error actualizando configuración alertas: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar configuración")

class UserCreate(BaseModel):
    username: str
    password: str
    nombres: str
    apellidos: str
    correo: str
    dni: str
    administrador: int = 0
    envio_correo: int = 0

class UserUpdate(BaseModel):
    username: str
    nombres: str
    apellidos: str
    correo: str
    dni: str
    administrador: int
    envio_correo: int
    activo: int
    password: str = None

@app.get("/api/usuarios")
async def get_usuarios(current_user: str = Depends(get_current_user)):
    engine = create_engine_connection()
    with engine.connect() as conn:
        # Check admin
        df_admin = pd.read_sql(f"SELECT administrador FROM usuarios WHERE username = '{current_user}'", conn)
        if df_admin.empty or df_admin.iloc[0]['administrador'] != 1:
            raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
            
        df = pd.read_sql("SELECT id, username, nombres, apellidos, correo, dni, envio_correo, administrador, activo FROM usuarios", conn)
    return df.to_dict(orient='records')

@app.post("/api/usuarios")
async def create_usuario(user: UserCreate, current_user: str = Depends(get_current_user)):
    engine = create_engine_connection()
    with engine.begin() as conn:
        df_admin = pd.read_sql(f"SELECT administrador FROM usuarios WHERE username = '{current_user}'", conn)
        if df_admin.empty or df_admin.iloc[0]['administrador'] != 1:
            raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
            
        df_exist = pd.read_sql(f"SELECT id FROM usuarios WHERE username = '{user.username}' OR correo = '{user.correo}' OR dni = '{user.dni}'", conn)
        if not df_exist.empty:
            raise HTTPException(status_code=400, detail="El nombre de usuario, correo o DNI ya existe")
            
        hashed_pw = get_password_hash(user.password)
        query = text("""
            INSERT INTO usuarios (username, hashed_password, nombres, apellidos, correo, dni, envio_correo, dia_envio_semanal, administrador, activo)
            VALUES (:username, :hashed_pw, :nombres, :apellidos, :correo, :dni, :envio_correo, 5, :admin, 1)
        """)
        conn.execute(query, {
            "username": user.username, "hashed_pw": hashed_pw, "nombres": user.nombres, 
            "apellidos": user.apellidos, "correo": user.correo, "dni": user.dni,
            "envio_correo": user.envio_correo, "admin": user.administrador
        })
    return {"message": "Usuario creado exitosamente"}

@app.put("/api/usuarios/{user_id}")
async def update_usuario(user_id: int, user: UserUpdate, current_user: str = Depends(get_current_user)):
    engine = create_engine_connection()
    with engine.begin() as conn:
        df_admin = pd.read_sql(f"SELECT administrador FROM usuarios WHERE username = '{current_user}'", conn)
        if df_admin.empty or df_admin.iloc[0]['administrador'] != 1:
            raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
            
        df_exist = pd.read_sql(f"SELECT id FROM usuarios WHERE (username = '{user.username}' OR correo = '{user.correo}' OR dni = '{user.dni}') AND id != {user_id}", conn)
        if not df_exist.empty:
            raise HTTPException(status_code=400, detail="El nombre de usuario, correo o DNI ya está en uso por otro usuario")
            
        if user.password:
            hashed_pw = get_password_hash(user.password)
            query = text("""
                UPDATE usuarios SET username=:username, hashed_password=:hashed_pw, nombres=:nombres, apellidos=:apellidos, 
                correo=:correo, dni=:dni, envio_correo=:envio_correo, administrador=:admin, activo=:activo
                WHERE id=:id
            """)
            conn.execute(query, {
                "username": user.username, "hashed_pw": hashed_pw, "nombres": user.nombres, 
                "apellidos": user.apellidos, "correo": user.correo, "dni": user.dni,
                "envio_correo": user.envio_correo, "admin": user.administrador, "activo": user.activo, "id": user_id
            })
        else:
            query = text("""
                UPDATE usuarios SET username=:username, nombres=:nombres, apellidos=:apellidos, 
                correo=:correo, dni=:dni, envio_correo=:envio_correo, administrador=:admin, activo=:activo
                WHERE id=:id
            """)
            conn.execute(query, {
                "username": user.username, "nombres": user.nombres, 
                "apellidos": user.apellidos, "correo": user.correo, "dni": user.dni,
                "envio_correo": user.envio_correo, "admin": user.administrador, "activo": user.activo, "id": user_id
            })
    return {"message": "Usuario actualizado exitosamente"}

@app.delete("/api/usuarios/{user_id}")
async def delete_usuario(user_id: int, current_user: str = Depends(get_current_user)):
    engine = create_engine_connection()
    with engine.begin() as conn:
        df_admin = pd.read_sql(f"SELECT administrador FROM usuarios WHERE username = '{current_user}'", conn)
        if df_admin.empty or df_admin.iloc[0]['administrador'] != 1:
            raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
            
        query = text("UPDATE usuarios SET activo=0 WHERE id=:id")
        conn.execute(query, {"id": user_id})
    return {"message": "Usuario desactivado exitosamente"}
