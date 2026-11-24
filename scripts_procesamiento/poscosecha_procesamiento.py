# Importar librerias 
import pandas as pd
import numpy as np
from utilidades import cod_divipola
from pathlib import Path

# Lectura de base de datos de las Evaluaciones Agropecuarias Municipales (EVAS)
# de la pagina ofical de la UPRA https://upra.gov.co/es-co/eva#produccion
ruta = Path(__file__).resolve().parent.parent / 'raw_data'
ruta_bd1 = ruta / 'Base_Datos_cultivos_2007-2018.xlsx'
ruta_bd2 = ruta / 'Base_Datos_cultivos_2019-2024.xlsx'
bd_1 = pd.read_excel(ruta_bd1, skiprows=1)
bd_2 = pd.read_excel(ruta_bd2)

# seleccion de columnas importantes limpieza y normalización de nombres
bd_1.columns = bd_1.columns.str.replace('\n', ' ')
bd_1 = bd_1.drop(columns=['ESTADO FISICO PRODUCCION','NOMBRE CIENTIFICO','Unnamed: 17'])
bd_1.columns = bd_1.columns.str.replace('.', '')
bd_1.columns = bd_1.columns.str.normalize('NFKD') \
                       .str.encode('ascii', errors='ignore') \
                       .str.decode('utf-8') \
                       .str.upper()
bd_1.columns = bd_1.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
print(bd_1.info())
bd_2.columns = bd_2.columns.str.replace('\n', ' ')
bd_2.columns = bd_2.columns.str.replace('.', '')
bd_2.columns = bd_2.columns.str.normalize('NFKD') \
                       .str.encode('ascii', errors='ignore') \
                       .str.decode('utf-8') \
                       .str.upper()
bd_2.columns = bd_2.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
print(bd_2.info())

# Concatenar dos bases de datos
df_cultivos = pd.concat([bd_1, bd_2], ignore_index=True)

# Normalización de codigo DIVPIPOLA
df_cultivos['COD MUN'] = df_cultivos['COD MUN'].astype(str).str.zfill(5)

# Limpieza valores de la base de datos normalización de valores de cultivo
df_cultivos['CULTIVO'] = df_cultivos['CULTIVO'].astype(str) \
                             .str.normalize('NFKD') \
                             .str.encode('ascii', errors='ignore') \
                             .str.decode('utf-8') \
                             .str.lower()
# Normalizar banano de exportación
def norm_sist_prod(valor):
    if valor == 'Banano de exportación'or valor == 'BANANO EXPORTACION' :
        return 'banano exportacion'
    else:
        return valor

df_cultivos['DESAGREGACION REGIONAL Y/O SISTEMA PRODUCTIVO'] = df_cultivos['DESAGREGACION REGIONAL Y/O SISTEMA PRODUCTIVO'].apply(norm_sist_prod)
#---------------------------------------------------------
# CULTIVO DE PALMA
#------------------------------------------------------------

#Seleccionar solo cultivo de Palma
df_palma = df_cultivos[df_cultivos['CULTIVO']=='palma de aceite']
# Eliminar registros duplicados si existen
df_palma = df_palma.drop_duplicates(subset=['ANO','COD MUN','PRODUCCION (T)'], keep='first')

# agrupar df de palma por año y municipio
df_palma_agrupado = df_palma.groupby(
    ['ANO','COD MUN','DEPARTAMENTO','CULTIVO'],as_index=False)[['AREA SEMBRADA (HA)','AREA COSECHADA (HA)','PRODUCCION (T)']].sum().sort_values(
        by=['ANO','COD MUN'])

# Filtrar por registros de 2008 en adelante
df_palma_agrupado = df_palma_agrupado[df_palma_agrupado['ANO']>2007]

