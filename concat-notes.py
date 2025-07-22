import os


def cargar_ignorados(ruta_base):
    ignorados = set()
    ruta_ignore = os.path.join(ruta_base, '.notes-ignore')
    if os.path.exists(ruta_ignore):
        with open(ruta_ignore, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith('#'):
                    ignorados.add(os.path.normpath(linea))
    return ignorados


def esta_ignorado(path_relativo, ignorados):
    partes = path_relativo.split(os.sep)
    for i in range(1, len(partes) + 1):
        subpath = os.path.join(*partes[:i])
        if subpath in ignorados:
            return True
    return False


def concatenar_notas(directorio_raiz, salida):
    ignorados = cargar_ignorados(directorio_raiz)

    with open(salida, 'w', encoding='utf-8') as archivo_salida:
        for carpeta_actual, subcarpetas, archivos in sorted(os.walk(directorio_raiz)):
            ruta_rel_carpeta = os.path.relpath(carpeta_actual, directorio_raiz)
            if esta_ignorado(ruta_rel_carpeta, ignorados):
                subcarpetas.clear()
                continue

            for archivo in sorted(archivos):
                ruta_rel_archivo = os.path.relpath(os.path.join(carpeta_actual, archivo), directorio_raiz)
                if archivo.endswith('.md') and not esta_ignorado(ruta_rel_archivo, ignorados):
                    archivo_salida.write(f"# {ruta_rel_archivo}\n\n")
                    with open(os.path.join(carpeta_actual, archivo), 'r', encoding='utf-8') as f:
                        archivo_salida.write("========================================\n")
                        archivo_salida.write(f"📄 Archivo: {archivo}\n")
                        archivo_salida.write(f"📁 Ruta relativa: {ruta_rel_archivo}\n")
                        archivo_salida.write("========================================\n\n")



# Usa esta ruta para apuntar a tu árbol de notas
directorio = "/home/jorgehaq_vm/mnt/google_drive_folder_main/NOTES/PROJECTS/9. CLAUDE CV PREPARATION"
salida = "notas_concatenadas.md"

concatenar_notas(directorio, salida)
