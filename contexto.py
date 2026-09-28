# contexto.py

from pathlib import Path

# ==========================================================
# CONFIGURACION
# ==========================================================

ROOT = Path(".")

PROJECT_DOCS = ROOT / "project_docs"

ARCHIVOS_RAIZ = [
    "app.py",
    "config.py",
    "data_loader.py",
    "generar_objetivos_manuales.py",
    "requirements.txt",
    "runtime.txt",
    ".gitignore",
    "iniciar_sistema.bat",
]

DOCS_PRIORITARIOS = [
    "ARQUITECTURA.md",
    "ESTADO_ACTUAL.md",
    "ROADMAP.md",
    "DECISIONES_TECNICAS.md",
    "DICCIONARIO_TABLAS.md",
    "GLOSARIO_REGLAS.md",
    "CORE_OPERACION_V1.md",
    "CORE_VENTAS_BASE_V1.md",
    "BITACORA.md",
]

DIRECTORIOS_CODIGO = ["modules"]

SALIDA_CONTEXTO = PROJECT_DOCS / "CONTEXTO_IA.md"
SALIDA_CODIGO = PROJECT_DOCS / "CODIGO_CONSOLIDADO.md"
SALIDA_INVENTARIO = PROJECT_DOCS / "INVENTARIO_PROYECTO.md"

EXCLUIR_DIRECTORIOS = {"__pycache__", ".git", ".venv", ".vscode"}

EXCLUIR_EXTENSIONES = {".pyc"}

# ==========================================================
# UTILIDADES
# ==========================================================


def separador(f):
    f.write("\n\n" + "=" * 100 + "\n\n")


def leer_archivo(path):
    try:
        with open(path, "r", encoding="utf-8") as fp:
            return fp.read()
    except Exception as e:
        return f"ERROR LEYENDO {path}\n{e}"


# ==========================================================
# CONTEXTO IA
# ==========================================================


def generar_contexto_ia():

    with open(SALIDA_CONTEXTO, "w", encoding="utf-8") as out:
        out.write("# CONTEXTO IA - MATINAL\n\n")

        out.write("## RESUMEN EJECUTIVO\n\n")

        out.write(
            """
Proyecto: MATINAL

Estado:
Producción Operativa

Objetivo:
Permitir que una nueva IA o una nueva sesión de Copilot
continúe el proyecto sin pérdida de contexto.

Arquitectura Oficial:

RAW
↓
SQLITE
↓
STAGING
↓
CORE
↓
BUSINESS RULES
↓
REPORTES

Prioridad de lectura:

1. ARQUITECTURA.md
2. ESTADO_ACTUAL.md
3. ROADMAP.md
4. DECISIONES_TECNICAS.md
5. DICCIONARIO_TABLAS.md
6. GLOSARIO_REGLAS.md
7. CORE_OPERACION_V1.md
8. CORE_VENTAS_BASE_V1.md
9. BITACORA.md
"""
        )

        separador(out)

        for doc in DOCS_PRIORITARIOS:
            ruta = PROJECT_DOCS / doc

            if not ruta.exists():
                continue

            out.write(f"# DOCUMENTO: {doc}\n\n")
            out.write(leer_archivo(ruta))
            separador(out)

    print(f"✅ CONTEXTO IA generado: {SALIDA_CONTEXTO}")


# ==========================================================
# CODIGO CONSOLIDADO
# ==========================================================


def generar_codigo_consolidado():

    with open(SALIDA_CODIGO, "w", encoding="utf-8") as out:
        out.write("# CODIGO CONSOLIDADO MATINAL\n\n")

        # ARCHIVOS RAIZ

        for archivo in ARCHIVOS_RAIZ:
            ruta = Path(archivo)

            if not ruta.exists():
                continue

            out.write(f"\n### ARCHIVO: {archivo}\n\n")

            out.write(leer_archivo(ruta))

            separador(out)

        # MODULOS

        for directorio in DIRECTORIOS_CODIGO:
            base = Path(directorio)

            if not base.exists():
                continue

            for ruta in sorted(base.rglob("*.py")):
                if any(parte in EXCLUIR_DIRECTORIOS for parte in ruta.parts):
                    continue

                out.write(f"\n### ARCHIVO: {ruta}\n\n")

                out.write(leer_archivo(ruta))

                separador(out)

    print(f"✅ CODIGO CONSOLIDADO generado: {SALIDA_CODIGO}")


# ==========================================================
# INVENTARIO
# ==========================================================


def generar_inventario():

    with open(SALIDA_INVENTARIO, "w", encoding="utf-8") as out:
        out.write("# INVENTARIO DEL PROYECTO MATINAL\n\n")

        # ----------------------------------
        # RAIZ
        # ----------------------------------

        out.write("## ARCHIVOS RAIZ\n\n")

        for item in sorted(ROOT.iterdir()):
            if not item.is_file():
                continue

            if item.suffix.lower() in EXCLUIR_EXTENSIONES:
                continue

            out.write(f"- {item.name}\n")

        # ----------------------------------
        # MODULES
        # ----------------------------------

        out.write("\n## MODULES\n\n")

        modules = ROOT / "modules"

        if modules.exists():
            for ruta in sorted(modules.rglob("*")):
                if not ruta.is_file():
                    continue

                if ruta.suffix.lower() in EXCLUIR_EXTENSIONES:
                    continue

                if any(parte in EXCLUIR_DIRECTORIOS for parte in ruta.parts):
                    continue

                out.write(f"- {ruta.relative_to(ROOT)}\n")

        # ----------------------------------
        # PROJECT DOCS
        # ----------------------------------

        out.write("\n## PROJECT_DOCS\n\n")

        if PROJECT_DOCS.exists():
            for doc in sorted(PROJECT_DOCS.glob("*")):
                if doc.is_file():
                    out.write(f"- {doc.name}\n")

    print(f"✅ INVENTARIO generado: {SALIDA_INVENTARIO}")


# ==========================================================
# MAIN
# ==========================================================


def generar_contexto():

    PROJECT_DOCS.mkdir(parents=True, exist_ok=True)

    generar_contexto_ia()
    generar_codigo_consolidado()
    generar_inventario()

    print("\n✅ Contexto MATINAL generado correctamente")


if __name__ == "__main__":
    generar_contexto()
