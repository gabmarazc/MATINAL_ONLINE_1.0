import os

ARCHIVO_SALIDA = "todo_el_proyecto.txt"

ARCHIVOS_RAIZ = [
    "app.py",
    "config.py",
    "contexto.py",
    "data_loader.py",
    "generar_objetivos_manuales.py",
    "requirements.txt",
    "runtime.txt",
    ".gitignore",
    "iniciar_sistema.bat"
]

DIRECTORIOS = [
    ("modules", [".py"]),
    ("project_docs", [".md"])
]


def escribir_separador(outfile):
    outfile.write("\n\n" + "=" * 100 + "\n\n")


def agregar_archivo(outfile, filepath, categoria):

    try:

        outfile.write(
            f"=== {categoria}: {filepath} ===\n\n"
        )

        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as infile:

            outfile.write(infile.read())

        escribir_separador(outfile)

    except Exception as e:

        outfile.write(
            f"ERROR LEYENDO {filepath}: {e}\n"
        )

        escribir_separador(outfile)


def agregar_archivos_raiz(outfile):

    outfile.write(
        "###############################\n"
    )

    outfile.write(
        "# ARCHIVOS PRINCIPALES\n"
    )

    outfile.write(
        "###############################\n\n"
    )

    for archivo in ARCHIVOS_RAIZ:

        if os.path.exists(archivo):

            agregar_archivo(
                outfile,
                archivo,
                "ARCHIVO"
            )


def agregar_directorio(
    outfile,
    directorio,
    extensiones
):

    if not os.path.exists(directorio):
        return

    outfile.write(
        f"\n###############################\n"
    )

    outfile.write(
        f"# DIRECTORIO: {directorio}\n"
    )

    outfile.write(
        f"###############################\n\n"
    )

    archivos = sorted(os.listdir(directorio))

    for archivo in archivos:

        ruta = os.path.join(
            directorio,
            archivo
        )

        if not os.path.isfile(ruta):
            continue

        if any(
            archivo.endswith(ext)
            for ext in extensiones
        ):
            agregar_archivo(
                outfile,
                ruta,
                directorio.upper()
            )


def consolidar_proyecto():

    with open(
        ARCHIVO_SALIDA,
        "w",
        encoding="utf-8"
    ) as outfile:

        outfile.write(
            "MATINAL - CONTEXTO COMPLETO DEL PROYECTO\n"
        )

        outfile.write(
            "VERSIÓN CONSOLIDADA PARA IA\n"
        )

        outfile.write(
            "=" * 100 + "\n\n"
        )

        agregar_archivos_raiz(outfile)

        for directorio, extensiones in DIRECTORIOS:

            agregar_directorio(
                outfile,
                directorio,
                extensiones
            )

    print(
        f"Proyecto consolidado correctamente en: {ARCHIVO_SALIDA}"
    )


if __name__ == "__main__":
    consolidar_proyecto()