# Modulos de consumo de palma por municipio productor
modulos_palma = {
    "05172": 4.797,
    "13442": 9.094,
    "13580": 6.473,
    "13670": 6.473,
    "18094": 5.628,
    "20011": 4.845,
    "20013": 4.797,
    "20238": 4.895,
    "20250": 4.797,
    "20383": 4.892,
    "20621": 2.693,
    "20710": 10.441,
    "20770": 6.285,
    "25572": 6.473,
    "47053": 3.344,
    "47189": 4.797,
    "47268": 4.956,
    "47980": 4.948,
    "50006": 5.176,
    "50110": 5.054,
    "50124": 4.795,
    "50226": 4.706,
    "50313": 5.449,
    "50325": 5.449,
    "50568": 5.449,
    "50590": 5.449,
    "50680": 5.877,
    "52835": 5.624,
    "54261": 6.473,
    "54810": 6.473,
    "68573": 4.463,
    "68575": 8.090,
    "68655": 3.500,
    "68689": 5.604,
    "85139": 5.616,
    "85225": 5.604,
    "85230": 5.449,
    "85410": 5.527,
    "85440": 6.330,
    "99524": 5.449,
    "99624": 5.604
}
# Asignar modulos de uso de agua de acuerdo al codigo de municipio
def modulo_palma(municipio):
    '''Función para asignar modulos de consumo de agua de acuerdo al código 
    divipola del municipio y los valores del diccionario modulos_palma'''
    for clave,modulo in modulos_palma.items():
        if clave in municipio:
            return modulo
    return None
df_palma_agrupado['modulo_consumo_m3_ton'] = df_palma_agrupado['COD MUN'].apply(modulo_palma)

# Para los registros con municipios que no tienen modulo de consumo
# se asignar modulos por dempartamento
modulos_departamentos = {
    "antioquia": 4.797,
    "bolivar": 7.347,
    "caqueta": 5.628,
    "casanare": 5.705,
    "cesar": 5.779,
    "cundinamarca": 6.473,
    "magdalena": 4.511,
    "meta": 5.267,
    "narino": 5.624,
    "norte de santander": 6.473,
    "santander": 5.414,
    "vichada": 5.527
}
def modulo_depart(departamento):
    '''Función para rellenar los valores vacios de modulo a partir 
    del diccionario de modulos_departamentos
    
    '''
    if pd.isna(departamento):
        return None
    for clave,modulo in modulos_departamentos.items():
        if clave in departamento:
            return modulo
    return 
df_palma_agrupado['modulo_consumo_m3_ton'] =df_palma_agrupado['modulo_consumo_m3_ton'].fillna(
    df_palma_agrupado['DEPARTAMENTO'].apply(modulo_depart))

# Se descartar los registros con producciones de 0 y los registros
# de los departamentos Tolimna, Caldas y Putumayo ya que son productores
#menores y no se tienen modulos de consumo verificados

df_palma_agrupado = df_palma_agrupado[df_palma_agrupado['PRODUCCION (T)'] != 0]
df_palma_agrupado = df_palma_agrupado[~df_palma_agrupado['DEPARTAMENTO'].isin(['tolima', 'caldas', 'putumayo'])]

# Asignar modulo de consumo a demás departamentos que no tienen modulo como la mediana de los modulos de los departamentos que si tienen modulo
modulo_mediana = df_palma_agrupado['modulo_consumo_m3_ton'].median()
df_palma_agrupado['modulo_consumo_m3_ton'] = df_palma_agrupado['modulo_consumo_m3_ton'].fillna(modulo_mediana)
# Calcular consumo de agua por municipio y año
df_palma_agrupado['consumo_agua_m3'] = df_palma_agrupado['PRODUCCION (T)'] * df_palma_agrupado['modulo_consumo_m3_ton']

print (" Cultivo de palma procesado y calculo de consumo de agua por municipio y año finalizado")

#---------------------------------------------------------
# CULTIVO DE BANANO
#------------------------------------------------------------
# Seleccionar cultivo de banano
df_banano = df_cultivos[(df_cultivos['CULTIVO']=='banano') &
                         (df_cultivos[
                            'DESAGREGACION REGIONAL Y/O SISTEMA PRODUCTIVO']=='banano exportacion')]
#Eliminar registros duplicados si existen
df_banano = df_banano.drop_duplicates(
    subset=['ANO','COD MUN','PRODUCCION (T)'], keep='first')

