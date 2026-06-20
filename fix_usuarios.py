import sys

with open('usuarios.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos la línea donde empieza el error
target_start = content.find('const res = new Array(labels.length).fill(0);')

if target_start == -1:
    print("No se encontró el error.")
    sys.exit(1)

# Encontramos la línea exacta retrocediendo hasta el salto de línea anterior
line_start = content.rfind('\n', 0, target_start)

# El código que queremos mantener
clean_content = content[:line_start]

# Lo que vamos a añadir
replacement = """
                if (res.ok) {
                    alert(id ? "Usuario actualizado exitosamente." : "Usuario creado exitosamente.");
                    closeUserModal();
                    loadUsers();
                } else {
                    let err = {};
                    try { err = await res.json(); } catch(e){}
                    alert("Error: " + (err.detail || "No se pudo guardar el usuario."));
                }
            } catch (e) {
                console.error("Error saving user", e);
                alert("Error de conexión al guardar el usuario.");
            }
        }

        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('collapsed');
        }

        // --- INICIALIZACIÓN ---
        checkAdminAccess();
        loadUsers();
    </script>
</body>
</html>
"""

final_content = clean_content + replacement

with open('usuarios.html', 'w', encoding='utf-8') as f:
    f.write(final_content)

print("usuarios.html corregido exitosamente.")
