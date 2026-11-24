# Importar librerias 
import pandas as pd
import numpy as np
from pathlib import Path
from utilidades import imputar_consumo_servicios
from utilidades import cod_divipola

# Leer base de datos limpia de la SUPERSERVICIOS
ruta_salida = Path(__file__).resolve().parent.parent / 'procesed_data'
df = pd.read_parquet(ruta_salida / 'consumo_agua_servicios_domestica.parquet')

# Seleccionar solo los servicios de interés: Oficial, Comercial y 
# Otros( Especial, Temporal, Multiusuario Mixto y Provisional)
servicios = df[df['CLASE_DE_USO'].isin(['Oficial','Comercial','Especial', 'Temporal',
       'Multiusuario Mixto', 'Provisional'])]

# -----------------------------------------------------------------------------
#                                   COMERCIAL
# -----------------------------------------------------------------------------
comercial = servicios[servicios['CLASE_DE_USO'] == 'Comercial']

# Corregir codigo divipola municipio 66450
comercial['cod_mplity'] = comercial['cod_mplity'].apply(
                        lambda x:'66045' if x=='66450'else x)

# Imputar consumos comerciales
comercial = imputar_consumo_servicios(comercial)

#Imprimir las primeras filas de la base de datos procesada
print("\nPrimeras filas de la base de datos procesada:")
print(comercial.head())

# Agrupar la información por año, mes y municipio
comercial_agrupado_mensual = comercial.groupby(['AÑO', 'MES', 'cod_mplity']).agg({
    'SUSCRIPTORES FACTURADOS':'sum',
    'CONSUMO M3':'sum'
}).reset_index().sort_values(by=['AÑO','cod_mplity'])

# Agrupar la información por año y municipio
comercial_agrupado = comercial_agrupado_mensual.groupby(['AÑO','cod_mplity']).agg({
    'SUSCRIPTORES FACTURADOS':'mean',
    'CONSUMO M3':'sum'
}).reset_index().sort_values(by=['AÑO','cod_mplity'])

# Verificación de tendencia de crecimiento de consumo comercial 2016-2018
comercial_agrupado_2016 = comercial_agrupado[
       comercial_agrupado['AÑO']==2016][
           ['cod_mplity', 'CONSUMO M3']].rename(
               columns={'CONSUMO M3': 'consumo_2016'})
comercial_agrupado_2017 = comercial_agrupado[
    comercial_agrupado['AÑO']==2017][
        ['cod_mplity', 'CONSUMO M3']].rename(
            columns={'CONSUMO M3': 'consumo_2017'})
comercial_agrupado_2018 = comercial_agrupado[
    comercial_agrupado['AÑO']==2018][
        ['cod_mplity', 'CONSUMO M3']].rename(
            columns={'CONSUMO M3': 'consumo_2018'})
audit = pd.merge(comercial_agrupado_2016, 
                 comercial_agrupado_2017,
                   on='cod_mplity', 
                   how='outer')
comercial_2016_2018 = pd.merge(audit, 
                               comercial_agrupado_2018,
                                 on='cod_mplity', how='outer')

# 3. Calcular el exceso absoluto de 2017 frente a la tendencia (promedio de 2016 y 2018)
comercial_2016_2018['tendencia_esperada'] = (comercial_2016_2018['consumo_2016'] + 
                                             comercial_2016_2018['consumo_2018']) / 2
comercial_2016_2018['exceso_volumen_2017'] = comercial_2016_2018['consumo_2017'] - comercial_2016_2018['tendencia_esperada']

# 4. Ordenar para ver los municipios que generaron los 35 millones de m3 extras
principales_causantes = comercial_2016_2018.sort_values(
                            by='exceso_volumen_2017', 
                             ascending=False)

# Descartar municipios que no tienen registros en 2016 o 2018
principales_causantes = principales_causantes[
    ~(principales_causantes['tendencia_esperada'].isna())]

print("--- MUNICIPIOS QUE CAUSARON EL PICO DE 2017 ---")
print(principales_causantes[['cod_mplity', 
                             'consumo_2016',
                               'consumo_2017',
                                 'consumo_2018',
                                   'exceso_volumen_2017']])

# Suavizar datos que generaron picos de consumo en 2017, reemplazando el valor de 2017 por la tendencia esperada
comercial_agrupado_suavizado = comercial_agrupado.copy()
for municipio in comercial_agrupado_suavizado['cod_mplity'].unique():
    if municipio in principales_causantes['cod_mplity'].values:
        tendencia = comercial_2016_2018.loc[
            comercial_2016_2018['cod_mplity'] == municipio,
              'tendencia_esperada'].values[0]
        comercial_agrupado_suavizado.loc[
            (comercial_agrupado_suavizado['cod_mplity'] == municipio) & 
            (comercial_agrupado_suavizado['AÑO'] == 2017), 
            'CONSUMO M3'] = tendencia

