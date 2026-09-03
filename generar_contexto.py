import os

# Configuración de rutas
DIRECTORIO_MODULOS = "modules"
ARCHIVO_SALIDA = "todo_el_proyecto.txt"

def consolidar_proyecto():
    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as outfile:
        # Incluir app.py principal si se desea
        if os.path.exists("app.py"):
        # Escribe el contenido del archivo principal
            outfile.write("=== ARCHIVO: app.py ===\n\n")
            with open("app.py", "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
            outfile.write("\n\n" + "="*50 + "\n\n")

        # Recorrer la carpeta de módulos
        if os.path.exists(DIRECTORIO_MODULOS):
            for filename in sorted(os.listdir(DIRECTORIO_MODULOS)):
                if filename.endswith(".py"):
                    filepath = os.path.join(DIRECTORIO_MODULOS, filename)
                    outfile.write(f"=== MÓDULO: {filename} ===\n\n")
                    with open(filepath, "r", encoding="utf-8") as infile:
                        outfile.write(infile.read())
                    outfile.write("\n\n" + "="*50 + "\n\n")
                    
    print(f"¡Proyecto consolidado con éxito en {ARCHIVO_SALIDA}!")

if __name__ == "__main__":
    consolidar_proyecto()