# Agrupar registros por año y  municipio
df_banano_agrupado = df_banano.groupby(
    ['ANO','COD MUN','DEPARTAMENTO','CULTIVO'],
    as_index=False)[['AREA SEMBRADA (HA)','AREA COSECHADA (HA)','PRODUCCION (T)']].sum().sort_values(
        by=['ANO','COD MUN'])
# Filtrar por años superiores a 2007
df_banano_agrupado = df_banano_agrupado[df_banano_agrupado['ANO']>2007]
# Asignar una zona bananera según departamento productor
def zona_bananera(departamento):
    '''Función para asignar zona bananera a los registros'''
    if departamento in ['magdalena','la guajira']:
        return 'magdalena'
    else:
        return 'uraba'

df_banano_agrupado['zona_bananera'] = df_banano_agrupado['DEPARTAMENTO'].apply(
    zona_bananera)

def modulos_banano(zona_bananera):
    '''Función para asignar modulos de consumo según
    zona bananera'''
    if zona_bananera == 'magdalena':
        return 400
    else:
        return 60
df_banano_agrupado['modulo_consumo'] = df_banano_agrupado['zona_bananera'].apply(modulos_banano)
df_banano_agrupado['uso_de_agua_m3'] = df_banano_agrupado['AREA COSECHADA (HA)']*df_banano_agrupado['modulo_consumo']

print(" Cultivo de banano procesado y calculo de consumo de agua por municipio y año finalizado")
#---------------------------------------------------------
# CULTIVO DE CAFÉ
#------------------------------------------------------------

# Seleccionar cultivo de café
df_cafe = df_cultivos[(df_cultivos['CULTIVO']=='cafe')]
# Filtrar datos entre 2008 a 2018
df_cafe_2008_2018 = df_cafe[(df_cafe['ANO']>=2008) & (df_cafe['ANO']<=2018)]
df_cafe_agrupado = df_cafe_2008_2018.groupby(
    ['ANO','COD MUN','CULTIVO'],as_index=False)[['AREA SEMBRADA (HA)','AREA COSECHADA (HA)','PRODUCCION (T)']].sum().sort_values(
    by=['ANO','COD MUN'])
# Calculo café pergamino y uso de agua para café cosechado en beneficios ecológicos y no ecológicos
df_cafe_agrupado['produccion_pergamino_ton'] = df_cafe_agrupado['PRODUCCION (T)'] / 5
df_cafe_agrupado['produccion_pergamino_kg'] = df_cafe_agrupado['produccion_pergamino_ton'] * 1000
df_cafe_agrupado['produccion_necologico_kg'] = df_cafe_agrupado['produccion_pergamino_kg'] * 0.7
df_cafe_agrupado['produccion_benecologico_kg']= df_cafe_agrupado['produccion_pergamino_kg'] * 0.3
df_cafe_agrupado['uso_agua_noecologico'] = df_cafe_agrupado['produccion_necologico_kg'] * 45
df_cafe_agrupado['uso_agua_ecologico'] = df_cafe_agrupado['produccion_benecologico_kg'] * 1
df_cafe_agrupado['uso_agua_total'] = (df_cafe_agrupado['uso_agua_noecologico'] + df_cafe_agrupado['uso_agua_ecologico'])/1000
df_cafe_agrupado['modulo_consumo'] =round((df_cafe_agrupado['uso_agua_total']/df_cafe_agrupado['PRODUCCION (T)']),2)
df_cafe_agrupado = df_cafe_agrupado[['ANO','COD MUN','CULTIVO','AREA SEMBRADA (HA)','AREA COSECHADA (HA)','PRODUCCION (T)','uso_agua_total','modulo_consumo']]

# Calculo de uso de agua para 2019 a 2024
df_cafe_2019_2024 = df_cafe[
    (df_cafe['ANO'] >= 2019)
    & (df_cafe['ANO'] <= 2024)
    & (~df_cafe['DEPARTAMENTO'].isin(['cordoba', 'sucre', 'arauca']))
]
df_cafe_2019_2024_agrupado = df_cafe_2019_2024.groupby(
    ['ANO','COD MUN','DEPARTAMENTO','CULTIVO'],as_index=False)[[
        'AREA SEMBRADA (HA)','AREA COSECHADA (HA)','PRODUCCION (T)'
        ]].sum().sort_values(by=['ANO','COD MUN'])

