import os


def cargar_ignorados(ruta_base):
    ignorados = set()
    ruta_ignore = os.path.join(ruta_base, ".notes-ignore")
    if os.path.exists(ruta_ignore):
        with open(ruta_ignore, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#"):
                    ignorados.add(os.path.normpath(linea))
    return ignorados


def debe_ignorar_carpeta(nombre_carpeta):
    """Ignora automáticamente carpetas comunes que no queremos"""
    carpetas_ignoradas = {
        ".venv",
        "__pycache__",
        ".git",
        ".pytest_cache",
        "node_modules",
        ".idea",
        ".vscode",
        "venv",
        "env",
    }
    return nombre_carpeta in carpetas_ignoradas


def esta_ignorado(path_relativo, ignorados):
    # Normalizar path
    path_relativo = os.path.normpath(path_relativo)

    # Verificar si el path completo está ignorado
    if path_relativo in ignorados:
        return True

    # Verificar cada parte del path
    partes = path_relativo.split(os.sep)
    for i in range(1, len(partes) + 1):
        subpath = os.path.join(*partes[:i])
        if subpath in ignorados:
            return True

    return False


def concatenar_notas(directorio_raiz, salida):
    ignorados = cargar_ignorados(directorio_raiz)

    if not os.path.exists(directorio_raiz):
        print(f"Error: El directorio '{directorio_raiz}' no existe.")
        return False
    
    try:
        with open(salida, "w", encoding="utf-8") as archivo_salida:
        
            for carpeta_actual, subcarpetas, archivos in os.walk(directorio_raiz):
                # Filtrar subcarpetas antes de continuar
                subcarpetas[:] = [sc for sc in subcarpetas if not debe_ignorar_carpeta(sc)]

                ruta_rel_carpeta = os.path.relpath(carpeta_actual, directorio_raiz)

                # Skip si la carpeta actual está ignorada
                if ruta_rel_carpeta != "." and esta_ignorado(ruta_rel_carpeta, ignorados):
                    continue

                for archivo in sorted(archivos):
                    # if archivo.endswith('.py'):
                    if archivo.endswith(".md"):
                        ruta_rel_archivo = os.path.relpath(
                            os.path.join(carpeta_actual, archivo), directorio_raiz
                        )

                        if not esta_ignorado(ruta_rel_archivo, ignorados):
                            archivo_salida.write(f"# {ruta_rel_archivo}\n\n")
                            archivo_salida.write(
                                "========================================\n"
                            )
                            archivo_salida.write(f"📄 Archivo: {archivo}\n")
                            archivo_salida.write(f"📁 Ruta relativa: {ruta_rel_archivo}\n")
                            archivo_salida.write(
                                "========================================\n\n"
                            )

                            try:
                                with open(
                                    os.path.join(carpeta_actual, archivo),
                                    "r",
                                    encoding="utf-8",
                                ) as f:
                                    archivo_salida.write(f.read() + "\n\n")
                            except UnicodeDecodeError:
                                archivo_salida.write(
                                    f"[Error: No se pudo leer el archivo {archivo}]\n\n"
                                )
    
    except PermissionError:
        print(f"Error: No se pudo escribir en el archivo de salida '{salida}'.")
        return False
    except FileNotFoundError:
        print(f"Error: El directorio '{directorio_raiz}' no existe.")
        return False
    
    except OSError as e:
        print(f"Error de sistema operativo: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado: {e}")


# Configuración
directorio = "/home/jorgehaq_vm/projects/backend/python/interview-exercises/007-djang-factory-report/"
directorio = "/home/jorgehaq_vm/mnt/google_drive_folder_main/NOTES/PROJECTS/B. HOT/10. KAFKA PROYECTO"
directorio = "/home/jorgehaq_vm/projects/backend/python/interview-exercises/007-django-simple-factory-report"
directorio = "/home/jorgehaq_vm/mnt/google_drive_folder_main/NOTES/PROJECTS/A. STAGED/9. CLAUDE CV PREPARATION/2. CHATGPT - DEEP DIVE/1. Arquitectura y Patrones de Diseño/KIRK/2.1.2.0 django simple factory usuarios"
directorio = "/home/jorgehaq_vm/mnt/google_drive_folder_main/NOTES/PROJECTS/B. HOT/10. KAFKA PROYECTO/A.3. insights, arbol jerarquias tech"
salida = "notas_concatenadas.md"

concatenar_notas(directorio, salida)
