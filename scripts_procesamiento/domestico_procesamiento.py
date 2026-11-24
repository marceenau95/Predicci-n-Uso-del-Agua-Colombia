# Importar librerias 
import pandas as pd
import numpy as np
from pathlib import Path
from utilidades import imputar_consumo_servicios
from utilidades import cod_divipola

# Leer base de datos limpia de la SUPERSERVICIOS
ruta_salida = Path(__file__).resolve().parent.parent / 'procesed_data'
ruta_raw = Path(__file__).resolve().parent.parent / 'raw_data'
df = pd.read_parquet(ruta_salida / 'consumo_agua_servicios_domestica.parquet')

# Seleccionar solo los servicios de interés: Bajo-Bajo, Bajo,
# Medio-bajo, Medio, Medio-Alto y Alto
df_domestico = df[df['CLASE_DE_USO'].isin(['Bajo-Bajo', 'Bajo', 'Medio-Bajo',
                                         'Medio','Medio-Alto', 'Alto'])]
# Eliminar duplicados 
df_domestico = df_domestico.drop_duplicates(subset=['cod_mplity', 'AÑO','MES','CONSUMO M3','EMPRESA'], keep='first')
# Ajustar códigos de municipio que no existen dentro del DANE
df_domestico['cod_mplity'] = df_domestico['cod_mplity'].replace({
    '66450': '66045',
    '15266': '15226',
    '25004': '25001'
})

# Se verifican valores de consumo menores a 11 m3, que es el mínimo consumo por suscriptor al mes
df_domestico[df_domestico['CONSUMO M3'] < 11]

# Se imputan valores de consumo menores a 11 m3 con los valores de modulos de consumo doméstico
# de la Resolucion Resolucion_CRA_750_de_2016 de acuerdo a la altitud del municipio y 
# y el año.

# Importar altitud de los municipios
df_altitud = pd.read_excel(ruta_raw / 'Altitud.xlsx')

# Eliminar valores nulos de altitud
df_altitud = df_altitud.dropna(subset=['Altitud msnm'])