df_cafe_2019_2024_agrupado['produccion_pergamino_kg'] = df_cafe_2019_2024_agrupado[
                                        'PRODUCCION (T)']*1.26*1000
# Modulos de consumo por tipo de beneficiadero
# Modulos de consumo de agua por tipo de beneficiadero
modulos_consumo = {
    'C1': 40.0,
    'C2': 40.0,
    'C3': 37.6,
    'C4': 37.6,
    'T1': 20.9,
    'T2': 37.6,
    'T3': 20.9,
    'T4': 3.6,
    'E1': 6.0,
    'E2': 6.0,
    'E3': 2.6,
    'E4': 6.0,
    'E5': 2.6,
    'E6': 6.0,
    'E7': 2.6,
    'E8': 0.4,
    'SC': 40.0
}
df_modulos_consumo = pd.DataFrame(
    list(modulos_consumo.items()),
      columns=['tipo_beneficiadero', 'Modulo_consumo'])
# Distribución porcentual de beneficiaderos por departamento
datos_distribucion = {'AÑO':[2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,2019,
                             2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020,2020],
    'DEPARTAMENTO': [
        'ANTIOQUIA', 'ARAUCA', 'BOLÍVAR', 'BOYACÁ', 'CALDAS', 'CAQUETÁ', 'CASANARE', 
        'CAUCA', 'CESAR', 'CHOCÓ', 'CUNDINAMARCA', 'HUILA', 'LA GUAJIRA', 'MAGDALENA', 
        'META', 'NARIÑO', 'NORTE DE SANTANDER', 'PUTUMAYO', 'QUINDÍO', 'RISARALDA', 
        'SANTANDER', 'TOLIMA', 'VALLE DEL CAUCA','ANTIOQUIA', 'ARAUCA', 'BOLÍVAR', 'BOYACÁ', 'CALDAS', 'CAQUETÁ', 'CASANARE', 
        'CAUCA', 'CESAR', 'CHOCÓ', 'CUNDINAMARCA', 'HUILA', 'LA GUAJIRA', 'MAGDALENA', 
        'META', 'NARIÑO', 'NORTE DE SANTANDER', 'PUTUMAYO', 'QUINDÍO', 'RISARALDA', 
        'SANTANDER', 'TOLIMA', 'VALLE DEL CAUCA'
    ],
    'C1': [0.031,0.0,0.0,0.006,0.012,0.123,0.05,0.03,0.241, 0.011,0.035,0.04,0.536,0.064,0.065, 0.005,0.06,0.0,0.006,0.03,0.004,0.227,0.029,
           0.0350, 0.0000, 0.0000, 0.0050, 0.0110, 0.1270, 0.0420, 0.0320, 0.2150, 0.0100, 0.0330, 0.0410, 0.5300, 0.0590, 0.0560, 0.0040, 0.0620, 0.0000, 0.0060, 0.0290, 0.0040, 0.2180, 0.0300],
    'C2': [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.001,0.002,0.0,0.009,0.00,0.001,0.00,0.0,0.0,0.001,0.0,0.001,0.0,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0010, 0.0020, 0.0000, 0.0070, 0.0000, 0.0010, 0.0000, 0.000, 0.0000, 0.0010, 0.0000, 0.0010, 0.0000],
    'C3': [0.008,0.0,0.048,0.001,0.01,0.0,0.039,0.005,0.01,0.007,0.008,0.006,0.0,0.014,0.021,0.004,0.017,0.0,0.005,0.011,0.004,0.014,0.008,
       0.0070, 0.0000, 0.0440, 0.0010, 0.0110, 0.0000, 0.0300, 0.0050, 0.0100, 0.0060, 0.0080, 0.0060, 0.0000, 0.0130, 0.0240, 0.0030, 0.0170, 0.0000, 0.0050, 0.0100, 0.0040, 0.0130, 0.0070 ],
    'C4': [0.002,0.0,0.0,0.003,0.0,0.0,0.0,0.003,0.012,0.0,0.002,0.001,0.001,0.03,0.0,0.002,0.02,0.0,0.002,0.002,0.002,0.001,0.004,
        0.0020, 0.0000, 0.000, 0.0020, 0.0000, 0.0090, 0.0000, 0.0020, 0.0130, 0.0000, 0.0020, 0.0010, 0.0010, 0.0270, 0.0000, 0.0020, 0.0020, 0.0000, 0.0010, 0.0020, 0.0020, 0.0010, 0.0040],
    'T1': [0.146,0.0,0.337,0.309,0.304,0.226,0.304,0.223,0.208,0.121,0.271,0.352,0.223,0.171,0.324,0.20,0.404,0.642,0.13,0.204,0.206,0.294,0.219,
        0.1560, 0.0000, 0.3500, 0.3100, 0.3030, 0.2040, 0.2830, 0.2320, 0.2330, 0.1370, 0.2740, 0.3520, 0.2240, 0.1680, 0.3450, 0.2050, 0.4010, 0.4850, 0.1300, 0.2040, 0.2070, 0.2980, 0.2180],
    'T2': [0.019,0.0,0.008,0.003,0.003,0.0,0.0,0.003,0.063,0.0,0.014,0.009,0.039,0.048,0.002,0.0,0.001,0.0,0.008,0.018,0.001,0.016,0.001,
        0.0200, 0.0000, 0.0110, 0.0030, 0.0030, 0.0000, 0.0000, 0.0040, 0.0590, 0.0000, 0.0150, 0.0080, 0.0400, 0.0470, 0.0050, 0.0000, 0.0010, 0.0000, 0.0100, 0.0160, 0.0010, 0.0170, 0.0110],
    'T3': [0.196,0.0,0.435,0.117,0.227,0.07,0.037,0.010,0.254,0.10,0.169,0.213,0.111,0.494,0.089,0.097,0.091,0.093,0.134,0.271,0.141,0.111,0.165,
        0.1960, 0.0000, 0.4410, 0.1110, 0.2200, 0.0750, 0.0290, 0.0950, 0.2570, 0.0960, 0.1660, 0.2110, 0.1120, 0.4990, 0.0690, 0.1020, 0.0910, 0.0840, 0.1360, 0.2700, 0.1410, 0.1140, 0.1590],
    'T4': [0.066,0.0,0.085,0.265,0.096,0.305,0.296,0.23,0.031,0.617,0.196,0.085,0.032,0.019,0.303,0.315,0.234,0.132,0.082,0.086,0.133,0.09,0.173,
        0.0740, 0.0000, 0.0840, 0.2820, 0.0980, 0.2930, 0.3480, 0.2350, 0.0380, 0.6190, 0.2010, 0.0880, 0.0350, 0.0200, 0.2680, 0.3210, 0.2340, 0.3090, 0.0840, 0.0920, 0.1410, 0.0910, 0.1780],
    'E1': [0.098,0.0,0.031,0.078,0.073,0.067,0.078,0.127,0.086,0.057,0.097,0.076,0.004,0.013,0.088,0.194,0.067,0.0,0.177,0.093,0.089,0.106,0.084,
        0.0940, 0.0000, 0.0220, 0.0740, 0.0720, 0.0730, 0.0670, 0.1240, 0.0800, 0.0530, 0.0970, 0.0760, 0.0050, 0.0130, 0.0690, 0.1830, 0.0670, 0.0000, 0.1710, 0.0920, 0.0870, 0.1060, 0.0860],
    'E2': [0.007,0.0,0.0,0.023,0.013,0.0,0.0,0.015,0.003,0.0,0.01,0.01,0.039,0.002,0.009,0.005,0.012,0.0,0.028,0.011,0.037,0.006,0.017,
        0.0070, 0.0000, 0.0000, 0.0210, 0.0140, 0.0020, 0.0000, 0.0120, 0.0030, 0.0000, 0.0090, 0.0110, 0.0000, 0.0020, 0.0070, 0.0050, 0.0120, 0.0000, 0.0270, 0.0100, 0.0340, 0.0060, 0.0180],
    'E3': [0.102,0.0,0.013,0.088,0.082,0.029,0.12,0.094,0.02,0.088,0.062,0.042,0.037,0.007,0.043,0.077,0.041,0.071,0.203,0.06,0.15,0.032,0.097,
        0.1020, 0.0000, 0.0070, 0.0870, 0.0840, 0.0290, 0.1690, 0.0950, 0.0200, 0.0780, 0.0600, 0.0410, 0.0400, 0.0090, 0.0660, 0.0760, 0.0400, 0.0780, 0.1990, 0.0580, 0.1480, 0.0330, 0.0970],
    'E4': [0.046,0.0,0.007,0.042,0.042,0.007,0.012,0.067,0.022,0.0,0.035,0.055,0.003,0.013,0.02,0.048,0.0250,0.006,0.046,0.074,0.04,0.03,0.056,
        0.0470, 0.0000, 0.0070, 0.0400, 0.0420, 0.0100, 0.0100, 0.0630, 0.0220, 0.000, 0.0340, 0.0530, 0.004, 0.0120, 0.0270, 0.0450, 0.0250, 0.0000, 0.0460, 0.0720, 0.0380, 0.0310, 0.0570],
    'E5': [0.175,0.0,0.0,0.043,0.091,0.022,0.005,0.058,0.024,0.0,0.058,0.053,0.002,0.04,0.005,0.029,0.017,0.031,0.076,0.095,0.115,0.029,0.083,
        0.1650, 0.0000, 0.0000, 0.0380, 0.0960, 0.0350, 0.0050, 0.0560, 0.0220, 0.000, 0.0550, 0.0510, 0.0020, 0.0480, 0.0130, 0.030, 0.0160, 0.0230, 0.0780, 0.0990, 0.1160, 0.0300, 0.0810],
    'E6': [0.01,0.0,0.0,0.01,0.003,0.023,0.003,0.008,0.003,0.0,0.004,0.012,0.0,0.006,0.0,0.003,0.007,0.0,0.019,0.006,0.014,0.01,0.011,
        0.010, 0.0000, 0.0000, 0.0110, 0.0030, 0.0380, 0.0030, 0.0080, 0.0030, 0.000, 0.0040, 0.0130, 0.0000, 0.0060, 0.000, 0.0030, 0.0070, 0.0000, 0.0170, 0.0070, 0.0130, 0.0090, 0.0100],
    'E7': [0.054,0.0,0.0,0.003,0.017,0.017,0.1,0.009,0.002,0.0,0.011,0.008,0.0,0.006,0.004,0.007,0.005,0.0,0.064,0.012,0.042,0.012,0.017,
        0.0480, 0.0000, 0.0000, 0.0030, 0.0140, 0.0140, 0.0010, 0.0090, 0.0010, 0.0000, 0.0130, 0.0080, 0.000, 0.0050, 0.0040, 0.0060, 0.0060, 0.0000, 0.0650, 0.0110, 0.0420, 0.0110, 0.0150],
    'E8': [0.007,0.0,0.007,0.0,0.003,0.0,0.0,0.0,0.0,0.0,0.001,0.004,0.0,0.001,0.0,0.001,0.001,0.0,0.002,0.002,0.001,0.003,0.001,
        0.005, 0.0000, 0.0000, 0.0020, 0.0000, 0.0010, 0.0000, 0.0000, 0.0000, 0.0000, 0.0010, 0.0040, 0.0000, 0.0010, 0.0000, 0.0010, 0.0010, 0.0000, 0.0010, 0.0030, 0.0010, 0.0030, 0.0010],
    'SC': [0.031,0.0,0.036,0.007,0.027,0.11,0.055,0.026,0.02,0.0,0.027,0.033,0.01,0.06,0.026,0.013,0.016,0.024,0.017,0.024,0.021,0.017,0.025,
        0.0330, 0.0000, 0.0360, 0.0070, 0.0270, 0.0890, 0.0150, 0.0270, 0.0220, 0.000, 0.0270, 0.0340, 0.0080, 0.0630, 0.0460, 0.0130, 0.0180, 0.0210, 0.0240, 0.0250, 0.0210, 0.0170, 0.0260]}
