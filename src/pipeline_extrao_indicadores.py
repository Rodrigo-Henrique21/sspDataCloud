# Databricks notebook source
from pyspark.sql.functions import col, to_date
import requests
import pandas as pd

# COMMAND ----------

class SeriesBCB:
    def __init__(self, series_br):
        self.series_br = {
    'SELIC_Efetiva_Diaria': 11,
    'SELIC_Meta_Anual': 432,
    'IPCA_Mensal': 433,
    'IGP_M_Mensal': 189,
    'INCC_Mensal': 192,
    'Indice_Condicoes_Econ_BR': 27574,
    'Indice_Condicoes_Econ_BR_USD': 29042,
    'Salario_Minimo': 1619,
    'IBC_BR': 24363,
    'Populacao_BR': 21774,
    'PIB_Trimestral_Real': 4380,
    'PIB_Anual_Corrente': 7326,
    'Deflator_Implicito_PIB': 1211
    }
        self.br_dataframes = {}

    def buscar_serie_bcb(self, codigo_sgs, inicio, fim):
        """
        Busca uma série do SGS do Banco Central do Brasil.

        :param codigo_sgs: Código da série SGS.
        :param inicio: Data de início.
        :param fim: Data de fim.
        :return: Dados da série em formato JSON.
        """
        url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_sgs}/dados'
        params = {
            'formato': 'json',
            'dataInicial': inicio.strftime('%d/%m/%Y'),
            'dataFinal': fim.strftime('%d/%m/%Y'),
        }
        resposta = requests.get(url, params=params)
        dados = resposta.json()

        if not dados:
            print(f"Aviso: Nenhum dado encontrado para o código SGS {codigo_sgs} entre {inicio} e {fim}.")
            return dados
        
        return dados

    def baixar_series(self):
        """
        Baixa todas as séries e armazena num dicionário.
        """
        for nome, codigo in self.series_br.items():
            print(f'Baixando {nome} (código {codigo})...')
            try:
                dt_inicio = pd.to_datetime('2022-01-01')
                dt_fim = pd.to_datetime('today')
                self.br_dataframes[nome] = pd.DataFrame(self.buscar_serie_bcb(codigo, inicio=dt_inicio, fim=dt_fim))
            except Exception as e:
                print(f"Erro ao baixar a série {nome} (código {codigo}): {e}")

    def processar_series(self):
        """
        Processa as séries baixadas e salva os resultados em tabelas Delta.
        """
        if self.br_dataframes:
            diaria_df = pd.DataFrame()
            mensal_df = pd.DataFrame()
            trimestral_df = pd.DataFrame()
            anual_df = pd.DataFrame()

            for chave, df in self.br_dataframes.items():
                df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
                if 'Diaria' in chave:
                    diaria_df[chave] = df.set_index('data')['valor']
                elif 'Mensal' in chave:
                    df = df.set_index('data').resample('D').ffill().reset_index()
                    mensal_df[chave] = df.set_index('data')['valor']
                elif 'Trimestral' in chave:
                    df = df.set_index('data').resample('D').ffill().reset_index()
                    trimestral_df[chave] = df.set_index('data')['valor']
                elif 'Anual' in chave or 'Meta' in chave:
                    df = df.set_index('data').resample('D').ffill().reset_index()
                    anual_df[chave] = df.set_index('data')['valor']

            if not diaria_df.empty:
                spark_diaria_df = spark.createDataFrame(diaria_df.reset_index())
                spark_diaria_df = spark_diaria_df.withColumn('data', to_date(col('data'), 'yyyy-MM-dd')).orderBy('data')
                spark_diaria_df.write.format("delta").mode("overwrite").saveAsTable("ssp_cloud.indicadores_economicos_diarios")
            if not mensal_df.empty:
                spark_mensal_df = spark.createDataFrame(mensal_df.reset_index())
                spark_mensal_df = spark_mensal_df.withColumn('data', to_date(col('data'), 'yyyy-MM-dd')).orderBy('data')
                spark_mensal_df.write.format("delta").mode("overwrite").saveAsTable("indicadores_economicos_mensal")

            if not trimestral_df.empty:
                spark_trimestral_df = spark.createDataFrame(trimestral_df.reset_index())
                spark_trimestral_df = spark_trimestral_df.withColumn('data', to_date(col('data'), 'yyyy-MM-dd')).orderBy('data')
                spark_trimestral_df.write.format("delta").mode("overwrite").saveAsTable("indicadores_economicos_trimestral")

            if not anual_df.empty:
                spark_anual_df = spark.createDataFrame(anual_df.reset_index())
                spark_anual_df = spark_anual_df.withColumn('data', to_date(col('data'), 'yyyy-MM-dd')).orderBy('data')
                spark_anual_df.write.format("delta").mode("overwrite").saveAsTable("indicadores_economicos_anual")
        else:
            print("Nenhum dataframe para processar.")

# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG dbw_prd_bra_01;
# MAGIC USE SCHEMA ssp_cloud;

# COMMAND ----------

series_bcb = SeriesBCB(series_br={})
series_bcb.baixar_series()
series_bcb.processar_series()