import re

# Lee el modal de dasboard_frontend.html
with open('dasboard_frontend.html', 'r', encoding='utf-8') as f:
    dashboard = f.read()

# Extraer HTML del modal
match_html = re.search(r'(<!-- --- VENTANA MODAL: CONFIGURACIÓN REPORTE SEMANAL --- -->.*?</div>\s*</div>\s*</div>)', dashboard, re.DOTALL)
if match_html:
    modal_html = match_html.group(1)
else:
    print("No se encontró HTML del modal")

# Extraer JS del modal
match_js = re.search(r'(// --- 4\. LÓGICA DE CONFIGURACIÓN.*?async function saveConfig\(\) \{.*?\}\s*\}\s*catch.*?\}\s*\})', dashboard, re.DOTALL)
if match_js:
    modal_js = match_js.group(1)
else:
    print("No se encontró JS del modal")

if match_html and match_js:
    for filename in ['usuarios.html', 'analisis_historico.html', 'importacion.html']:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar si ya tiene el modal
            if 'id="configModal"' not in content:
                print(f"Parchando {filename}")
                # Insertar HTML antes de <script>
                content = content.replace('<script>', f'{modal_html}\n\n    <script>', 1)
                
                # Insertar JS antes de </script>
                content = content.replace('</script>\n</body>', f'\n{modal_js}\n    </script>\n</body>')
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
        except Exception as e:
            print(f"Error procesando {filename}: {e}")