df_distribucion = pd.DataFrame(datos_distribucion)
df_dist_largo = df_distribucion.melt(
    id_vars=['AÑO', 'DEPARTAMENTO'],
    var_name='tipo_beneficiadero',
    value_name='porcentaje'
)

print(df_dist_largo.head(10))

# Unir los modulos de consumo con la distribución porcentual de beneficiaderos por departamento para calcular el modulo ponderado de consumo de agua por departamento y tipo de beneficiadero
df_modulos_consumo_ponderado = pd.merge(
                    df_modulos_consumo, 
                    df_dist_largo,
                      on='tipo_beneficiadero',
                      how = 'left')
df_modulos_consumo_ponderado['Modulo_consumo_ponderado'] = df_modulos_consumo_ponderado['Modulo_consumo'] * df_modulos_consumo_ponderado['porcentaje']
 #Calcular modulos de consumo por departamento sumando los modulos ponderados de consumo de agua por departamento y tipo de beneficiadero
df_modulos_consumo_departamento = df_modulos_consumo_ponderado.groupby(['AÑO','DEPARTAMENTO'], as_index=False)['Modulo_consumo_ponderado'].sum()
df_modulos_consumo_departamento = df_modulos_consumo_departamento.rename(columns={'Modulo_consumo_ponderado': 'modulo_ponderado_l/kg','AÑO':'ANO'})