# -----------------------------------------------------------------------------
#                                         INSTITUCIONAL
# -----------------------------------------------------------------------------
# Filtrar los servicios institucionales (Oficial)
institucional = servicios[servicios['CLASE_DE_USO'] == 'Oficial']

# Eliminar duplicados en la base de datos institucional
institucional = institucional.drop_duplicates(
    subset=['cod_mplity',
             'AÑO',
             'CONSUMO M3',
             'EMPRESA'], keep='first')

# Imputar valores faltantes de consumo institucional
df_oficial_imputado = imputar_consumo_servicios(institucional)

# Agrupar la información institucional por año, mes y municipio
oficial_agrupado_mensual = df_oficial_imputado.groupby(
    ['AÑO','MES','cod_mplity']).agg({
    'SUSCRIPTORES FACTURADOS':'sum',
    'CONSUMO M3':'sum'
}).reset_index().sort_values(by=['AÑO','cod_mplity'])

# Agrupar la información institucional por año y municipio
oficial_agrupado = oficial_agrupado_mensual.groupby(['AÑO','cod_mplity']).agg({
    'SUSCRIPTORES FACTURADOS':'mean',
    'CONSUMO M3':'sum'
}).reset_index().sort_values(by=['AÑO','cod_mplity'])

# Verificación de tendencia de crecimiento de consumo institucional 2016-2018
oficial_agrupado_2016 = oficial_agrupado[
    oficial_agrupado['AÑO']==2016][
        ['cod_mplity', 'CONSUMO M3']].rename(
            columns={'CONSUMO M3': 'consumo_2016'})
oficial_agrupado_2017 = oficial_agrupado[
    oficial_agrupado['AÑO']==2017][
        ['cod_mplity', 'CONSUMO M3']].rename(
            columns={'CONSUMO M3': 'consumo_2017'})
oficial_agrupado_2018 = oficial_agrupado[
    oficial_agrupado['AÑO']==2018][
        ['cod_mplity', 'CONSUMO M3']].rename(
            columns={'CONSUMO M3': 'consumo_2018'})

audit = pd.merge(oficial_agrupado_2016, 
                 oficial_agrupado_2017,
                   on='cod_mplity', 
                   how='outer')
oficial_2016_2018 = pd.merge(audit,
                              oficial_agrupado_2018,
                             on='cod_mplity',
                               how='outer')
# 3. Calcular el exceso absoluto de 2017 frente a la tendencia (promedio de 2016 y 2018)
oficial_2016_2018['tendencia_esperada'] = (oficial_2016_2018[
    'consumo_2016'] + oficial_2016_2018[
        'consumo_2018']) / 2
oficial_2016_2018['exceso_volumen_2017'] = oficial_2016_2018[
    'consumo_2017'] - oficial_2016_2018[
        'tendencia_esperada']

# 4. Ordenar para ver los municipios que generaron los 35 millones de m3 extras
principales_causantes_oficial = oficial_2016_2018.sort_values(
    by='exceso_volumen_2017', 
    ascending=False)
# Descartar los municipios que no tienen registros en 2016 u 2018
principales_causantes_oficial = principales_causantes_oficial[
    ~(principales_causantes_oficial['tendencia_esperada'].isna())]

print("--- MUNICIPIOS QUE CAUSARON EL PICO DE 2017 ---")
print(principales_causantes_oficial[
    ['cod_mplity',
      'consumo_2016',
        'consumo_2017',
          'consumo_2018', 
          'exceso_volumen_2017']])

# Suavizar datos que generaron picos de consumo en 2017, reemplazando el valor de 2017 por la tendencia esperada
oficial_agrupado_suavizado = oficial_agrupado.copy()
for municipio in oficial_agrupado_suavizado['cod_mplity'].unique():
    if municipio in principales_causantes_oficial['cod_mplity'].values:
        tendencia = oficial_2016_2018.loc[
            oficial_2016_2018['cod_mplity'] == municipio,
              'tendencia_esperada'].values[0]
        oficial_agrupado_suavizado.loc[
            (oficial_agrupado_suavizado['cod_mplity'] == municipio) & 
            (oficial_agrupado_suavizado['AÑO'] == 2017), 
            'CONSUMO M3'] = tendencia

# -----------------------------------------------------------------------------
#                                         OTROS
# -----------------------------------------------------------------------------
# filtrar los servicios de otros (Especial, Temporal, Multiusuario Mixto y Provisional)

df_otros = df[df['CLASE_DE_USO'].isin(['Especial', 'Temporal',
       'Multiusuario Mixto', 'Provisional'])]
df_otros = df_otros.drop_duplicates(subset=['cod_mplity', 
                                            'AÑO',
                                            'MES',
                                            'CONSUMO M3',
                                            'EMPRESA'], 
                                            keep='first')

# Filtrar solo registros con consumo mayor a 0
df_otros = df_otros[~(df_otros['CONSUMO M3']==0)]

