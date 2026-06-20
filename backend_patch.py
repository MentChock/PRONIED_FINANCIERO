import re

with open("dasboard_backend.py", "r") as f:
    content = f.read()

# 1. Update setup_database_triggers to include the new table
new_setup = """
            # 4. Crear tabla de configuración de reportes si no existe
            conn.execute(text('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='configuracion_reportes' AND xtype='U')
                CREATE TABLE configuracion_reportes (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    dia_semana VARCHAR(10) NOT NULL,
                    hora VARCHAR(2) NOT NULL,
                    minuto VARCHAR(2) NOT NULL,
                    activo BIT NOT NULL
                )
            '''))
            conn.commit()

            # Insertar configuración por defecto (Viernes 17:00) si está vacía
            conn.execute(text('''
                IF NOT EXISTS (SELECT * FROM configuracion_reportes)
                INSERT INTO configuracion_reportes (dia_semana, hora, minuto, activo) 
                VALUES ('fri', '17', '00', 1)
            '''))
            conn.commit()
            
            print("✅ Triggers y tabla 'control_cambios' configurados correctamente.")
"""
content = content.replace('            print("✅ Triggers y tabla \'control_cambios\' configurados correctamente.")', new_setup)


# 2. Update startup_event to read from DB and schedule with an ID
startup_old = """    # HU011 funciona como un "Scheduler" formal (Cron)
    # Ejecuta el resumen semanal todos los viernes a las 17:00
    scheduler.add_job(enviar_resumen_semanal_h011, 'cron', day_of_week='fri', hour=17, minute=0)"""

startup_new = """    # HU011 funciona como un "Scheduler" formal (Cron)
    try:
        with engine.connect() as conn:
            config = conn.execute(text("SELECT TOP 1 dia_semana, hora, minuto, activo FROM configuracion_reportes")).fetchone()
            if config and config[3]: # si activo == 1
                scheduler.add_job(
                    enviar_resumen_semanal_h011, 
                    'cron', 
                    day_of_week=config[0], 
                    hour=int(config[1]), 
                    minute=int(config[2]), 
                    id="reporte_semanal", 
                    replace_existing=True
                )
                print(f"✅ HU011 programada para: {config[0]} a las {config[1]}:{config[2]}")
            else:
                print("ℹ️ HU011 (Resumen Semanal) está desactivado en la configuración.")
    except Exception as e:
        print(f"⚠️ Error cargando configuración de reportes: {e}")"""

content = content.replace(startup_old, startup_new)

# 3. Add the Pydantic model and Endpoints at the end of the file
endpoints = """
# --- CONFIGURACIÓN DE REPORTES (HU011) ---
class ConfigReporte(BaseModel):
    dia_semana: str
    hora: str
    minuto: str
    activo: bool

@app.get("/api/config-reportes")
async def get_config_reportes():
    try:
        with engine.connect() as conn:
            config = conn.execute(text("SELECT TOP 1 dia_semana, hora, minuto, activo FROM configuracion_reportes")).fetchone()
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
async def update_config_reportes(config: ConfigReporte):
    try:
        with engine.connect() as conn:
            # Actualizar en BD
            conn.execute(text(f'''
                UPDATE configuracion_reportes 
                SET dia_semana = '{config.dia_semana}', 
                    hora = '{config.hora}', 
                    minuto = '{config.minuto}', 
                    activo = {1 if config.activo else 0}
            '''))
            conn.commit()
            
        # Actualizar Scheduler en memoria
        if config.activo:
            scheduler.add_job(
                enviar_resumen_semanal_h011, 
                'cron', 
                day_of_week=config.dia_semana, 
                hour=int(config.hora), 
                minute=int(config.minuto), 
                id="reporte_semanal", 
                replace_existing=True
            )
            print(f"✅ Scheduler actualizado: {config.dia_semana} a las {config.hora}:{config.minuto}")
        else:
            if scheduler.get_job("reporte_semanal"):
                scheduler.remove_job("reporte_semanal")
                print("ℹ️ Scheduler de Resumen Semanal desactivado.")
                
        return {"message": "Configuración actualizada correctamente"}
    except Exception as e:
        print(f"Error actualizando configuración: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar configuración")
"""

with open("dasboard_backend.py", "w") as f:
    f.write(content + endpoints)