df_modulos_consumo_departamento['DEPARTAMENTO'] = df_modulos_consumo_departamento['DEPARTAMENTO'].astype(str) \
                             .str.normalize('NFKD') \
                             .str.encode('ascii', errors='ignore') \
                             .str.decode('utf-8') \
                             .str.lower()

# Redondear columna de modulo_ponderado_l/kg
df_modulos_consumo_departamento['modulo_ponderado_l/kg'] = df_modulos_consumo_departamento['modulo_ponderado_l/kg'].round(4)

# Unir base de datos de café 2019-2024 con los modulos de consumo por departamento para calcular el consumo de agua por departamento y año
df_cafe_2019_2024_consumo = pd.merge(df_cafe_2019_2024_agrupado, df_modulos_consumo_departamento, on=['ANO','DEPARTAMENTO'], how='left')
df_cafe_2019_2024_consumo['uso_agua_total'] = df_cafe_2019_2024_consumo['produccion_pergamino_kg'] * df_cafe_2019_2024_consumo['modulo_ponderado_l/kg']/1000

df_cafe_2019_2024_consumo = df_cafe_2019_2024_consumo.rename(columns = {'modulo_ponderado_l/kg':'modulo_consumo'})
df_cafe_2019_2024_consumo = df_cafe_2019_2024_consumo[['ANO','COD MUN','CULTIVO','AREA SEMBRADA (HA)','AREA COSECHADA (HA)','PRODUCCION (T)','modulo_consumo','uso_agua_total']]

