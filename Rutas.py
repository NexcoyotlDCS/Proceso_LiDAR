#Programa que crea rutas completas a partir de puntos de archivo GNSS
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import glob
import os

def crear_shps_gnss():
    # Obtener el directorio de trabajo actual
    ruta_directorio = os.getcwd()

    # Crear la carpeta 'Shapes' si no existe
    carpeta_shapes = os.path.join(ruta_directorio, 'Shapes')
    os.makedirs(carpeta_shapes, exist_ok=True)

    # Obtener todos los archivos .txt que comienzan con 'GNSS_v' (o cualquier patrón proporcionado)
    archivo_p = input("Ingrese patrón de búsqueda: ")
    archivos_txt = glob.glob(os.path.join(ruta_directorio, f'{archivo_p}*.txt'))

    if not archivos_txt:
        print(f"No se encontraron archivos con el patrón '{archivo_p}'.")
        return

    # Solicitar al usuario el Sistema de Referencia de Coordenadas
    SRC = input("Sistema de Referencia de Coordenadas ej. (EPSG:XXXXX) solo números ó dejar vacío para EPSG:4326 (Geográficas)): ")

    # Asignar el SRC ingresado o usar EPSG:4326 por defecto
    if SRC.strip() == "":
        SRC_asignado = "EPSG:4326"
        print("No se ingresó SRC. Usando el valor por defecto: EPSG:4326\n")
    else:
        SRC_asignado = f"EPSG:{SRC.strip()}"
        print(f"Datos reproyectados a {SRC_asignado} \n")

    for archivo in archivos_txt:
        # Leer el archivo .txt
        df = pd.read_csv(archivo, sep=r'\s+', header=None)

        # Verificar si hay suficientes columnas
        if df.shape[1] < 5:
            print(f"El archivo {archivo} no tiene suficientes columnas para procesar.")
            continue

        # Eliminar columnas que no sean de coordenadas (asumiendo que X=columna 2, Y=columna 3, Z=columna 4)
        df_coordenadas = df[[2, 3, 4]].copy()

        # Renombrar las columnas
        df_coordenadas.columns = ['X', 'Y', 'Z']

        # Crear geometría de puntos
        geometry = [Point(xy) for xy in zip(df_coordenadas['X'], df_coordenadas['Y'])]

        # Crear un GeoDataFrame
        gdf = gpd.GeoDataFrame(df_coordenadas, geometry=geometry)

        # Asignar el sistema de referencia de coordenadas (SRC ingresado por el usuario)
        gdf.set_crs("EPSG:4326", inplace=True)  # Asignar inicialmente como EPSG:4326

        # Si se ingresó un SRC diferente, reproyectar
        if SRC_asignado != "EPSG:4326":
            gdf = gdf.to_crs(SRC_asignado)
            #print(f"Datos reproyectados a {SRC_asignado}")

        # Generar el nombre del archivo .shp
        nombre_archivo_salida = os.path.splitext(os.path.basename(archivo))[0] + '.shp'
        ruta_salida = os.path.join(carpeta_shapes, nombre_archivo_salida)

        # Guardar como archivo .shp
        gdf.to_file(ruta_salida, driver='ESRI Shapefile')
        print(f"Archivo {nombre_archivo_salida} guardado exitosamente en Shapes")

# Ejemplo de uso
crear_shps_gnss()