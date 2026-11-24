import pandas as pd
import numpy as np
from pathlib import Path

def cod_divipola():
    # 1. Obtiene la ruta de 'scripts_procesamiento' (donde está este script .py)
    carpeta_scripts = Path(__file__).resolve().parent

    # 2. Sube un nivel (.parent) a la raíz del proyecto y entra a 'raw_data'
    ruta_archivo = carpeta_scripts.parent / 'raw_data' / 'Cod_Mpio_DIVIPOLA.xlsx'

    # 3. Carga el archivo en pandas
    cod_divipola = pd.read_excel(ruta_archivo)
    cod_divipola['Código _DIVIPOLA'] = (
        cod_divipola['Código _DIVIPOLA'].astype(str).str.zfill(5)
    )
    cod_divipola['cod_dpto']= cod_divipola['cod_dpto'].astype(str).str.zfill(2)

    cod_divipola.rename(
    columns={
        'Nombre Depto': 'department',
        'Nombre_mpio':'municipality',
        'cod_dpto': 'cod_dpt',
        'Código _DIVIPOLA':'cod_mplity'
    },
    inplace=True
)
    return cod_divipola

def imputar_consumo_servicios(
    df,
    col_municipio='cod_mplity',
    col_empresa='EMPRESA',
    col_anio='AÑO',
    col_mes='MES',
    col_suscriptores='SUSCRIPTORES FACTURADOS',
    col_consumo='CONSUMO M3',
    min_datos=3
):
    ''' Imputa los consumos de agua de los servicios comerciales e institucionales
        de la base de datos de la SUPERSERVICIOS. La imputación se realiza
        siguiendo un conjunto de reglas jerárquicas, que consideran la información
        de consumo y suscriptores a nivel de municipio, empresa, año y mes.'''

    df = df.copy()

    # =========================================================
    # 1. INFORMACIÓN ORIGINAL
    # =========================================================

    df['_CONSUMO_ORIGINAL'] = df[col_consumo]

    # Solo consumos originalmente positivos pueden utilizarse
    # como referencia para promedios y tasas.
    df['_CONSUMO_VALIDO'] = np.where(
        df[col_consumo] > 0,
        df[col_consumo],
        np.nan
    )

    df['ORIGEN_CONSUMO'] = np.where(
        df[col_consumo] > 0,
        'ORIGINAL',
        'PENDIENTE'
    )

    df['N_DATOS_IMPUTACION'] = np.nan


    # =========================================================
    # 2. FUNCIÓN PARA DETECTAR OUTLIERS DE SUSCRIPTORES
    # =========================================================

    def outliers_iqr(x):

        resultado = pd.Series(
            False,
            index=x.index
        )

        valores = x.dropna()

        if len(valores) < 4:
            return resultado

        q1 = valores.quantile(0.25)
        q3 = valores.quantile(0.75)

        iqr = q3 - q1

        limite_inf = q1 - 1.5 * iqr
        limite_sup = q3 + 1.5 * iqr

        resultado.loc[x.notna()] = (
            (x.loc[x.notna()] < limite_inf) |
            (x.loc[x.notna()] > limite_sup)
        )

        return resultado


    # =========================================================
    # CONDICIÓN 1
    #
    # MUNICIPIO + EMPRESA + MES
    #
    # 1A. Tasa
    # 1B. Promedio
    # =========================================================

    df['_OUTLIER_EMPRESA_MES'] = (
        df.groupby(
            [
                col_municipio,
                col_empresa,
                col_mes
            ],
            dropna=False
        )[col_suscriptores]
        .transform(outliers_iqr)
    )

    df['_TASA_EMPRESA_MES'] = np.where(
        (
            (df['_CONSUMO_VALIDO'] > 0) &
            (df[col_suscriptores] > 0) &
            (~df['_OUTLIER_EMPRESA_MES'])
        ),
        df['_CONSUMO_VALIDO'] / df[col_suscriptores],
        np.nan
    )

    tasa_empresa_mes = (
        df.groupby(
            [
                col_municipio,
                col_empresa,
                col_mes
            ],
            dropna=False
        )['_TASA_EMPRESA_MES']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_TASA_EM_MES',
            'count': '_N_TASA_EM_MES'
        })
    )

    df = df.merge(
        tasa_empresa_mes,
        on=[
            col_municipio,
            col_empresa,
            col_mes
        ],
        how='left'
    )

    # ---------------------------------------------------------
    # 1A. Tasa empresa + mes
    # ---------------------------------------------------------

    mask = (
        (df[col_consumo] == 0) &
        (df[col_suscriptores] > 0) &
        (df['_TASA_EM_MES'] > 0) &
        (df['_N_TASA_EM_MES'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_TASA_EM_MES'] *
        df.loc[mask, col_suscriptores]
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_EMPRESA_MES_SUSCRIPTORES'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_TASA_EM_MES']
    )

    # ---------------------------------------------------------
    # 1B. Promedio empresa + mes
    # ---------------------------------------------------------

    prom_empresa_mes = (
        df.groupby(
            [
                col_municipio,
                col_empresa,
                col_mes
            ],
            dropna=False
        )['_CONSUMO_VALIDO']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_PROM_EM_MES',
            'count': '_N_PROM_EM_MES'
        })
    )

    df = df.merge(
        prom_empresa_mes,
        on=[
            col_municipio,
            col_empresa,
            col_mes
        ],
        how='left'
    )

    mask = (
        (df[col_consumo] == 0) &
        (df['_PROM_EM_MES'] > 0) &
        (df['_N_PROM_EM_MES'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_PROM_EM_MES']
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_EMPRESA_MES_PROMEDIO'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_PROM_EM_MES']
    )


    # =========================================================
    # CONDICIÓN 2
    #
    # MUNICIPIO + EMPRESA + AÑO
    #
    # 2A. Tasa
    # 2B. Promedio
    # =========================================================

    df['_OUTLIER_EMPRESA_ANIO'] = (
        df.groupby(
            [
                col_municipio,
                col_empresa,
                col_anio
            ],
            dropna=False
        )[col_suscriptores]
        .transform(outliers_iqr)
    )

    df['_TASA_EMPRESA_ANIO'] = np.where(
        (
            (df['_CONSUMO_VALIDO'] > 0) &
            (df[col_suscriptores] > 0) &
            (~df['_OUTLIER_EMPRESA_ANIO'])
        ),
        df['_CONSUMO_VALIDO'] / df[col_suscriptores],
        np.nan
    )

    tasa_empresa_anio = (
        df.groupby(
            [
                col_municipio,
                col_empresa,
                col_anio
            ],
            dropna=False
        )['_TASA_EMPRESA_ANIO']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_TASA_EM_ANIO',
            'count': '_N_TASA_EM_ANIO'
        })
    )

    df = df.merge(
        tasa_empresa_anio,
        on=[
            col_municipio,
            col_empresa,
            col_anio
        ],
        how='left'
    )

    # ---------------------------------------------------------
    # 2A. Tasa empresa + año
    # ---------------------------------------------------------

    mask = (
        (df[col_consumo] == 0) &
        (df[col_suscriptores] > 0) &
        (df['_TASA_EM_ANIO'] > 0) &
        (df['_N_TASA_EM_ANIO'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_TASA_EM_ANIO'] *
        df.loc[mask, col_suscriptores]
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_EMPRESA_ANIO_SUSCRIPTORES'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_TASA_EM_ANIO']
    )

    # ---------------------------------------------------------
    # 2B. Promedio empresa + año
    # ---------------------------------------------------------

    prom_empresa_anio = (
        df.groupby(
            [
                col_municipio,
                col_empresa,
                col_anio
            ],
            dropna=False
        )['_CONSUMO_VALIDO']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_PROM_EM_ANIO',
            'count': '_N_PROM_EM_ANIO'
        })
    )

    df = df.merge(
        prom_empresa_anio,
        on=[
            col_municipio,
            col_empresa,
            col_anio
        ],
        how='left'
    )

    mask = (
        (df[col_consumo] == 0) &
        (df['_PROM_EM_ANIO'] > 0) &
        (df['_N_PROM_EM_ANIO'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_PROM_EM_ANIO']
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_EMPRESA_ANIO_PROMEDIO'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_PROM_EM_ANIO']
    )


    # =========================================================
    # CONDICIÓN 3
    #
    # MUNICIPIO + EMPRESA
    #
    # TODOS LOS AÑOS Y MESES
    #
    # IMPORTANTE:
    # Aquí NO utilizamos tasa.
    #
    # Utilizamos el promedio histórico de consumo de la
    # empresa en ese municipio.
    # =========================================================

    prom_empresa_total = (
        df.groupby(
            [
                col_municipio,
                col_empresa
            ],
            dropna=False
        )['_CONSUMO_VALIDO']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_PROM_EMPRESA_TOTAL',
            'count': '_N_PROM_EMPRESA_TOTAL'
        })
    )

    df = df.merge(
        prom_empresa_total,
        on=[
            col_municipio,
            col_empresa
        ],
        how='left'
    )

    mask = (
        (df[col_consumo] == 0) &
        (df['_PROM_EMPRESA_TOTAL'] > 0) &
        (df['_N_PROM_EMPRESA_TOTAL'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_PROM_EMPRESA_TOTAL']
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_EMPRESA_HISTORICO_PROMEDIO'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_PROM_EMPRESA_TOTAL']
    )


    # =========================================================
    # CONDICIÓN 4
    #
    # MUNICIPIO + MES
    #
    # OTRAS EMPRESAS
    #
    # IMPORTANTE:
    # NO usamos tasa de otras empresas.
    #
    # Solo promedio de consumo.
    # =========================================================

    consumo_empresa_mes = (
        df.groupby(
            [
                col_municipio,
                col_mes,
                col_empresa
            ],
            dropna=False
        )['_CONSUMO_VALIDO']
        .agg(
            suma='sum',
            n='count'
        )
        .reset_index()
    )

    consumo_mpio_mes = (
        df.groupby(
            [
                col_municipio,
                col_mes
            ],
            dropna=False
        )['_CONSUMO_VALIDO']
        .agg(
            suma_total='sum',
            n_total='count'
        )
        .reset_index()
    )

    df = df.merge(
        consumo_empresa_mes,
        on=[
            col_municipio,
            col_mes,
            col_empresa
        ],
        how='left'
    )

    df = df.merge(
        consumo_mpio_mes,
        on=[
            col_municipio,
            col_mes
        ],
        how='left'
    )

    # Excluir explícitamente la empresa objetivo
    df['_N_OTRAS_EMPRESAS'] = (
        df['n_total'] - df['n']
    )

    df['_SUMA_OTRAS_EMPRESAS'] = (
        df['suma_total'] - df['suma']
    )

    df['_PROM_OTRAS_EMPRESAS'] = np.where(
        df['_N_OTRAS_EMPRESAS'] > 0,
        (
            df['_SUMA_OTRAS_EMPRESAS'] /
            df['_N_OTRAS_EMPRESAS']
        ),
        np.nan
    )

    mask = (
        (df[col_consumo] == 0) &
        (df['_PROM_OTRAS_EMPRESAS'] > 0) &
        (df['_N_OTRAS_EMPRESAS'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_PROM_OTRAS_EMPRESAS']
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_MPIO_MES_OTRAS_EMPRESAS_PROMEDIO'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_OTRAS_EMPRESAS']
    )


    # =========================================================
    # CONDICIÓN 5
    #
    # MUNICIPIO + AÑO
    #
    # 5A. Tasa municipal-año
    # 5B. Promedio municipal-año
    # =========================================================

    df['_OUTLIER_MPIO_ANIO'] = (
        df.groupby(
            [
                col_municipio,
                col_anio
            ],
            dropna=False
        )[col_suscriptores]
        .transform(outliers_iqr)
    )

    df['_TASA_MPIO_ANIO'] = np.where(
        (
            (df['_CONSUMO_VALIDO'] > 0) &
            (df[col_suscriptores] > 0) &
            (~df['_OUTLIER_MPIO_ANIO'])
        ),
        df['_CONSUMO_VALIDO'] / df[col_suscriptores],
        np.nan
    )

    tasa_mpio_anio = (
        df.groupby(
            [
                col_municipio,
                col_anio
            ],
            dropna=False
        )['_TASA_MPIO_ANIO']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_TASA_MA',
            'count': '_N_TASA_MA'
        })
    )

    df = df.merge(
        tasa_mpio_anio,
        on=[
            col_municipio,
            col_anio
        ],
        how='left'
    )

    # ---------------------------------------------------------
    # 5A. Tasa municipio + año
    # ---------------------------------------------------------

    mask = (
        (df[col_consumo] == 0) &
        (df[col_suscriptores] > 0) &
        (df['_TASA_MA'] > 0) &
        (df['_N_TASA_MA'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_TASA_MA'] *
        df.loc[mask, col_suscriptores]
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_MPIO_ANIO_SUSCRIPTORES'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_TASA_MA']
    )

    # ---------------------------------------------------------
    # 5B. Promedio municipio + año
    # ---------------------------------------------------------

    prom_mpio_anio = (
        df.groupby(
            [
                col_municipio,
                col_anio
            ],
            dropna=False
        )['_CONSUMO_VALIDO']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_PROM_MA',
            'count': '_N_PROM_MA'
        })
    )

    df = df.merge(
        prom_mpio_anio,
        on=[
            col_municipio,
            col_anio
        ],
        how='left'
    )

    mask = (
        (df[col_consumo] == 0) &
        (df['_PROM_MA'] > 0) &
        (df['_N_PROM_MA'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_PROM_MA']
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_MPIO_ANIO_PROMEDIO'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_PROM_MA']
    )


    # =========================================================
    # CONDICIÓN 6
    #
    # MUNICIPIO COMPLETO
    #
    # TASA GLOBAL MUNICIPAL
    # =========================================================

    df['_OUTLIER_MPIO'] = (
        df.groupby(
            col_municipio,
            dropna=False
        )[col_suscriptores]
        .transform(outliers_iqr)
    )

    df['_TASA_MPIO'] = np.where(
        (
            (df['_CONSUMO_VALIDO'] > 0) &
            (df[col_suscriptores] > 0) &
            (~df['_OUTLIER_MPIO'])
        ),
        df['_CONSUMO_VALIDO'] / df[col_suscriptores],
        np.nan
    )

    tasa_mpio = (
        df.groupby(
            col_municipio,
            dropna=False
        )['_TASA_MPIO']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={
            'mean': '_TASA_MPIO_GLOBAL',
            'count': '_N_TASA_MPIO_GLOBAL'
        })
    )

    df = df.merge(
        tasa_mpio,
        on=col_municipio,
        how='left'
    )

    mask = (
        (df[col_consumo] == 0) &
        (df[col_suscriptores] > 0) &
        (df['_TASA_MPIO_GLOBAL'] > 0) &
        (df['_N_TASA_MPIO_GLOBAL'] >= min_datos)
    )

    df.loc[mask, col_consumo] = (
        df.loc[mask, '_TASA_MPIO_GLOBAL'] *
        df.loc[mask, col_suscriptores]
    )

    df.loc[mask, 'ORIGEN_CONSUMO'] = (
        'IMPUTADO_MPIO_GLOBAL_SUSCRIPTORES'
    )

    df.loc[mask, 'N_DATOS_IMPUTACION'] = (
        df.loc[mask, '_N_TASA_MPIO_GLOBAL']
    )


    # =========================================================
    # 7. ELIMINACIÓN FINAL
    # =========================================================

    mask_eliminar = (
        df[col_consumo] == 0
    )

    df.loc[
        mask_eliminar,
        'ORIGEN_CONSUMO'
    ] = 'ELIMINAR'

    df = df[
        df['ORIGEN_CONSUMO'] != 'ELIMINAR'
    ].copy()


    # =========================================================
    # 8. LIMPIAR COLUMNAS AUXILIARES
    # =========================================================

    columnas_auxiliares = [
        '_CONSUMO_ORIGINAL',
        '_CONSUMO_VALIDO',

        '_OUTLIER_EMPRESA_MES',
        '_TASA_EMPRESA_MES',
        '_TASA_EM_MES',
        '_N_TASA_EM_MES',
        '_PROM_EM_MES',
        '_N_PROM_EM_MES',

        '_OUTLIER_EMPRESA_ANIO',
        '_TASA_EMPRESA_ANIO',
        '_TASA_EM_ANIO',
        '_N_TASA_EM_ANIO',
        '_PROM_EM_ANIO',
        '_N_PROM_EM_ANIO',

        '_PROM_EMPRESA_TOTAL',
        '_N_PROM_EMPRESA_TOTAL',

        'suma',
        'n',
        'suma_total',
        'n_total',
        '_N_OTRAS_EMPRESAS',
        '_SUMA_OTRAS_EMPRESAS',
        '_PROM_OTRAS_EMPRESAS',

        '_OUTLIER_MPIO_ANIO',
        '_TASA_MPIO_ANIO',
        '_TASA_MA',
        '_N_TASA_MA',
        '_PROM_MA',
        '_N_PROM_MA',

        '_OUTLIER_MPIO',
        '_TASA_MPIO',
        '_TASA_MPIO_GLOBAL',
        '_N_TASA_MPIO_GLOBAL'
    ]

    df.drop(
        columns=columnas_auxiliares,
        inplace=True,
        errors='ignore'
    )

    return df