df_poscosecha_cafe = pd.concat([df_cafe_agrupado, df_cafe_2019_2024_consumo], ignore_index=True)

## Consolidación de la Base de datos de Poscosecha
df_banano_agrupado = df_banano_agrupado.rename(columns={'uso_de_agua_m3':'uso_agua_m3'})
df_palma_agrupado =df_palma_agrupado.rename(columns={'modulo_consumo_m3_ton':'modulo_consumo','consumo_agua_m3':'uso_agua_m3'})
df_poscosecha_cafe = df_poscosecha_cafe.rename(columns={'uso_agua_total':'uso_agua_m3'})

print("cultivo de café procesado y calculo de consumo de agua por municipio y año finalizado")

# Normalizar Base de datos

tablas_poscosecha =[df_palma_agrupado,df_banano_agrupado,df_poscosecha_cafe]
activity_name ={'palma de aceite':'Procesamiento fruto fresco Palma','cafe':'Poscosecha café','banano exportacion':'Poscosecha banano','banano':'Poscosecha banano'}
activity_code ={'palma de aceite':'palm_processing','cafe':'coffee_processing','banano exportacion':'banana_postharvest','banano':'banana_postharvest'}
source_activity ={'palma de aceite':'FEDEPALMA','cafe':'CENICAFE','banano exportacion':'UPRA','banano':'UPRA'}
factor_unit ={'palma de aceite':'m3/ton','cafe':'m3/ton','banano exportacion':'m3/ha','banano':'m3/ha'}
unit_activity ={'palma de aceite':'toneladas','cafe':'toneladas','banano exportacion':'hectareas','banano':'hectareas'}

