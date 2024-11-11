import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import glob
import os

def crear_shps_gnss():
    # Obtener el directorio de trabajo actual
    ruta_directorio = os.getcwd()

    # Crear la carpeta 'Rutas' si no existe
    carpeta_shapes = os.path.join(ruta_directorio, 'Rutas')
    os.makedirs(carpeta_shapes, exist_ok=True)

    # Obtener todos los archivos .txt que comienzan con el patrón proporcionado
    archivo_p = input("Ingrese patrón de búsqueda: ")
    archivos_txt = glob.glob(os.path.join(ruta_directorio, f'**/{archivo_p}*.txt'), recursive=True)

    if not archivos_txt:
        print(f"No se encontraron archivos con el patrón '{archivo_p}'.")
        return

    # Solicitar el Sistema de Referencia de Coordenadas
    SRC = input("Sistema de Referencia de Coordenadas ej. (EPSG:XXXXX) solo números ó dejar vacío para EPSG:4326 (Geográficas)): ")

    # Asignar el SRC ingresado o usar EPSG:4326 por defecto
    SRC_asignado = f"EPSG:{SRC.strip()}" if SRC.strip() else "EPSG:4326"
    print(f"Datos reproyectados a {SRC_asignado} \n")

    cor_x = int(input("Posición columna X: "))
    cor_y = int(input("Posición columna Y: "))
    cor_z = int(input("Posición columna Z: "))

    # Preguntar cuántas filas del inicio eliminar
    filas_a_eliminar = int(input("\n¿Cuántas filas iniciales desea eliminar? (0 para no eliminar ninguna): "))
    print("\n")

    for archivo in archivos_txt:
        # Leer el archivo .txt
        df = pd.read_csv(archivo, sep=r'\s+', header=None)
        if filas_a_eliminar > 0:
            df = df.iloc[filas_a_eliminar:]  # Eliminar las filas iniciales

        df = df[df[cor_z] >= 0]

        # Verificar si hay suficientes columnas
        if df.shape[1] < 5:
            print(f"El archivo {archivo} no tiene suficientes columnas para procesar.")
            continue

        # Eliminar columnas que no sean de coordenadas
        df_coordenadas = df[[cor_x, cor_y, cor_z]].copy()

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

        # Agregar la columna 'fil3' basada en los valores de 'Fil'
        df['fil3'] = None
        df.loc[df['Fil'].notnull() & df['fil2'] != 0, 'fil3'] = df['Fil'].apply(
            lambda x: 'N-S' if x in [90, 270] else ('E-W' if x in [180, 360] else None)
        )

        # Realizar un conteo en 'fil3' y filtrar las filas con el mayor conteo
        if 'fil3' in df.columns:
            max_label = df['fil3'].value_counts().idxmax()  # Obtener la etiqueta con el mayor conteo
            df_filtrada = df[df['fil3'] == max_label]  # Filtrar las filas con esa etiqueta
        else:
            df_filtrada = df

        # Guardar el archivo filtrado como shapefile
        gdf_filtrada = gpd.GeoDataFrame(df_filtrada, geometry=geometry)
        gdf_filtrada.set_crs(SRC_asignado, inplace=True)

        # Generar el nombre del archivo .shp
        nombre_archivo_salida = os.path.splitext(os.path.basename(archivo))[0] + '_filtrada.shp'
        ruta_salida = os.path.join(carpeta_shapes, nombre_archivo_salida)

        # Guardar como archivo .shp
        gdf_filtrada.to_file(ruta_salida, driver='ESRI Shapefile')
        print(f"Archivo {nombre_archivo_salida} guardado exitosamente en la carpeta 'Rutas'")

# Ejemplo de uso
crear_shps_gnss()
