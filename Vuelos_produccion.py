import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import glob
import os
import numpy as np

# Función para calcular el rumbo entre dos puntos
def calcular_rumbo(p_actual, p_siguiente):
    dx = p_siguiente[0] - p_actual[0]
    dy = p_siguiente[1] - p_actual[1]

    if dx == 0 and dy == 0:
        return None  # Puntos duplicados, no hay rumbo

    rumbo = np.degrees(np.arctan2(dy, dx)) % 360
    return rumbo

# Función para clasificar rumbos en grupos de 10°
def clasificar_rumbo_en_grupo(rumbo):
    if rumbo is None or np.isnan(rumbo):
        return None

    if rumbo <= 5 or rumbo > 355:
        return 360

    for grupo in range(10, 360, 10):
        if grupo - 5 < rumbo <= grupo + 5:
            return grupo

    return None

# Función principal para crear los shapefiles
def crear_shps_gnss():
    ruta_directorio = os.getcwd()
    carpeta_vuelos = os.path.join(ruta_directorio, 'Vuelos_producción')
    os.makedirs(carpeta_vuelos, exist_ok=True)

    # 1.- Preguntar el patrón de búsqueda
    archivo_p = input("Ingrese patrón de búsqueda: ")
    archivos_txt = glob.glob(os.path.join(ruta_directorio, f'**/{archivo_p}*.txt'), recursive=True)

    if not archivos_txt:
        print(f"No se encontraron archivos con el patrón '{archivo_p}'.")
        return

    SRC = input("\nSistema de Referencia de Coordenadas ej. (EPSG:XXXXX) o dejar vacío para EPSG:4326: ")
    SRC_asignado = f"EPSG:{SRC.strip()}" if SRC.strip() else "EPSG:4326"
    print(f"Datos reproyectados a {SRC_asignado} \n")

    ruta_longitudes = os.path.join(carpeta_vuelos, 'Reporte.txt')
    suma_total_longitudes = 0

    cor_x = int(input("Posición columna X: "))
    cor_y = int(input("Posición columna Y: "))
    cor_z = int(input("Posición columna Z: "))

    # Preguntar cuántas filas del inicio eliminar
    filas_a_eliminar = int(input("\n¿Cuántas filas iniciales desea eliminar? (0 para no eliminar ninguna): "))
    print("\n")

    for archivo in archivos_txt:
        try:
            df = pd.read_csv(archivo, sep=r'\s+', header=None)
            if filas_a_eliminar > 0:
                df = df.iloc[filas_a_eliminar:]  # Eliminar las filas iniciales

            df = df[df[cor_z] >= 0]

            if df.shape[1] < 5:
                print(f"El archivo {archivo} no tiene suficientes columnas para procesar.")
                continue

            df_coordenadas = df[[cor_x, cor_y, cor_z]].copy()
            df_coordenadas.columns = ['X', 'Y', 'Z']
            df_coordenadas['X'] = df_coordenadas['X'].round(9)
            df_coordenadas['Y'] = df_coordenadas['Y'].round(6)
            df_coordenadas = df_coordenadas.drop_duplicates().reset_index(drop=True)

            rumbos = []
            for i in range(len(df_coordenadas) - 1):
                p_actual = df_coordenadas.iloc[i][['X', 'Y']].values
                p_siguiente = df_coordenadas.iloc[i + 1][['X', 'Y']].values
                if np.array_equal(p_actual, p_siguiente):
                    rumbos.append(None)
                    continue
                rumbo = calcular_rumbo(p_actual, p_siguiente)
                rumbos.append(rumbo)
            rumbos.append(rumbos[-1] if rumbos else None)

            df_coordenadas['rumbo'] = rumbos

            grupos = [clasificar_rumbo_en_grupo(rumbo) for rumbo in rumbos]
            df_coordenadas['grupo'] = grupos

            conteo_grupos = df_coordenadas['grupo'].value_counts()
            dos_grupos_mayor_frecuencia = conteo_grupos.nlargest(2).index.tolist()
            df_coordenadas['Fil'] = np.where(df_coordenadas['grupo'].isin(dos_grupos_mayor_frecuencia), df_coordenadas['grupo'], np.nan)
            df_coordenadas['fil2'] = 0

            conteo_actual = 1
            for i in range(len(df_coordenadas)):
                if pd.notna(df_coordenadas.loc[i, 'Fil']):
                    df_coordenadas.loc[i, 'fil2'] = conteo_actual
                elif i > 0 and pd.notna(df_coordenadas.loc[i - 1, 'Fil']):
                    conteo_actual += 1

            df_coordenadas = df_coordenadas[df_coordenadas['fil2'] != 0]
            conteo_final = df_coordenadas['fil2'].value_counts()
            mayor_conteo = conteo_final.max()
            limite_conservacion = mayor_conteo - mayor_conteo // 3
            df_coordenadas = df_coordenadas[df_coordenadas['fil2'].isin(conteo_final[conteo_final >= limite_conservacion].index)]

            fil_values = df_coordenadas['Fil'].dropna().unique()
            direction = ''
            if any(fil in [180, 360] for fil in fil_values):
                direction = 'E - W'
            elif any(fil in [90, 270] for fil in fil_values):
                direction = 'N - S'
            else:
                direction = 'Dirección desconocida'

            lineas = [LineString(zip(grupo['X'], grupo['Y'])) for _, grupo in df_coordenadas.groupby('fil2')]
            gdf_lineas = gpd.GeoDataFrame(geometry=lineas)
            gdf_lineas.set_crs(epsg=4326, inplace=True)
            gdf_lineas = gdf_lineas.to_crs(SRC_asignado)
            gdf_lineas['long_km'] = gdf_lineas.length / 1000
            gdf_lineas['ID'] = range(1, len(gdf_lineas) + 1)
            gdf_lineas['dirección'] = direction
            gdf_lineas = gdf_lineas[['ID', 'dirección', 'long_km', 'geometry']]

            nombre_archivo_salida = os.path.basename(archivo).replace('.txt', '_lineas.shp')
            ruta_salida = os.path.join(carpeta_vuelos, nombre_archivo_salida)
            gdf_lineas.to_file(ruta_salida, driver='ESRI Shapefile')

            print(f"Vuelo {os.path.basename(archivo).replace('.txt', '')} con dirección {direction} procesado correctamente")

            suma_longitudes = gdf_lineas['long_km'].sum()
            suma_total_longitudes += suma_longitudes

            with open(ruta_longitudes, 'a') as f:
                f.write(f"Vuelo: {os.path.basename(archivo).replace('.txt', '')} con dirección {direction} y longitud total de líneas de producción {suma_longitudes:.3f} km\n")

        except Exception as e:
            print(f"Error al procesar el archivo {archivo}: {str(e)}")

    print("\n")
    with open(ruta_longitudes, 'a') as f:
        f.write(f"Total de todas las longitudes: {suma_total_longitudes:.3f} km\n")

# Ejecutar la función
crear_shps_gnss()
