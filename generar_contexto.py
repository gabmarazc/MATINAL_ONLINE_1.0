import os
import glob

# Extensiones de archivos de código, configuración y dependencias que forman parte del proyecto
extensiones_validas = (".py", ".toml", ".txt", ".env", ".json")

# Carpetas o archivos del sistema/entorno que debemos ignorar para no sobrecargar el contexto
elementos_excluidos = {"venv", ".git", "__pycache__", ".streamlit", "todo_el_proyecto.txt"}

nombre_salida = "todo_el_proyecto.txt"

with open(nombre_salida, "w", encoding="utf-8") as outfile:
    outfile.write("=== CONTEXTO COMPLETO DEL PROYECTO: SISTEMA MATINAL 2.0 ===\n")
    
    # Recorrer de forma recursiva toda la estructura desde la raíz
    for ruta in glob.glob("**/*.*", recursive=True):
        partes_ruta = os.path.normpath(ruta).split(os.sep)
        
        # Omitir si pertenece a una carpeta excluida
        if any(exc in partes_ruta for exc in elementos_excluidos):
            continue
            
        # Filtrar por extensiones válidas
        if ruta.endswith(extensiones_validas):
            outfile.write(f"\n\n{'='*50}\n")
            outfile.write(f"ARCHIVO: {ruta}\n")
            outfile.write(f"{'='*50}\n\n")
            try:
                with open(ruta, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read())
            except Exception as e:
                outfile.write(f"[No se pudo leer el archivo: {e}]")

print(f"¡Listo! Se ha generado el archivo '{nombre_salida}' en la raíz con todo el código y la estructura actualizados.")