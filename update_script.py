import os

files_to_update = [
    "reporte_general.html",
    "analisis_historico.html",
    "reporte_ejecutivo.html"
]

nav_item = """
                    <li class="nav-item">
                        <a href="#" onclick="openConfigModal()" class="nav-link">
                            <i class="ph ph-gear"></i>
                            <span class="link-text">Configuración</span>
                        </a>
                        <span class="tooltip">Configuración</span>
                    </li>
"""

modal_code = """
    <!-- --- VENTANA MODAL: CONFIGURACIÓN REPORTE SEMANAL --- -->
    <div id="configModal" class="modal opacity-0 pointer-events-none fixed w-full h-full top-0 left-0 flex items-center justify-center z-50">
        <div class="modal-overlay absolute w-full h-full bg-gray-900 opacity-50" onclick="closeConfigModal()"></div>
        <div class="modal-container bg-white w-11/12 md:max-w-md mx-auto rounded shadow-lg z-50 overflow-y-auto transform transition-all scale-95">
            <div class="modal-content py-4 text-left px-6">
                <!-- Título Modal -->
                <div class="flex justify-between items-center pb-3 border-b">
                    <div>
                        <p class="text-xl font-bold text-gray-800"><i class="ph-bold ph-envelope-simple text-indigo-600"></i> Reporte Semanal</p>
                    </div>
                    <button onclick="closeConfigModal()" class="cursor-pointer z-50 text-gray-500 hover:text-red-500 transition">
                        <i class="fa-solid fa-times text-xl"></i>
                    </button>
                </div>

                <!-- Cuerpo -->
                <div class="my-5 space-y-4">
                    <p class="text-sm text-gray-600">Configura cuándo deseas enviar automáticamente el resumen semanal (HU011).</p>
                    
                    <div class="flex items-center gap-2 mb-4 bg-gray-50 p-3 rounded">
                        <input type="checkbox" id="configActivo" class="w-5 h-5 text-indigo-600 rounded cursor-pointer">
                        <label for="configActivo" class="font-bold text-gray-700 cursor-pointer">Activar envío automático</label>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Día de la semana</label>
                        <select id="configDia" class="w-full bg-white border border-gray-300 text-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 shadow-sm cursor-pointer">
                            <option value="mon">Lunes</option>
                            <option value="tue">Martes</option>
                            <option value="wed">Miércoles</option>
                            <option value="thu">Jueves</option>
                            <option value="fri">Viernes</option>
                            <option value="sat">Sábado</option>
                            <option value="sun">Domingo</option>
                        </select>
                    </div>
                    <div class="flex gap-4">
                        <div class="w-1/2">
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Hora (24h)</label>
                            <select id="configHora" class="w-full bg-white border border-gray-300 text-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 shadow-sm cursor-pointer">
                            </select>
                        </div>
                        <div class="w-1/2">
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Minutos</label>
                            <select id="configMinuto" class="w-full bg-white border border-gray-300 text-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 shadow-sm cursor-pointer">
                                <option value="00">00</option>
                                <option value="15">15</option>
                                <option value="30">30</option>
                                <option value="45">45</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Footer Modal -->
                <div class="flex justify-end pt-4 border-t gap-2">
                    <button onclick="closeConfigModal()" class="px-5 py-2 bg-gray-200 rounded-lg text-gray-700 hover:bg-gray-300 font-medium transition text-sm">Cancelar</button>
                    <button onclick="saveConfig()" class="px-5 py-2 bg-indigo-600 rounded-lg text-white hover:bg-indigo-700 font-medium transition shadow text-sm flex items-center gap-2"><i class="fa-solid fa-save"></i> Guardar</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // --- LÓGICA DE CONFIGURACIÓN (HU011) ---
        async function openConfigModal() {
            const selectHora = document.getElementById('configHora');
            if (selectHora.options.length === 0) {
                for (let i = 0; i < 24; i++) {
                    const h = i.toString().padStart(2, '0');
                    selectHora.add(new Option(h + ":00", h));
                }
            }

            try {
                const token = localStorage.getItem('pronied_token');
                const res = await fetch('/api/config-reportes', {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('configDia').value = data.dia_semana;
                    document.getElementById('configHora').value = data.hora;
                    
                    let minSelect = document.getElementById('configMinuto');
                    let found = Array.from(minSelect.options).some(o => o.value === data.minuto);
                    if(!found) minSelect.add(new Option(data.minuto, data.minuto));
                    minSelect.value = data.minuto;
                    
                    document.getElementById('configActivo').checked = data.activo;
                }
            } catch(e) {
                console.error("Error cargando config", e);
            }

            const modal = document.getElementById('configModal');
            document.body.classList.add('modal-active');
            modal.classList.remove('opacity-0', 'pointer-events-none');
            modal.querySelector('.modal-container').classList.remove('scale-95');
            modal.querySelector('.modal-container').classList.add('scale-100');
        }

        function closeConfigModal() {
            const modal = document.getElementById('configModal');
            document.body.classList.remove('modal-active');
            modal.classList.add('opacity-0', 'pointer-events-none');
            modal.querySelector('.modal-container').classList.remove('scale-100');
            modal.querySelector('.modal-container').classList.add('scale-95');
        }

        async function saveConfig() {
            const payload = {
                dia_semana: document.getElementById('configDia').value,
                hora: document.getElementById('configHora').value,
                minuto: document.getElementById('configMinuto').value,
                activo: document.getElementById('configActivo').checked
            };

            try {
                const token = localStorage.getItem('pronied_token');
                const res = await fetch('/api/config-reportes', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(payload)
                });
                
                if (res.ok) {
                    alert("¡Configuración guardada! El resumen semanal se enviará automáticamente según el horario programado.");
                    closeConfigModal();
                } else {
                    alert("Error guardando la configuración.");
                }
            } catch (e) {
                console.error(e);
                alert("Error de conexión con el servidor.");
            }
        }
    </script>
</body>
"""

for file in files_to_update:
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
    
    modified = False
    
    # 1. Add Nav Item if missing
    if "openConfigModal()" not in content:
        logout_idx = content.find('<a href="#" onclick="logout()"')
        if logout_idx != -1:
            # find the <li before the logout
            li_idx = content.rfind('<li', 0, logout_idx)
            content = content[:li_idx] + nav_item + content[li_idx:]
            modified = True
            print(f"Added Nav Item to {file}")

    # 2. Add Modal if missing
    if "VENTANA MODAL: CONFIGURACIÓN REPORTE SEMANAL" not in content:
        body_idx = content.rfind('</body>')
        if body_idx != -1:
            content = content[:body_idx] + modal_code + content[body_idx + 7:]
            modified = True
            print(f"Added Modal to {file}")

    # 3. Add FontAwesome and CSS if missing
    if "fa-solid fa-times" in content and "font-awesome" not in content:
        head_idx = content.find('</style>')
        if head_idx != -1:
            # Add before </style> for CSS and before <style> for FontAwesome
            style_start = content.rfind('<style>', 0, head_idx)
            
            css = ".modal { transition: opacity 0.25s ease; }\n        body.modal-active { overflow: hidden !important; }\n        "
            fa_link = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">\n    '
            
            content = content[:style_start] + fa_link + content[style_start:style_start+7] + "\n        " + css + content[style_start+7:]
            modified = True
            print(f"Added FA/CSS to {file}")
            
    if modified:
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved {file}")
