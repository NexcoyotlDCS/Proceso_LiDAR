import os
import readline  # Autocompletado en terminal
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm
import time
import numpy as np
import pdal

# Configurar el autocompletado con TAB
def completer(text, state):
    options = [x for x in os.listdir() if x.startswith(text)]
    if state < len(options):
        return options[state]
    return None

readline.set_completer(completer)
readline.parse_and_bind('tab: complete')  # Habilitar autocompletado con TAB

# Introduce nombre de archivo LAS
filename_las = input("Nombre de archivo LAS (sin extensión .las): ")
las_file_path = f"{filename_las}.las"

if os.path.exists(las_file_path):
    print(f"Archivo capturado: {las_file_path} \n")

    # Leer el archivo LAS usando PDAL
    filename_SHP = input("Nombre de archivo SHAPE (sin extensión .shp): ")
    shp_file_path = f"{filename_SHP}.shp"

    if os.path.exists(shp_file_path):
        print(f"Archivo capturado: {shp_file_path}\n")
        # Cargar el archivo SHP como GeoDataFrame
        shp_file = gpd.read_file(shp_file_path)

        # Preguntar por el Sistema de Referencia de Coordenadas (SRC)
        SRC = input("Sistema de Referencia de Coordenadas ej. (EPSG:XXXXX) solo números: ")
        SRC_asignado = f"EPSG:{SRC.split(':')[-1]}"  # Asegura que esté en formato 'EPSG:XXXX'
        print(f"Usted capturó {SRC_asignado}")

        start_time = time.time()  # Marca el inicio del tiempo

        # Convertir al CRS asignado si es necesario
        if shp_file.crs != SRC_asignado:
            shp_file = shp_file.to_crs(SRC_asignado)
            print(f"CRS convertido a {SRC_asignado}\n")
        else:
            print("El archivo ya está en el CRS indicado.\n")

        print("Ejecutando programa.")

        # Obtener el polígono del shapefile
        ##polygon = shp_file.geometry.unary_union  # Usamos unary_union para mayor eficiencia
        polygon = shp_file.geometry.union_all()   # Usamos unary_union para mayor eficiencia
        polygon_wkt = polygon.wkt  # Obtiene la representación WKT del polígono

        # Crear el pipeline de PDAL
        pipeline = f"""
        {{
            "pipeline": [
                "{las_file_path}",
                {{
                    "type": "filters.crop",
                    "polygon": "{polygon_wkt}"
                }},
                {{
                    "type": "writers.las",
                    "filename": "{filename_las}_recortado.las"
                }}
            ]
        }}
        """

        print("Iniciando ejecución del pipeline PDAL...\n")
        for i in tqdm(range(1), desc="Procesando con PDAL"):

            # Ejecutar el pipeline
            pipeline_obj = pdal.Pipeline(pipeline)
            pipeline_obj.execute()

        print(f"Archivo recortado guardado como '{filename_las}_recortado.las'")
    else:
        print(f"El archivo '{shp_file_path}' no existe, revisar.")
else:
    print(f"El archivo '{las_file_path}' no existe, revisar.")

# Calcular el tiempo total de ejecución
end_time = time.time()  # Marca el final del tiempo
elapsed_time = (end_time - start_time) / 60  # Calcula la diferencia
print(f"El script tardó {elapsed_time:.2f} minutos en ejecutarse.")