# Agrupar la información de otros por año, mes y municipio
df_otros_agrupado_mensual = df_otros.groupby(
    ['AÑO','MES','cod_mplity']).agg({
    'SUSCRIPTORES FACTURADOS':'sum',
    'CONSUMO M3':'sum'
})
# Agrupar por AÑO, Cod_mpio 
df_otros_agrupado = df_otros_agrupado_mensual.groupby(['AÑO','cod_mplity']).agg({
    'SUSCRIPTORES FACTURADOS':'mean',
    'CONSUMO M3':'sum'
}).reset_index().sort_values(by=['AÑO','cod_mplity'])


#---------------------------------------------------------------------------------------
#                   NORMALIZAR BASES DE DATOS 2008 A 2020
#---------------------------------------------------------------------------------------
cod_divipola = cod_divipola()

# Incluir columnas de actividad económica y sector economico
oficial_agrupado_suavizado['activity_code'] = 'public_water_use'
oficial_agrupado_suavizado['activity_name'] = 'Uso de agua oficial'
comercial_agrupado_suavizado['activity_code'] = 'commercial_water_use'
comercial_agrupado_suavizado['activity_name'] = 'Uso de agua comercial'
df_otros_agrupado['activity_code'] = 'other_water_use'
df_otros_agrupado['activity_name'] = 'Uso de agua en otras actividades'

# Suscriptores de servicios 
suscriptores_servicios = pd.read_parquet(ruta_salida / 'susc_servicios.parquet')
# normalizar todas las bases de datos
servicios =[oficial_agrupado_suavizado,comercial_agrupado_suavizado,df_otros_agrupado]
servicios_mod =[]
for tabla in servicios:
    # Agregar pérdidas de agua del 37%
    tabla['CONSUMO_FINAL'] = round((tabla['CONSUMO M3'] / (1-0.37)),2)
    tabla = tabla.drop(columns =['CONSUMO M3'])
    tabla = tabla.rename(columns={'AÑO':'year','SUSCRIPTORES FACTURADOS':'activity_value','CONSUMO_FINAL':'water_use_m3'})
    tabla['unit_activity']= 'suscriptores'
    tabla['source_activity']= 'SUPERSERVICIOS'
    tabla['factor_value'] = ''
    tabla['factor_unit'] =''
    tabla['sector_name'] = 'Servicios'
    tabla['sector_code'] ='services'
    tabla = tabla.merge(cod_divipola,on='cod_mplity',how='left')
    tabla = tabla.merge(suscriptores_servicios,on=['year','cod_mplity','activity_code'],how='left')
    tabla['activity_value'] = np.where(tabla['activity_value']==0,np.nan, tabla['activity_value'])
    tabla['activity_value'] = tabla['activity_value'].fillna(tabla['Suscriptores'])
    tabla = tabla.drop(columns=['Suscriptores'])
    servicios_mod.append(tabla)

print("\nBases de datos normalizadas:")
for tabla in servicios_mod:
    print(f"  Filas: {len(tabla)}")
    print(f"  Columnas: {len(tabla.columns)}")
    orden_columnas =['year','cod_dpt','department','cod_mplity','municipality','sector_code',
                 'sector_name','activity_code','activity_name','unit_activity','activity_value',
                 'factor_unit','factor_value','water_use_m3','source_activity']
    tabla = tabla[orden_columnas]
#---------------------------------------------------------------------------------------
#                    BASES DE DATOS 2021 A 2024
#---------------------------------------------------------------------------------------
ruta_21_24 = Path(__file__).resolve().parent.parent/ 'raw_data'
oficial_2021_24 = pd.read_excel(ruta_21_24/'Bd_Servicios_Institucional_2021_24.xlsx')
comercial_2021_24 = pd.read_excel(ruta_21_24/'Bd_Servicios_comercial_2021_24.xlsx')
otros_2021_24 = pd.read_excel(ruta_21_24/'Bd_Servicios_Otros_2021_24.xlsx')
servicios_21_24 = [oficial_2021_24,comercial_2021_24,otros_2021_24]
serv_21_24 =[]
for tabla in servicios_21_24:
    tabla['cod_mplity'] = tabla['cod_mplity'].astype(str).str.zfill(5)
    tabla['cod_dpt'] = tabla['cod_dpt'].astype(str).str.zfill(2)
    tabla['water_use_m3'] = tabla['water_use_m3'].round(2)
    tabla = tabla.merge(suscriptores_servicios,on=['year','cod_mplity','activity_code'],how='left')
    tabla['activity_value'] = np.where(tabla['activity_value']==0,np.nan, tabla['activity_value'])
    tabla['activity_value'] = tabla['activity_value'].fillna(tabla['Suscriptores'])
    tabla = tabla.drop(columns=['Suscriptores'])
    serv_21_24.append(tabla)
#---------------------------------------------------------------------------------------
#                    CONCATENAR y EXPORTAR BASES DE DATOS 2008 A 2024
#---------------------------------------------------------------------------------------
servicios_final = pd.concat(servicios_mod + serv_21_24, ignore_index=True)
# Exportar df a parquet
servicios_final.to_parquet(ruta_salida/'servicios_final.parquet', index=False)

