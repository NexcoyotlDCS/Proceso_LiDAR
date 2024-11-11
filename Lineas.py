import geopandas as gpd
import pandas as pd
import os
from shapely.geometry import Point, LineString

# Definir las rutas de entrada y salida
input_folder = 'Vuelos_producción'
output_folder = 'Volumen de Obra'
lineas_file = os.path.join(output_folder, 'Lineas.shp')  # Nueva ruta para el shapefile de líneas

# Crear la carpeta de salida si no existe
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Leer y concatenar todos los shapefiles en el directorio de entrada
all_shapes = []
for file in os.listdir(input_folder):
    if file.endswith('.shp'):
        filepath = os.path.join(input_folder, file)
        shp = gpd.read_file(filepath)
        all_shapes.append(shp)

# Concatenar todos los shapefiles en un único GeoDataFrame
volumen = gpd.GeoDataFrame(pd.concat(all_shapes, ignore_index=True), crs=all_shapes[0].crs)

# Calcular la longitud de las geometrías y agregarla como columna
volumen['long_km'] = volumen.geometry.length / 1000  # Convertir a kilómetros

# Agregar columna 'grupo2' inicializada en -1 para indicar que aún no se ha asignado grupo
volumen['grupo2'] = -1
grupo_id = 0

# Agrupar por cada valor único en la columna 'dirección'
for direccion in volumen['dirección'].unique():
    subset = volumen[volumen['dirección'] == direccion].copy()
    subset_spatial_index = subset.sindex

    for i, row in subset.iterrows():
        if volumen.at[i, 'grupo2'] != -1:
            continue

        current_group = {i}
        processed = set()

        while current_group:
            idx = current_group.pop()
            processed.add(idx)

            line = subset.geometry[idx]
            start_point = Point(line.coords[0])
            end_point = Point(line.coords[-1])

            nearby_lines = subset.iloc[list(subset_spatial_index.intersection(start_point.buffer(10).bounds)) +
                                       list(subset_spatial_index.intersection(end_point.buffer(10).bounds))]

            nearby_lines = nearby_lines[(nearby_lines.geometry.distance(start_point) <= 10) |
                                        (nearby_lines.geometry.distance(end_point) <= 10)]

            for nearby_idx in nearby_lines.index:
                if nearby_idx not in processed:
                    current_group.add(nearby_idx)

        for idx in processed:
            volumen.at[idx, 'grupo2'] = grupo_id

        grupo_id += 1

# Filtrar líneas no unidas basadas en las preguntas del usuario
def filtrar_lineas(direccion):
    return volumen[(volumen['dirección'] == direccion) & (volumen['grupo2'].duplicated(keep=False) == False)]

if 'N - S' in volumen['dirección'].values:
    while True:
        respuesta_ns = input("¿Deseas eliminar líneas no unidas para dirección N - S? (sí/no): ")
        if respuesta_ns.lower() in ['sí', 'si']:
            volumen = volumen[~volumen.index.isin(filtrar_lineas('N - S').index)]
            break
        elif respuesta_ns.lower() == 'no':
            break
        else:
            print("No se capturó respuesta")

if 'E - W' in volumen['dirección'].values:
    while True:
        respuesta_ew = input("¿Deseas eliminar líneas no unidas para dirección E - W? (sí/no): ")
        if respuesta_ew.lower() in ['sí', 'si']:
            volumen = volumen[~volumen.index.isin(filtrar_lineas('E - W').index)]
            break
        elif respuesta_ew.lower() == 'no':
            break
        else:
            print("No se capturó respuesta")

direcciones_otros = volumen['dirección'].unique()
for direccion in direcciones_otros:
    if direccion not in ['N - S', 'E - W']:
        while True:
            respuesta_otros = input(f"¿Deseas eliminar líneas no unidas para dirección {direccion}? (sí/no): ")
            if respuesta_otros.lower() in ['sí', 'si']:
                volumen = volumen[~volumen.index.isin(filtrar_lineas(direccion).index)]
                break
            elif respuesta_otros.lower() == 'no':
                break
            else:
                print("No se capturó respuesta")

# Realizar un merge para las líneas con el mismo valor en 'grupo2' y conservar la dirección
volumen_merged = volumen.dissolve(by=['grupo2', 'dirección'], as_index=False)

# Calcular la longitud de las geometrías después de la disolución
volumen_merged['long_km'] = volumen_merged.geometry.length / 1000  # Recalcular long_km

