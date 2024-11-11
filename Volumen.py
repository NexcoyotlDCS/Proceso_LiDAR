import os
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
import pandas as pd
from mpl_interactions import panhandler, zoom_factory
from matplotlib.widgets import RectangleSelector, Button
from pykml.factory import KML_ElementMaker as KML
from lxml import etree

# Configuración de rutas
script_dir = os.path.dirname(os.path.abspath(__file__))
lineas_path = os.path.join(script_dir, 'Volumen de obra', 'Lineas.shp')
volumen_total_path = os.path.join(script_dir, 'Volumen de obra', 'VolumenTotal.txt')
kml_path = os.path.join(script_dir, 'Volumen de obra', 'Lineas.kml')
puntos_path = os.path.join(script_dir, 'Volumen de obra', 'Puntos.shp')
area_txt_path = os.path.join(script_dir, 'Volumen de obra', 'Área.txt')  # Archivo de área

# Preguntar si se desea aplicar una codificación específica
while True:
    codificacion = input("¿Desea aplicar una codificación específica para leer el shapefile? (si/no): ").strip().lower()
    if codificacion in ("si", "no"):
        break
    print("Por favor, ingrese una respuesta válida ('si' o 'no').")

# Leer el shapefile con o sin codificación
if codificacion == "si":
    while True:
        encoding_option = input("Seleccione la codificación:\n1. latin1\n2. utf-8\nIngrese su opción (1 o 2): ").strip()
        if encoding_option == "1":
            encoding = "latin1"
            break
        elif encoding_option == "2":
            encoding = "utf-8"
            break
        print("Por favor, ingrese una opción válida (1 o 2).")

    lineas_gdf = gpd.read_file(lineas_path, encoding=encoding)
else:
    lineas_gdf = gpd.read_file(lineas_path)



lineas_gdf['Long_km'] = lineas_gdf.geometry.length / 1000  # Longitud en km

# Extracción de puntos extremos
max_min_points = []
for idx, row in lineas_gdf.iterrows():
    coords = list(row.geometry.coords)
    min_point = Point(coords[0])  # Punto de inicio
    max_point = Point(coords[-1])  # Punto de fin
    max_min_points.extend([(min_point, 'Min', idx), (max_point, 'Max', idx)])

points_df = pd.DataFrame(max_min_points, columns=['geometry', 'type', 'line_id'])
points_gdf = gpd.GeoDataFrame(points_df, geometry='geometry', crs=lineas_gdf.crs)

# Variables de selección de puntos
selected_points = []
applied_selection = False

# Funciones de selección de puntos
def onselect(eclick, erelease):
    x_min, x_max = sorted([eclick.xdata, erelease.xdata])
    y_min, y_max = sorted([eclick.ydata, erelease.ydata])

    for i, point in enumerate(points_gdf.geometry):
        if x_min <= point.x <= x_max and y_min <= point.y <= y_max:
            if i not in selected_points:
                selected_points.append(i)
    update_plot()

def update_plot():
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    ax.clear()
    colors = ['blue' if i not in selected_points else 'red' for i in range(len(points_gdf))]
    points_gdf.plot(ax=ax, color=colors, label='Puntos Máximos y Mínimos')

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_title("Selecciona los puntos para excluir", pad=20)
    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")

    if any(colors):
        plt.legend(['Puntos Máximos y Mínimos'], loc='upper right')

    plt.draw()

def export_points():
    # Pedir al usuario el nombre del archivo
    nombre_archivo = input("Ingrese el nombre para el archivo de puntos exportado (sin extensión): ")
    export_path = os.path.join(script_dir, 'Volumen de obra', f"{nombre_archivo}.shp")

    # Exportar solo puntos no seleccionados
    export_gdf = points_gdf.drop(selected_points)
    print("Exportando solo puntos no seleccionados.")
    export_gdf.to_file(export_path, driver='ESRI Shapefile')
    print(f"Capa de puntos exportada exitosamente a {export_path}.")

# Funciones de botones
def on_button_unmark(event):
    selected_points.clear()
    update_plot()

def on_button_export(event):
    export_points()

