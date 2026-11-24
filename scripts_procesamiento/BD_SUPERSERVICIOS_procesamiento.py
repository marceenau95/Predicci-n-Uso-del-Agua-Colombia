# Importar librerias 
import pandas as pd
import numpy as np
from pathlib import Path

# Lectura de base de datos de la SUPERSERVICIOS
# de la pagina ofical de la entidad: 
# https://www.superservicios.gov.co/descargas/Pages/Estadisticas-de-Servicios-Publicos-Domiciliarios.aspxW
ruta = Path(__file__).resolve().parent.parent / 'raw_data'
ruta_bd1 = ruta / 'consumo_agua_servicios_domestica_2002_2018.xlsx'
ruta_bd2 = ruta / 'consumo_agua_servicios_domestica_2017_2021.xlsx'
ruta_bd3 = ruta / 'consumo_agua_servicios_domestica_res_39945_2017_2021.xlsx'
bd_1 = pd.read_excel(ruta_bd1, sheet_name='1')
bd_2 = pd.read_excel(ruta_bd1, sheet_name='2')
bd_3 = pd.read_excel(ruta_bd2)
bd_4 = pd.read_excel(ruta_bd3)

# Imprimir información de las bases de datos
print("Información de la base de datos 1:")
print(bd_1.info())
print("\nInformación de la base de datos 2:")
print(bd_2.info())
print("\nInformación de la base de datos 3:")
print(bd_3.info())
print("\nInformación de la base de datos 4:")
print(bd_4.info())

## Filtrar por consumo de agua de acueducto y  hasta el año 2016 en bd1 y bd2 
bd_1_filtrada = bd_1[bd_1['AÑO'] <= 2016]
bd_2_filtrada = bd_2[bd_2['AÑO'] <= 2016]
bd_1_filtrada = bd_1_filtrada[bd_1_filtrada['SERVICIO'] == 'ACUEDUCTO']
bd_2_filtrada = bd_2_filtrada[bd_2_filtrada['SERVICIO'] == 'ACUEDUCTO']

# Normalizar nombres de columnas para bd_3 y bd_4
bd_3 =bd_3.rename(columns={'ID':'IDENTIFICADOR_EMPRESA',
                           'Nombre de la empresa':'EMPRESA',
                           'NIT':'ARE_ESP_NIT',
                           'Año':'AÑO',
                           'Mes':'MES',
                           'Codigo Departamento':'COD_DANE_DEPTO',
                           'Codigo Municipio':'COD_DANE_MPIO',
                           'Uso':'CLASE_DE_USO',
                           'Consumo':'CONSUMO M3'})
bd_4 = bd_4.rename(columns={'ID':'IDENTIFICADOR_EMPRESA',
                            'NIT':'ARE_ESP_NIT',
                            'CODIGO DEPARTAMENTO':'COD_DANE_DEPTO',
                            'CODIGO MUNICIPIO':'COD_DANE_MPIO',
                            'USO':'CLASE_DE_USO',
                            'CONSUMO':'CONSUMO M3'})

# Eliminar Columnas innecesarias en bd2, bd3
bd_1_filtrada = bd_1_filtrada.drop(columns=['USO',
                                            'SERVICIO'])
                                            
bd_2_filtrada = bd_2_filtrada.drop(columns=['Unnamed: 12', 
                                            'Unnamed: 13', 
                                            'Unnamed: 14', 
                                            'Unnamed: 15',
                                            'USO',
                                            'SERVICIO'
                                            ])
bd_3 = bd_3.drop(columns=['Unnamed: 12',
                          'Unnamed: 13',
                          'Departamento',
                          'Municipio',
                          'Estrato'

])
bd_4 = bd_4.drop(columns=['DEPARTAMENTO',
                          'MUNICIPIO',
                          'ESTRATO'
                          ])
# Concatenar las bases de datos filtradas y normalizadas
bd_concatenada = pd.concat([bd_1_filtrada, bd_2_filtrada, bd_3, bd_4], 
                           ignore_index=True)
print("\nInformación de la base de datos concatenada:")
print(bd_concatenada.info())
print("\nPrimeras filas de la base de datos concatenada:")
print(bd_concatenada.head())

# Ajustar el tipo de dato de la columna 'AÑO' a entero y filtrar a años desde 2008
bd_concatenada['AÑO'] = bd_concatenada['AÑO'].astype(int)
bd_concatenada = bd_concatenada[bd_concatenada['AÑO'] >= 2008]

#-------------------------------------------------------------------
#                      LIMPIEZA DE DATOS
#-------------------------------------------------------------------

# normalizar codigos de departamento y municipio
bd_concatenada['COD_DANE_DEPTO'] = bd_concatenada['COD_DANE_DEPTO'].apply(
                                    lambda x: 5 if x == 1 else x )
bd_concatenada['COD_DANE_MPIO'] = bd_concatenada['COD_DANE_MPIO'].apply(
                                lambda x: 1 if x == 0 else x )
bd_concatenada['COD_DANE_DEPTO'] = bd_concatenada['COD_DANE_DEPTO'].astype(
                                    str).str.zfill(2)
bd_concatenada['COD_DANE_MPIO'] = bd_concatenada['COD_DANE_MPIO'].astype(
                                    str).str.zfill(3)

# Crear columna de codigo divipola de municipio
bd_concatenada['cod_mplity'] = bd_concatenada['COD_DANE_DEPTO'] + bd_concatenada['COD_DANE_MPIO']

# Normalizar clase de uso 
def clase_uso (x):
    ''' Normaliza la columna de clase de uso para 
            que tenga un formato consistente.'''
    if x == 'Residencial (Bajo- Bajo)'or x =='Bajo- Bajo':
        return 'Bajo-Bajo'
    elif x == 'Residencial (Bajo)':
        return 'Bajo'
    elif x == 'Residencial (Medio)':
        return 'Medio'
    elif x == 'Residencial (Alto)':
        return 'Alto'
    elif x == 'Residencial (Medio - Bajo)'or x =='Medio- Bajo':
        return 'Medio-Bajo'
    elif x == 'Residencial (Medio -Alto)'or x =='Medio- Alto':
        return 'Medio-Alto'
    elif x == 'Multiusuario mixto':
        return 'Multiusuario Mixto'
    else:
        return x
bd_concatenada['CLASE_DE_USO'] = bd_concatenada['CLASE_DE_USO'].apply(clase_uso)

# Renombrar columna de codigo Departamento
bd_concatenada = bd_concatenada.rename(columns={'COD_DANE_DEPTO': 'cod_dpt'})

# Eliminar Columnas innecesarias
bd_concatenada = bd_concatenada.drop(columns=['ARE_ESP_NIT','COD_DANE_MPIO'])

# Eliminar duplicados
bd_concatenada = bd_concatenada.drop_duplicates()
bd_concatenada = bd_concatenada.drop_duplicates(subset=['cod_mplity', 'AÑO','CONSUMO M3','EMPRESA','CLASE_DE_USO'], keep='first')

# Guardar la base de datos limpia en un archivo parquet
ruta_salida = Path(__file__).resolve().parent.parent / 'procesed_data'
bd_concatenada.to_parquet(ruta_salida / 'consumo_agua_servicios_domestica.parquet', index=False)


    