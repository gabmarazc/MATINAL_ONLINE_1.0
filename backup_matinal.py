from pathlib import Path
from datetime import datetime
import shutil
import sys

# ==================================================
# CONFIGURACION
# ==================================================

DB_NAME = "data/matinal.db"
BACKUP_FOLDER = "Backup"
MAX_BACKUPS = 3

# ==================================================
# FUNCIONES
# ==================================================


def crear_backup():
    db_path = Path(DB_NAME)

    # Verificar que exista la base
    if not db_path.exists():
        print(f"\nERROR: No se encontró la base '{DB_NAME}'")
        sys.exit(1)

    # Crear carpeta Backup si no existe
    backup_dir = Path(BACKUP_FOLDER)
    backup_dir.mkdir(exist_ok=True)

    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Archivo destino
    backup_file = backup_dir / f"matinal_{timestamp}.db"

    # Copia física conservando metadata
    shutil.copy2(db_path, backup_file)

    print("\nBackup creado correctamente")
    print(f"Archivo: {backup_file}")

    return backup_dir


def limpiar_backups_antiguos(backup_dir):
    backups = sorted(
        backup_dir.glob("matinal_*.db"),
        key=lambda archivo: archivo.stat().st_mtime,
        reverse=True,
    )

    eliminados = 0

    if len(backups) > MAX_BACKUPS:
        for archivo in backups[MAX_BACKUPS:]:
            archivo.unlink()
            eliminados += 1

    return eliminados


def mostrar_estado(backup_dir):
    backups = sorted(
        backup_dir.glob("matinal_*.db"),
        key=lambda archivo: archivo.stat().st_mtime,
        reverse=True,
    )

    print("\nBackups disponibles:\n")

    if not backups:
        print("No hay backups.")
        return

    for archivo in backups:
        tamaño_mb = archivo.stat().st_size / (1024 * 1024)

        print(f"{archivo.name} ({tamaño_mb:.2f} MB)")

    print(f"\nBackups conservados: {len(backups)}")


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BACKUP AUTOMATICO DE MATINAL.DB")
    print("=" * 60)

    backup_dir = crear_backup()

    eliminados = limpiar_backups_antiguos(backup_dir)

    if eliminados > 0:
        print(f"\nBackups eliminados: {eliminados}")

    mostrar_estado(backup_dir)

    print("\nProceso finalizado correctamente")