# Asegurarse de que 'dirección' y 'long_km' estén disponibles para el siguiente paso
volumen_merged = volumen_merged[['grupo2', 'dirección', 'geometry', 'long_km']].copy()

# Calcular centroides antes de ordenar
volumen_merged['centroid'] = volumen_merged.geometry.centroid

# Asignar el nuevo ID en base a la prioridad de orden y dirección
volumen_ns = volumen_merged[volumen_merged['dirección'] == 'N - S'].sort_values(by='centroid', key=lambda g: g.apply(lambda geom: geom.x))
volumen_ew = volumen_merged[volumen_merged['dirección'] == 'E - W'].sort_values(by='centroid', key=lambda g: g.apply(lambda geom: -geom.y))
volumen_otros = volumen_merged[~volumen_merged['dirección'].isin(['N - S', 'E - W'])].sort_values(by='centroid', key=lambda g: g.apply(lambda geom: geom.y))

# Concatenar el orden final y asignar ID
volumen_ordenado = pd.concat([volumen_ns, volumen_ew, volumen_otros], ignore_index=True)
volumen_ordenado['ID'] = range(1, len(volumen_ordenado) + 1)

# Conservar solo las columnas ID, dirección y long_km
volumen_final = volumen_ordenado[['ID', 'dirección', 'long_km', 'geometry']]

# Crear un GeoDataFrame para almacenar los puntos extremos
# No se guardará el shapefile de Puntos_Extremos
puntos_extremos = gpd.GeoDataFrame(columns=['ID', 'tipo', 'geometry'], crs=volumen_final.crs)

# Agregar puntos extremos basados en la dirección
for idx, row in volumen_final.iterrows():
    puntos = []

    # Obtener las coordenadas de cada segmento según el tipo de geometría
    if row.geometry.geom_type == 'LineString':
        coords = list(row.geometry.coords)
    elif row.geometry.geom_type == 'MultiLineString':
        coords = [pt for line in row.geometry.geoms for pt in line.coords]
    else:
        continue  # Ignorar geometrías no compatibles

    # Procesar según la etiqueta de dirección
    if row['dirección'] == 'E - W':
        # Para 'E - W': seleccionar puntos extremos en X
        max_x_point = Point(max(coords, key=lambda c: c[0]))  # Punto con X máximo
        min_x_point = Point(min(coords, key=lambda c: c[0]))  # Punto con X mínimo
        puntos.append({'ID': row['ID'], 'tipo': 'max_x', 'geometry': max_x_point})
        puntos.append({'ID': row['ID'], 'tipo': 'min_x', 'geometry': min_x_point})

    else:
        # Para 'N - S' u otras direcciones: seleccionar puntos extremos en Y
        max_y_point = Point(max(coords, key=lambda c: c[1]))  # Punto con Y máximo
        min_y_point = Point(min(coords, key=lambda c: c[1]))  # Punto con Y mínimo
        puntos.append({'ID': row['ID'], 'tipo': 'max_y', 'geometry': max_y_point})
        puntos.append({'ID': row['ID'], 'tipo': 'min_y', 'geometry': min_y_point})

    # Agregar los puntos al GeoDataFrame utilizando pd.concat
    puntos_extremos = pd.concat([puntos_extremos, gpd.GeoDataFrame(puntos, crs=volumen_final.crs)], ignore_index=True)

# Crear líneas a partir de los puntos extremos
lineas = []

# Agrupar puntos extremos por ID
for id_val in puntos_extremos['ID'].unique():
    subset = puntos_extremos[puntos_extremos['ID'] == id_val]
    if len(subset) >= 2:  # Debe haber al menos 2 puntos para formar una línea
        coords = list(subset.geometry.apply(lambda geom: (geom.x, geom.y)))
        line = LineString(coords)
        lineas.append({'ID': id_val, 'geometry': line})

# Crear un GeoDataFrame de líneas
lineas_gdf = gpd.GeoDataFrame(lineas, crs=volumen_final.crs)

# Agregar la columna 'dirección' al GeoDataFrame de líneas
lineas_gdf['dirección'] = volumen_final.loc[lineas_gdf['ID'] - 1, 'dirección'].values

# Guardar el shapefile de líneas
lineas_gdf.to_file(lineas_file, driver='ESRI Shapefile')

# Eliminar capas Puntos_Extremos y Volumen al final
del puntos_extremos
del volumen

print("Shapefile de líneas guardado exitosamente.")
