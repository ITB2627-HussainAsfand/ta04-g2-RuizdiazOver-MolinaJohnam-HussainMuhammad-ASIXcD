import csv
import xml.etree.ElementTree as ET
import re
import glob
import sys
import os

def limpiar_nombre_etiqueta(nombre):
    nombre = nombre.strip().lower()
    nombre = re.sub(r'[^a-z0-9_]', '_', nombre)
    if not nombre or nombre[0].isdigit() or nombre.startswith('xml'):
        nombre = f"campo_{nombre}"
    return nombre

def convertir_csv_a_xml(archivo_csv, archivo_xml):
    raiz = ET.Element("incidencies")
    
    with open(archivo_csv, mode='r', encoding='utf-8-sig') as f:
        muestra = f.read(1024)
        f.seek(0)
        delimitador = ';' if muestra.count(';') > muestra.count(',') else ','
        
        lector = csv.DictReader(f, delimiter=delimitador)
        
        for fila in lector:
            nodo_incidencia = ET.SubElement(raiz, "incidencia")
            for columna, valor in fila.items():
                if columna is not None:
                    etiqueta = limpiar_nombre_etiqueta(columna)
                    sub_elemento = ET.SubElement(nodo_incidencia, etiqueta)
                    sub_elemento.text = valor.strip() if valor else ""

    arbol = ET.ElementTree(raiz)
    ET.indent(arbol, space="    ", level=0)
    arbol.write(archivo_xml, encoding="utf-8", xml_declaration=True)
    print(f"✅ ¡Listo! '{archivo_csv}' convertido a '{archivo_xml}' correctamente.")

if __name__ == "__main__":
    try:
        # 1. Si el usuario/profe pasa el nombre por terminal: python3 convertir.py otro_archivo.csv
        if len(sys.argv) > 1:
            archivo_entrada = sys.argv[1]
        else:
            # 2. Si no pasa nada, busca automáticamente cualquier .csv en la carpeta actual
            archivos_csv = glob.glob("*.csv")
            if not archivos_csv:
                raise FileNotFoundError("No hay ningún archivo .csv en esta carpeta.")
            archivo_entrada = archivos_csv[0]

        convertir_csv_a_xml(archivo_entrada, "incidencies.xml")

    except FileNotFoundError as e:
        print(f"\033[91m❌ Error de archivo:\033[0m No se encuentra '{e.filename or e}'")
    except PermissionError:
        print("\033[91m❌ Error de permisos:\033[0m Cierra el archivo CSV o XML si lo tienes abierto en otro programa.")
    except Exception as e:
        # Captura cualquier otro error y muestra solo el tipo y el mensaje corto
        print(f"\033[91m❌ Error inesperado ({type(e).__name__}):\033[0m {e}")