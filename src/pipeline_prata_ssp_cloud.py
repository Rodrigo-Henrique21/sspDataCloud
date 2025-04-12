# Databricks notebook source
from pyspark.sql import SparkSession, functions as F
from pyspark.sql import Window
import requests
import pandas as pd
import unicodedata

# COMMAND ----------

class MaturacaoSSPSilver:
    """
    Classe para maturação incremental detalhada dos dados da camada Bronze para Silver.
    Realiza tratamentos específicos por coluna, incluindo conversão de tipos e padronizações.

    Atributos:
        spark_session (SparkSession): Sessão Spark.
        tabela_bronze (str): Nome da tabela Bronze.
        tabela_silver (str): Nome da tabela Silver.
    """

    def __init__(self, spark_session: SparkSession, tabela_bronze: str, tabela_silver: str):
        """
        Inicializa a classe MaturacaoSSPSilver com os parâmetros fornecidos.

        Args:
            spark_session (SparkSession): Sessão Spark.
            tabela_bronze (str): Nome da tabela Bronze.
            tabela_silver (str): Nome da tabela Silver.
        """
        self.spark = spark_session
        self.tabela_bronze = tabela_bronze
        self.tabela_silver = tabela_silver

    def carregar_dados_bronze(self):
        """
        Carrega os dados da tabela Bronze.

        Returns:
            DataFrame: Dados carregados da tabela Bronze.
        """
        print("📥 [INFO] Carregando dados da camada Bronze...")
        return self.spark.table(self.tabela_bronze)

    def carregar_indicadores(self):
        """
        Carrega os dados das tabelas de indicadores econômicos.

        Returns:
            dict: Dicionário com DataFrames dos indicadores econômicos.
        """
        print("📥 [INFO] Carregando dados das tabelas de indicadores econômicos...")
        indicadores = {
            "anual": self.spark.table("dbw_prd_bra_01.ssp_cloud.indicadores_economicos_anual"),
            "mensal": self.spark.table("dbw_prd_bra_01.ssp_cloud.indicadores_economicos_mensal"),
            "trimestral": self.spark.table("dbw_prd_bra_01.ssp_cloud.indicadores_economicos_trimestral"),
            "diarios": self.spark.table("dbw_prd_bra_01.ssp_cloud.indicadores_economicos_diarios")
        }
        return indicadores

    def tratar_dados(self, df_bronze):
        """
        Realiza o tratamento e preparação dos dados para a camada Silver.

        Args:
            df_bronze (DataFrame): Dados da camada Bronze.

        Returns:
            DataFrame: Dados tratados prontos para a camada Silver.
        """
        print("🛠️ [INFO] Tratando e preparando dados para camada Silver...")

        # Renomear colunas com acentos e padronizar colunas com DESCR_
        def remover_acentos(input_str):
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

        for coluna in df_bronze.columns:
            nova_coluna = remover_acentos(coluna)
            nova_coluna = nova_coluna.replace("DESC_", "DESCRICAO_")
            if coluna != nova_coluna:
                df_bronze = df_bronze.withColumnRenamed(coluna, nova_coluna)

        # Tratamento específico das datas
        colunas_data = [col for col in df_bronze.columns if 'DATA' in col]
        for coluna in colunas_data:
            df_bronze = df_bronze.withColumn(
                coluna,
                F.to_date(F.col(coluna), 'yyyy-MM-dd').cast('date')
            )

        # Tratamento específico de numéricos (exemplo: LATITUDE, LONGITUDE)
        colunas_numericas = ['LATITUDE', 'LONGITUDE']
        for coluna in colunas_numericas:
            df_bronze = df_bronze.withColumn(
                coluna,
                df_bronze[coluna].cast("decimal(18,10)")
            )
        # Mantem coluna mes_estatistica como inteiro
        df_bronze = df_bronze.withColumn("mes_estatistica", F.col("mes_estatistica").cast("int"))

        # Tratamento específico das horas
        colunas_hora = [col for col in df_bronze.columns if 'HORA' in col]
        for coluna in colunas_hora:
            df_bronze = df_bronze.withColumn(
                coluna,
                F.to_timestamp(F.col(coluna), 'yyyy-MM-dd HH:mm:ss').cast('timestamp')
            )

        # Padronização de campos string
        colunas_string = ['NOME_DELEGACIA', 'CIDADE', 'BAIRRO', 'RUBRICA', 'LOGRADOURO']
        for coluna in colunas_string:
            df_bronze = df_bronze.withColumn(
                coluna,
                F.upper(F.trim(F.col(coluna)))
            )

        # Conversão de colunas para inteiro
        colunas_inteiro = ['NUMERO_LOGRADOURO', 'NUM_BO']
        for coluna in colunas_inteiro:
            df_bronze = df_bronze.withColumn(coluna, F.col(coluna).cast("int"))

        # Limpeza de linhas vazias (totalmente nulas)
        df_bronze = df_bronze.na.drop("all")

        # Excluir linhas em que a coluna NUM_BO for null
        df_bronze = df_bronze.filter(F.col("NUM_BO").isNotNull())

        # Carregar indicadores econômicos
        indicadores = self.carregar_indicadores()

        # Renomear a coluna 'data' para 'DATA_COMUNICACAO_INDICADOR' no DataFrame de indicadores
        for key in indicadores:
            indicadores[key] = indicadores[key].withColumnRenamed("data", f"DATA_COMUNICACAO_INDICADOR_{key}")

        # Realizar a operação de join
        df_silver = df_bronze
        for key, df_indicador in indicadores.items():
            df_silver = df_silver.join(
                df_indicador,
                df_silver["DATA_COMUNICACAO_BO"] == df_indicador[f"DATA_COMUNICACAO_INDICADOR_{key}"],
                "left"
            ).drop(f"DATA_COMUNICACAO_INDICADOR_{key}")

        print("✅ [INFO] Dados tratados detalhadamente com sucesso.")
        return df_silver

    def salvar_silver(self, df_silver):
        """
        Salva os dados tratados na tabela Silver.

        Args:
            df_silver (DataFrame): Dados tratados prontos para serem salvos na camada Silver.
        """
        print(f"💾 [INFO] Salvando dados tratados na camada Silver ({self.tabela_silver})...")
        try:
            df_silver.write \
                .format("delta") \
                .mode("overwrite") \
                .option("mergeSchema", "true") \
                .option("primaryKey", "NUM_BO") \
                .saveAsTable(self.tabela_silver)

            print("✅ [INFO] Dados salvos com sucesso na camada Silver.")
        except Exception as e:
            print(f"🔴 [ERRO] Falha ao salvar dados na camada Silver: {e}")

    def executar_maturacao(self):
        """
        Executa o processo de maturação dos dados da camada Bronze para Silver.
        """
        print("🚀 [INFO] Iniciando maturação detalhada de Bronze para Silver...")
        df_bronze = self.carregar_dados_bronze()
        df_silver = self.tratar_dados(df_bronze)
        self.salvar_silver(df_silver)
        print("🏁 [INFO] Processo de maturação concluído com sucesso!")

# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG dbw_prd_bra_01;
# MAGIC USE SCHEMA ssp_cloud;
# MAGIC

# COMMAND ----------

maturacao = MaturacaoSSPSilver(
    spark_session=spark,
    tabela_bronze="bronze_sp_dados_criminais",
    tabela_silver="silver_sp_dados_criminais"
)

maturacao.executar_maturacao()