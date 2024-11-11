import glob

def renombrar_columna(archivo_entrada, archivo_salida):
    with open(archivo_entrada, 'r') as entrada:
        lineas = entrada.readlines()

    # Eliminar las primeras 6 líneas
    lineas = lineas[6:]

    # Renombrar la primera columna
    for i in range(len(lineas)):
        if len(lineas[i]) >= 8:  # Asegúrate de que la línea tenga al menos 8 caracteres
            nuevo_nombre = 'DSC{0}.JPG{1}'.format(str(i+1).zfill(5), lineas[i][8:])
            lineas[i] = nuevo_nombre  # Modificación aquí
        else:
            print(f"Advertencia: La línea {i+1} tiene menos de 8 caracteres y no se modificará.")

    # Escribir en el archivo de salida
    with open(archivo_salida, 'w') as salida:
        salida.writelines(lineas)

# Obtener una lista de todos los archivos que comienzan con "Camara_v"
archivos_entrada = glob.glob('Camara_v*.txt')

# Procesar cada archivo
for archivo_entrada in archivos_entrada:
    archivo_salida = archivo_entrada.replace('.txt', '__.txt')  # Nombre de archivo de salida
    renombrar_columna(archivo_entrada, archivo_salida)

    print(f"Archivo: {archivo_entrada} modificado a: {archivo_salida} ")