# Función para generar el polígono
def generate_polygon(event):
    # Filtrar solo los puntos que no han sido seleccionados
    available_points = points_gdf.drop(selected_points)

    # Crear columnas 'x' y 'y' con las coordenadas de cada punto
    available_points['x'] = available_points.geometry.x
    available_points['y'] = available_points.geometry.y

    # Filtrar y ordenar puntos máximos en función de 'x'
    max_points = available_points[available_points['type'] == 'Max'].sort_values(by='x')
    min_points = available_points[available_points['type'] == 'Min']

    # Verificar si hay puntos máximos disponibles
    if max_points.empty:
        print("No hay puntos máximos disponibles para generar el polígono.")
        return

    # Reproyectar a un CRS proyectado para medir distancias
    projected_gdf = available_points.copy()
    max_points_proj = projected_gdf[projected_gdf['type'] == 'Max'].sort_values(by='x')
    min_points_proj = projected_gdf[projected_gdf['type'] == 'Min']

    # Ordenar puntos máximos
    ordered_points = [max_points_proj.iloc[0]]
    remaining_max_points = max_points_proj.iloc[1:].copy()

    while not remaining_max_points.empty:
        last_point = ordered_points[-1].geometry
        distances = remaining_max_points.distance(last_point)

        # Seleccionar el punto más cercano
        next_point_index = distances.idxmin()
        next_point = remaining_max_points.loc[next_point_index]
        ordered_points.append(next_point)
        remaining_max_points = remaining_max_points.drop(next_point.name)

    # Agregar puntos mínimos en orden
    remaining_min_points = min_points_proj.copy()
    while not remaining_min_points.empty:
        last_point = ordered_points[-1].geometry
        distances = remaining_min_points.distance(last_point)

        # Seleccionar el punto más cercano
        next_point_index = distances.idxmin()
        next_point = remaining_min_points.loc[next_point_index]
        ordered_points.append(next_point)
        remaining_min_points = remaining_min_points.drop(next_point.name)

    # Cerrar el polígono uniendo el último punto mínimo al primer punto máximo
    polygon_points = [point.geometry for point in ordered_points] + [ordered_points[0].geometry]
    polygon_geom = Polygon([[p.x, p.y] for p in polygon_points])

    # Crear GeoDataFrame para el polígono
    area_gdf = gpd.GeoDataFrame(geometry=[polygon_geom], crs=projected_gdf.crs)

    # Guardar como KML
    area_gdf.to_file(os.path.join(script_dir, 'Volumen de obra', 'Area.kml'), driver='KML')
    print("Polígono generado y guardado como 'Area.kml'.")

    # Calcular el área en km² y hectáreas
    area_km2 = area_gdf.geometry.area.iloc[0]  # Área en km²
    area_ha = area_km2 / 10000  # Convertir a hectáreas

    # Guardar el área en un archivo de texto
    with open(area_txt_path, 'w') as area_file:
        area_file.write(f"Área en km²: {area_km2:.3f}\n")
        area_file.write(f"Área en hectáreas: {area_ha:.3f}\n")
    print(f"Archivo de área guardado en {area_txt_path}.")

# Configuración del gráfico y los botones
fig, ax = plt.subplots()
points_gdf.plot(ax=ax, color='blue', label='Puntos Máximos y Mínimos')
plt.title("Selecciona los puntos para excluir", pad=20)
plt.xlabel("Coordenada X")
plt.ylabel("Coordenada Y")

# Agregar interacción
zoom_factory(ax)
pan = panhandler(fig)  # Conectar a la figura en lugar de a los ejes

# Crear el RectangleSelector
rect_selector = RectangleSelector(ax, onselect, useblit=True,
                                  button=[1], minspanx=5, minspany=5, spancoords='pixels')

ax_button_unmark = plt.axes([0.91, 0.01, 0.1, 0.075])
button_unmark = Button(ax_button_unmark, 'Desmarcar')
button_unmark.on_clicked(on_button_unmark)

ax_button_export = plt.axes([0.01, 0.01, 0.1, 0.075])
button_export = Button(ax_button_export, 'Exportar')
button_export.on_clicked(on_button_export)

ax_button_generate_polygon = plt.axes([0.11, 0.01, 0.1, 0.075])
button_generate_polygon = Button(ax_button_generate_polygon, 'Generar Polígono')
button_generate_polygon.on_clicked(generate_polygon)

plt.show()

# Generar KML de Lineas y archivo VolumenTotal.txt al final
lineas_gdf = lineas_gdf.to_crs(epsg=4326)
kml_doc = KML.kml(
    KML.Document(
        KML.name("Lineas"),
        *[KML.Placemark(
            KML.name(f"Linea {row['ID']}"),
            KML.description(
                f"Dirección: {row['dirección']}\n"
                f"Longitud: {row['Long_km']:.3f} km\n" +
                "\n".join([f"{col}: {row[col]}" for col in lineas_gdf.columns if col not in ['geometry', 'ID', 'dirección', 'Long_km']])
            ),
            KML.LineString(
                KML.coordinates(" ".join(f"{x},{y}" for x, y in row.geometry.coords))
            )
        ) for _, row in lineas_gdf.iterrows()]
    )
)
with open(kml_path, "wb") as kml_file:
    kml_file.write(etree.tostring(kml_doc, pretty_print=True))
print(f"Archivo KML de Lineas guardado en {kml_path}.")

with open(volumen_total_path, 'w') as volumen_total_file:
    volumen_total_file.write("Volumen de Obra:\n")
    total_km = lineas_gdf['Long_km'].sum()
    for _, row in lineas_gdf.iterrows():
        volumen_total_file.write(f"Linea {row['ID']}: {row['Long_km']:.3f} km\n")
    volumen_total_file.write(f"\nTotal de Longitud en km: {total_km:.3f}\n")
print(f"Archivo VolumenTotal.txt guardado en {volumen_total_path}.")
