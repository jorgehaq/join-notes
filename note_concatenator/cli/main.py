import os
import sys
import json
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class ArchivoInfo:
    ruta_relativa: str
    contenido: str
    nombre: str
    proyecto_origen: str


def leer_archivo_individual(ruta_completa, ruta_relativa, nombre, proyecto_origen=""):
    """Lee un archivo y retorna su info"""
    try:
        with open(ruta_completa, "r", encoding="utf-8") as f:
            contenido = f.read()
        return ArchivoInfo(ruta_relativa, contenido, nombre, proyecto_origen)
    except UnicodeDecodeError:
        return ArchivoInfo(
            ruta_relativa,
            f"[Error: No se pudo leer el archivo {nombre}]",
            nombre,
            proyecto_origen,
        )


def cargar_configuracion(archivo_config="projects.json"):
    """Carga la configuración de proyectos desde JSON"""
    try:
        with open(archivo_config, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{archivo_config}'")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer JSON: {e}")
        return None


def listar_proyectos(config):
    """Muestra todos los proyectos disponibles"""
    print("📋 Proyectos disponibles:")
    print("=" * 50)

    for proyecto in config["projects"]:
        activos = sum(1 for d in proyecto["directorios"] if d["activo"])
        total = len(proyecto["directorios"])

        print(f"🔹 {proyecto['project']}")
        print(f"   📝 {proyecto.get('description', 'Sin descripción')}")
        print(f"   📁 {activos}/{total} directorios activos")
        print()


def obtener_proyecto(config, nombre_proyecto):
    """Obtiene un proyecto específico por nombre"""
    for proyecto in config["projects"]:
        if proyecto["project"] == nombre_proyecto:
            return proyecto
    return None


def cargar_ignorados(ruta_base):
    """Carga archivos/carpetas a ignorar desde .notes-ignore"""
    ignorados = set()
    ruta_ignore = os.path.join(ruta_base, ".notes-ignore")
    if os.path.exists(ruta_ignore):
        with open(ruta_ignore, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#"):
                    ignorados.add(os.path.normpath(linea))
    return ignorados


def coincide_con_patron(nombre_archivo, patron):
    """Verifica si archivo coincide con extensión o patrón"""
    nombre_lower = nombre_archivo.lower()
    patron_lower = patron.lower()

    # Caso 1: Extensión normal (.md, .py, .txt)
    if nombre_lower.endswith(patron_lower):
        return True

    # Caso 2: Archivos especiales (.env -> .env.docker)
    if patron_lower in [".env", ".config"] and nombre_lower.startswith(
        patron_lower + "."
    ):
        return True

    return False


def recolectar_archivos_a_procesar(
    directorio_raiz, ignorados, extensiones, proyecto_nombre=""
):
    """Recolecta archivos con las extensiones/patrones especificados"""
    archivos_a_procesar = []

    if not os.path.exists(directorio_raiz):
        print(f"⚠️  Directorio no existe: {directorio_raiz}")
        return archivos_a_procesar

    print(f"📁 Procesando: {directorio_raiz}")

    for carpeta_actual, subcarpetas, archivos in os.walk(directorio_raiz):
        # Filtrar subcarpetas ignoradas
        subcarpetas[:] = [sc for sc in subcarpetas if not debe_ignorar_carpeta(sc)]

        ruta_rel_carpeta = os.path.relpath(carpeta_actual, directorio_raiz)

        if ruta_rel_carpeta != "." and esta_ignorado(ruta_rel_carpeta, ignorados):
            continue

        for archivo in sorted(archivos):
            if any(coincide_con_patron(archivo, ext) for ext in extensiones):
                ruta_completa = os.path.join(carpeta_actual, archivo)
                ruta_relativa = os.path.relpath(ruta_completa, directorio_raiz)

                if not esta_ignorado(ruta_relativa, ignorados):
                    archivos_a_procesar.append(
                        (ruta_completa, ruta_relativa, archivo, proyecto_nombre)
                    )

    return archivos_a_procesar


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
        ".mypy_cache",
    }
    return nombre_carpeta in carpetas_ignoradas


def esta_ignorado(path_relativo, ignorados):
    path_relativo = os.path.normpath(path_relativo)

    # Ignorar coincidencia exacta
    if path_relativo in ignorados:
        return True

    # Ignorar si cualquier ruta ignorada es un prefijo de la ruta relativa
    for patron in ignorados:
        patron_normalizado = os.path.normpath(patron)
        if path_relativo.startswith(patron_normalizado):
            return True

    return False



def crear_directorio_proyecto(
    proyecto_nombre, ruta_base="/home/jorgehaq_vm/gdrive_fast/JOINED-NOTES"
):
    """Crea el directorio del proyecto si no existe"""
    directorio_proyecto = os.path.join(ruta_base, proyecto_nombre)

    try:
        os.makedirs(directorio_proyecto, exist_ok=True)
        print(f"📁 Directorio preparado: {directorio_proyecto}")
        return directorio_proyecto
    except Exception as e:
        print(f"❌ Error creando directorio: {e}")
        return None


def concatenar_proyecto(proyecto, salida, extensiones):
    """Concatena todos los directorios activos de un proyecto"""

    print(f"🚀 Procesando proyecto: {proyecto['project']}")
    print(f"📝 Descripción: {proyecto.get('description', 'Sin descripción')}")
    print("=" * 60)

    todos_los_archivos = []

    for directorio_info in proyecto["directorios"]:
        if not directorio_info["activo"]:
            print(f"⏸️  Saltando (inactivo): {directorio_info['path']}")
            continue

        directorio_raiz = directorio_info["path"]
        ignorados = cargar_ignorados(directorio_raiz)

        archivos_del_directorio = recolectar_archivos_a_procesar(
            directorio_raiz, ignorados, extensiones, proyecto["project"]
        )

        todos_los_archivos.extend(archivos_del_directorio)
        print(f"   ✅ Encontrados: {len(archivos_del_directorio)} archivos")

    if not todos_los_archivos:
        extensiones_str = ", ".join(extensiones)
        print(f"⚠️  No se encontraron archivos con extensiones: {extensiones_str}")
        return False

    print(f"\n📦 Total archivos a procesar: {len(todos_los_archivos)}")

    # Leer todos los archivos en paralelo
    archivos_contenido = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                leer_archivo_individual,
                ruta_completa,
                ruta_relativa,
                nombre,
                proyecto_origen,
            )
            for ruta_completa, ruta_relativa, nombre, proyecto_origen in todos_los_archivos
        ]

        for future in futures:
            archivos_contenido.append(future.result())

    # Escribir todo de una vez
    try:
        with open(salida, "w", encoding="utf-8") as archivo_salida:
            # Header del proyecto
            archivo_salida.write(f"# 📋 PROYECTO: {proyecto['project'].upper()}\n\n")
            archivo_salida.write(
                f"**Descripción:** {proyecto.get('description', 'Sin descripción')}\n"
            )
            archivo_salida.write(
                f"**Generado:** {len(archivos_contenido)} archivos concatenados\n"
            )
            archivo_salida.write(f"**Extensiones:** {', '.join(extensiones)}\n\n")
            archivo_salida.write("=" * 80 + "\n\n")

            directorio_actual = ""
            for info in archivos_contenido:
                # Separador por directorio
                directorio_archivo = os.path.dirname(info.ruta_relativa)
                if directorio_archivo != directorio_actual:
                    directorio_actual = directorio_archivo
                    archivo_salida.write(
                        f"\n## 📁 Directorio: {directorio_archivo}\n\n"
                    )

                archivo_salida.write(f"### 📄 {info.nombre}\n")
                archivo_salida.write(f"**Ruta:** `{info.ruta_relativa}`\n\n")
                archivo_salida.write("```\n")
                archivo_salida.write(info.contenido)
                archivo_salida.write("\n```\n\n")
                archivo_salida.write("-" * 60 + "\n\n")

    except Exception as e:
        print(f"❌ Error al escribir: {e}")
        return False

    print(f"✅ Proyecto concatenado exitosamente en: {salida}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Concatena notas de proyectos configurados"
    )
    parser.add_argument("proyecto", nargs="?", help="Nombre del proyecto a concatenar")
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Lista todos los proyectos disponibles",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="projects.json",
        help="Archivo de configuración (default: projects.json)",
    )
    parser.add_argument(
        "--output", "-o", help="Archivo de salida (default: {proyecto}_concatenado.md)"
    )
    parser.add_argument(
        "--extensions",
        "-e",
        nargs="+",
        default=["md", "py", "txt", "json", "yml", "Dockerfile", "sh", ".env"],
        help="Extensiones de archivos a incluir",
    )

    args = parser.parse_args()

    # Cargar configuración
    config = cargar_configuracion(args.config)
    if not config:
        return 1

    # Listar proyectos si se solicita
    if args.list:
        listar_proyectos(config)
        return 0

    # Validar que se especificó un proyecto
    if not args.proyecto:
        print("❌ Error: Debes especificar un proyecto o usar --list para ver opciones")
        parser.print_help()
        return 1

    # Obtener proyecto
    proyecto = obtener_proyecto(config, args.proyecto)
    if not proyecto:
        print(f"❌ Error: Proyecto '{args.proyecto}' no encontrado")
        print("\n💡 Usa --list para ver proyectos disponibles")
        return 1

    # Normalizar extensiones
    extensiones_normalizadas = []
    for ext in args.extensions:
        if not ext.startswith("."):
            ext = "." + ext
        extensiones_normalizadas.append(ext.lower())

    # Determinar archivo de salida
    if args.output:
        salida = args.output
    else:
        salida = f"{args.proyecto}_concatenado.md"

    # Concatenar proyecto
    # exito = concatenar_proyecto(proyecto, salida, extensiones_normalizadas)

    # Crear directorio del proyecto
    directorio_destino = crear_directorio_proyecto(args.proyecto)
    if not directorio_destino:
        return 1

    # Determinar archivo de salida dentro del directorio del proyecto
    if args.output:
        # Si especifica nombre personalizado
        nombre_archivo = (
            args.output if args.output.endswith(".md") else f"{args.output}.md"
        )
    else:
        # Nombre por defecto
        nombre_archivo = f"{args.proyecto}_concatenado.md"

    salida = os.path.join(directorio_destino, nombre_archivo)

    print(f"📝 Archivo destino: {salida}")

    # Concatenar proyecto
    exito = concatenar_proyecto(proyecto, salida, extensiones_normalizadas)

    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
