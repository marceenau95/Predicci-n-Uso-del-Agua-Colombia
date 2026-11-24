import pandas as pd
import numpy as np
import glob
import re
import os
from pathlib import Path
# Leer archivos de excel de la ruta
ruta = Path(__file__).resolve().parent.parent /'raw_data' / 'Suscriptores'
todos_los_archivos = glob.glob(str(ruta / "*.xlsx"))
# Concatenar archivos en un solo df, extraer año del nombre del archivo
dfs =[]
print("Archivos encontrados:")
for archivo in todos_los_archivos:
    print(os.path.basename(archivo))

for archivo in todos_los_archivos:

    nombre_archivo = os.path.basename(archivo)

    print(f"\nLeyendo: {nombre_archivo}")

    try:

        # Leer archivo
        df_temp = pd.read_excel(archivo)

        # Extraer año
        match = re.search(r'(\d{4})', nombre_archivo)

        if match:
            año = int(match.group(1))
                       # Agregar año
            df_temp["Año"] = año

            # Agregar a lista
            dfs.append(df_temp)

            print(f"✓ Año {año} leído correctamente")
            print(f"  Filas: {len(df_temp)}")
            print(f"  Columnas: {len(df_temp.columns)}")

        else:
            print("⚠ No se encontró el año en el nombre")

    except Exception as e:
            print(f"❌ ERROR leyendo {nombre_archivo}")
            print(f"   {e}")


# Concatenar
df = pd.concat(dfs, ignore_index=True)

print("\nDataFrame final:")
print(df.shape)

print("\nAños encontrados:")
print(sorted(df["Año"].unique()))
print(df[df['Código Dane'].isnull()])

# Separar Df por sector de servicios, normalizar dfs
df = df.rename(columns={'Código Dane':'cod_mplity','Año':'year'})
df['cod_mplity'] = df['cod_mplity'].astype(int).astype(str).str.zfill(5)
suscriptores_residenciales = df[['year','cod_mplity','Total Residencial']]
suscriptores_comerciales = df[['year','cod_mplity','Comercial']]
suscriptores_oficial = df[['year','cod_mplity','Oficial']]
suscriptores_otros = df[['year','cod_mplity','Otros']]
# Diccionario de nombres
nombres = {'Total Residencial':'Suscriptores','Comercial':'Suscriptores','Oficial':'Suscriptores','Otros':'Suscriptores'}
# Generar una lista de tablas
servicios =[suscriptores_residenciales,suscriptores_comerciales,suscriptores_oficial,suscriptores_otros]
# Groupby por municipio para determinar el numero de suscriptores
agrupacion =[]
for tabla in servicios:
    tabla_renombrada = tabla.rename(columns = nombres)
    tabla_agrupada = tabla_renombrada.groupby(['year','cod_mplity'])['Suscriptores'].sum().reset_index()
    agrupacion.append(tabla_agrupada)
# Tablas finales
suscriptores_residenciales = agrupacion[0]
suscriptores_comerciales = agrupacion[1]
suscriptores_oficial = agrupacion[2]
suscriptores_otros = agrupacion[3]

#Incluir columna de activity_code

suscriptores_residenciales['activity_code'] ="domestic_water_use"
suscriptores_comerciales['activity_code']= "commercial_water_use"
suscriptores_oficial['activity_code'] = "public_water_use"
suscriptores_otros['activity_code'] = "other_water_use"

# Concatenar tablas de Servicios
suscriptores_servicios = pd.concat([suscriptores_comerciales,suscriptores_oficial,suscriptores_otros])

# Exportar df a parquet
ruta_salida = Path(__file__).resolve().parent.parent /'procesed_data'
suscriptores_residenciales.to_parquet(ruta_salida / 'susc_residenciales.parquet', index=False)
suscriptores_servicios.to_parquet(
    ruta_salida / 'susc_servicios.parquet',
    index=False,)