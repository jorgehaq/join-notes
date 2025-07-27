import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

@dataclass
class ArchivoInfo:
    ruta_relativa: str
    contenido: str
    nombre: str


def leer_archivo_individual(ruta_completa, ruta_relativa, nombre):
    """Lee un archivo y retorna su info"""
    try:
        with open(ruta_completa, "r", encoding="utf-8") as f:
            contenido = f.read()
        return ArchivoInfo(ruta_relativa, contenido, nombre)
    except UnicodeDecodeError:
        return ArchivoInfo(ruta_relativa, f"[Error: No se pudo leer el archivo {nombre}]", nombre)

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

def coincide_con_patron(nombre_archivo, patron):
    """Verifica si archivo coincide con extensión o patrón"""
    nombre_lower = nombre_archivo.lower()
    patron_lower = patron.lower()
    
    # Caso 1: Extensión normal (.md, .py, .txt)
    if nombre_lower.endswith(patron_lower):
        return True
    
    # Caso 2: Archivos especiales (.env -> .env.docker)
    if patron_lower in ['.env', '.config'] and nombre_lower.startswith(patron_lower + '.'):
        return True
        
    return False

def recolectar_archivos_a_procesar(directorio_raiz, ignorados, extensiones):
    """Recolecta archivos con las extensiones/patrones especificados"""
    archivos_a_procesar = []
    
    print(f"🚀 Iniciando recorrido desde: {directorio_raiz}")
    
    for carpeta_actual, subcarpetas, archivos in os.walk(directorio_raiz):
        print(f"📁 Procesando carpeta: {carpeta_actual}")
        print(f"   📂 Subcarpetas encontradas: {subcarpetas}")
        print(f"   📄 Archivos encontrados: {archivos}")
        
        # Filtrar subcarpetas ignoradas
        subcarpetas_originales = subcarpetas.copy()
        subcarpetas[:] = [sc for sc in subcarpetas if not debe_ignorar_carpeta(sc)]
        if subcarpetas_originales != subcarpetas:
            print(f"   🚫 Subcarpetas filtradas: {set(subcarpetas_originales) - set(subcarpetas)}")
        
        ruta_rel_carpeta = os.path.relpath(carpeta_actual, directorio_raiz)
        print(f"   📍 Ruta relativa: {ruta_rel_carpeta}")
        
        if ruta_rel_carpeta != "." and esta_ignorado(ruta_rel_carpeta, ignorados):
            print("   ❌ Carpeta ignorada por .notes-ignore")
            continue
            
        for archivo in sorted(archivos):
            print(f"      🔍 Evaluando archivo: {archivo}")
            # NUEVO: verificar patrones además de extensiones
            coincide = any(coincide_con_patron(archivo, ext) for ext in extensiones)
            print(f"         ✅ Coincide con patrón: {coincide}")
            
            if coincide:
                ruta_completa = os.path.join(carpeta_actual, archivo)
                ruta_relativa = os.path.relpath(ruta_completa, directorio_raiz)
                
                if not esta_ignorado(ruta_relativa, ignorados):
                    archivos_a_procesar.append((ruta_completa, ruta_relativa, archivo))
                    print(f"         ✅ AGREGADO: {archivo}")
                else:
                    print(f"         ❌ Ignorado por .notes-ignore: {archivo}")
    
    print(f"🎯 Total archivos a procesar: {len(archivos_a_procesar)}")
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

def concatenar_notas(directorio_raiz, salida, extensiones=None):
    """
    extensiones: lista de extensiones a incluir, ej: ['.md', '.py', '.txt']
    Si es None, usa solo .md por defecto
    """
    if extensiones is None:
        extensiones = ['.md']
    
    # Normalizar extensiones (agregar punto si falta)
    extensiones_normalizadas = []
    for ext in extensiones:
        if not ext.startswith('.'):
            ext = '.' + ext
        extensiones_normalizadas.append(ext.lower())
    
    if not os.path.exists(directorio_raiz):
        print(f"❌ Error: El directorio '{directorio_raiz}' no existe")
        return False
    
    ignorados = cargar_ignorados(directorio_raiz)
    archivos_a_procesar = recolectar_archivos_a_procesar(directorio_raiz, ignorados, extensiones_normalizadas)
    
    # DEBUG TEMPORAL
    print(f"🔍 Extensiones buscadas: {extensiones_normalizadas}")
    print(f"🔍 Directorio: {directorio_raiz}")
    print(f"🔍 Archivos encontrados: {len(archivos_a_procesar)}")
    
    if not archivos_a_procesar:
        extensiones_str = ', '.join(extensiones_normalizadas)
        print(f"⚠️  No se encontraron archivos con extensiones: {extensiones_str}")
        return False
    
    print(f"📁 Procesando {len(archivos_a_procesar)} archivos...")
    
    # PASO CLAVE: Leer todos los archivos en paralelo
    archivos_contenido = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(leer_archivo_individual, ruta_completa, ruta_relativa, nombre)
            for ruta_completa, ruta_relativa, nombre in archivos_a_procesar
        ]
        
        for future in futures:
            archivos_contenido.append(future.result())
    
    # PASO 2: Escribir todo de una vez
    try:
        with open(salida, "w", encoding="utf-8") as archivo_salida:
            for info in archivos_contenido:
                archivo_salida.write(f"# {info.ruta_relativa}\n\n")
                archivo_salida.write("========================================\n")
                archivo_salida.write(f"📄 Archivo: {info.nombre}\n")
                archivo_salida.write(f"📁 Ruta relativa: {info.ruta_relativa}\n")
                archivo_salida.write("========================================\n\n")
                archivo_salida.write(info.contenido + "\n\n")
                
    except Exception as e:
        print(f"❌ Error al escribir: {e}")
        return False
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
    
    print(f"✅ Notas concatenadas exitosamente en: {salida}")
    return True

# Configuración
directorio = "/home/jorgehaq_vm/projects/backend/python/interview-exercises/007-djang-factory-report/"
directorio = "/home/jorgehaq_vm/gdrive_fast/NOTES/PROJECTS/B. HOT/10. KAFKA PROYECTO"
directorio = "/home/jorgehaq_vm/projects/backend/python/interview-exercises/007-django-simple-factory-report"
directorio = "/home/jorgehaq_vm/gdrive_fast/NOTES/PROJECTS/A. STAGED/9. CLAUDE CV PREPARATION/2. CHATGPT - DEEP DIVE/1. Arquitectura y Patrones de Diseño/KIRK/2.1.2.0 django simple factory usuarios"
directorio = "/home/jorgehaq_vm/gdrive_fast/NOTES/PROJECTS/B. HOT/10. KAFKA PROYECTO/A.3. insights, arbol jerarquias tech"
directorio = "/home/jorgehaq_vm/gdrive_fast/NOTES/PROJECTS/B. HOT/10. KAFKA PROYECTO/0. STRUCTURE CODE"
directorio = "/home/jorgehaq_vm/gdrive_fast/NOTES/PROJECTS/B. HOT/3. AI-Powerred Data Processing"
directorio = "/home/jorgehaq_vm/gdrive_fast/NOTES/PROJECTS/A. OTROS/1. AXI - Client Analytics API"


salida = "notas_concatenadas.md"

directorio = "/home/jorgehaq_vm/gdrive_fast/NOTES/PROJECTS/B. HOT/3. AI-Powerred Data Processing"
directorio = "/home/jorgehaq_vm/projects/backend/python/client-analytics-api"

concatenar_notas(directorio, salida, ['md', 'py', 'txt', 'json', 'yml', 'Dockerfile', 'sh', '.env', '.dev', '.gcp'])