# Importar codigos divipola
codigos_divipola = cod_divipola()

for i, tabla in enumerate(tablas_poscosecha):
    # Seleccionar columnas importantes
    tabla = tabla[['ANO','COD MUN','CULTIVO','AREA COSECHADA (HA)','PRODUCCION (T)','modulo_consumo','uso_agua_m3']]
    # 1. Agregar las columnas fijas
    tabla['sector_code'] = 'postharvest'
    tabla['sector_name'] = 'Poscosecha'
    tabla['unit_activity'] = tabla['CULTIVO'].map(unit_activity)
    tabla['factor_unit'] = tabla['CULTIVO'].map(factor_unit)
    tabla['activity_code'] = tabla['CULTIVO'].map(activity_code)
    tabla['activity_name'] = tabla['CULTIVO'].map(activity_name)
    tabla['source_activity'] = tabla['CULTIVO'].map(source_activity)
    tabla['activity_value'] = np.where(
        tabla['CULTIVO'].isin(['palma de aceite', 'cafe']),
        tabla['PRODUCCION (T)'],
        tabla['AREA COSECHADA (HA)']
            )
    # Ajustar decimales de columnas numéricas
    tabla['activity_value'] = tabla['activity_value'].round (2)
    tabla['modulo_consumo'] = tabla['modulo_consumo'].round (3)
    tabla['uso_agua_m3'] = tabla['uso_agua_m3'].round (2)
    # 3. Renombrar las columnas sobre el nuevo DataFrame unido
    tabla.rename(
        columns={
            'ANO': 'year', 
            'COD MUN': 'cod_mplity', 
            'uso_agua_m3': 'water_use_m3',
            'modulo_consumo':'factor_value'
        }, 
        inplace=True
    )

    # 2. Hacer el merge (asignándolo a una variable temporal o directamente)
    
    tabla_unida = tabla.merge(
        codigos_divipola, 
        on='cod_mplity',
        how='left'
    )
    # Eliminar las columnas que no se necesitan
    tabla_unida.drop(columns=['CULTIVO','AREA COSECHADA (HA)','PRODUCCION (T)'], inplace=True)
    # Reordenar las columnas del DataFrame final
    tabla_unida = tabla_unida[['year', 'cod_dpt','department','cod_mplity', 'municipality', 'sector_code', 'sector_name',
                                'activity_code','activity_name', 'unit_activity', 'activity_value', 
                                'factor_unit', 'factor_value', 'water_use_m3', 'source_activity']]
        # 4. Guardar el DataFrame final de vuelta en la lista original
    tablas_poscosecha[i] = tabla_unida

print("Poscosecha_Palma : ",tablas_poscosecha[0].head(5))
print("Poscosecha_Banano : ",tablas_poscosecha[1].head(5))
print("Poscosecha_Cafe : ",tablas_poscosecha[2].head(5))

# Consolidación de la Base de datos de Poscosecha
df_poscosecha_final = pd.concat(tablas_poscosecha, ignore_index=True)
print("Poscosecha_Final : ",df_poscosecha_final.head(5))
# Guardar la base de datos final de Poscosecha en archivo parquet carpeta "procesed_data"
print("Guardando la base de datos final de Poscosecha en archivo parquet carpeta 'procesed_data'")
df_poscosecha_final.to_parquet("procesed_data/poscosecha_final.parquet", index=False)