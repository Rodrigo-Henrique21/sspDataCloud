# Databricks notebook source
# MAGIC %pip install beautifulsoup4 tenacity
# MAGIC %pip install openpyxl
# MAGIC

# COMMAND ----------

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import BytesIO
import pandas as pd
import pyspark.sql.functions as F
from pyspark.sql import SparkSession

# COMMAND ----------

spark.conf.set("spark.sql.execution.arrow.enabled", "true") # Para conversão Pandas <-> Spark mais rápida

# COMMAND ----------

class IngestaoSSPIncrementalMensal:
    def __init__(self, spark_session: SparkSession, url_base: str, padrao_caminho_excel: str, ano_inicial: int, nome_tabela: str):
        self.spark = spark_session
        self.url_base = url_base.rstrip('/')
        self.padrao_caminho_excel = padrao_caminho_excel.lstrip('/')
        self.ano_inicial = ano_inicial
        self.nome_tabela = nome_tabela
        self.anos_encontrados = []
        self.session = self.criar_session_com_retries()

    def criar_session_com_retries(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def descobrir_anos(self):
        print(f"🔎 [INFO] Descobrindo anos disponíveis a partir de {self.ano_inicial}...")
        ano = self.ano_inicial
        while True:
            url_teste = f"{self.url_base}/{self.padrao_caminho_excel.format(ano)}"
            try:
                resp = self.session.head(url_teste, timeout=10)
                if resp.status_code == 200:
                    print(f"   🟢 [ENCONTRADO] {url_teste}")
                    self.anos_encontrados.append((ano, url_teste))
                    ano += 1
                else:
                    print(f"   🔴 [NAO EXISTE] {url_teste}, parando.")
                    break
            except Exception as e:
                print(f"   🔴 [ERRO] {e}")
                break
        print(f"✅ [INFO] Total de anos encontrados: {len(self.anos_encontrados)}")

    def baixar_e_converter_para_spark(self, ano: int, url_xlsx: str):
        print(f"⬇️ [INFO] Baixando e convertendo arquivo do ano {ano}: {url_xlsx}")
        try:
            resp = self.session.get(url_xlsx, timeout=600)
            resp.raise_for_status()
        except Exception as e:
            print(f"   🔴 [ERRO] Falha ao baixar arquivo: {e}")
            return None

        df_pandas = pd.read_excel(BytesIO(resp.content))
        df_pandas = df_pandas.astype(str)

        tabelas = self.spark.sql(f"SHOW TABLES LIKE '{self.nome_tabela}'").collect()
        if tabelas:
            df_existente = self.spark.table(self.nome_tabela)
            anos_existentes = [row['ano'] for row in df_existente.select("ano").distinct().collect()]
            if str(ano) in anos_existentes and ano != datetime.now().year:
                print(f"   🔴 [INFO] Ano {ano} já ingerido, pulando.")
                return None

        df_spark = self.spark.createDataFrame(df_pandas)
        # Renomear ANO_BO para ano se existir
        colunas_upper = [c.upper() for c in df_spark.columns]
        if "ANO_BO" in colunas_upper:
            for c in df_spark.columns:
                if c.upper() == "ANO_BO":
                    df_spark = df_spark.withColumnRenamed(c, "ano")
                    break
        else:
            df_spark = df_spark.withColumn("ano", F.lit(str(ano)))

        # Força explicitamente todas as colunas (inclusive "ano") para string
        for col in df_spark.columns:
            df_spark = df_spark.withColumn(col, F.col(col).cast("string"))

        print(f"✅ [INFO] Ano {ano} baixado e convertido (coluna ano como string).")
        return df_spark

    def unir_dataframes_dinamicamente(self, lista_dfs):
        print("🛠️ [INFO] Alinhando e unindo DataFrames dinamicamente...")
        colunas_totais = list(set(c for df in lista_dfs for c in df.columns))

        dfs_alinhados = []
        for df in lista_dfs:
            colunas_faltantes = [col for col in colunas_totais if col not in df.columns]
            for col in colunas_faltantes:
                df = df.withColumn(col, F.lit(None).cast("string"))

            # Forçar explicitamente todas as colunas (inclusive "ano") para string
            for col in colunas_totais:
                df = df.withColumn(col, F.col(col).cast("string"))

            df = df.select(colunas_totais)
            dfs_alinhados.append(df)

        df_final = dfs_alinhados[0]
        for df in dfs_alinhados[1:]:
            df_final = df_final.unionByName(df)

        print("✅ [INFO] DataFrames unidos com sucesso.")
        return df_final


    def salvar_com_sobrescrita_parcial(self, df_novo, ano: int):
        print(f"💾 [INFO] Salvando ano {ano} na tabela {self.nome_tabela}...")
        try:
            tabelas = self.spark.sql(f"SHOW TABLES LIKE '{self.nome_tabela}'").collect()
            if not tabelas:
                df_novo.write.format("delta").mode("overwrite").saveAsTable(self.nome_tabela)
                print("✅ [INFO] Tabela criada com sucesso.")
                return

            df_existente = self.spark.table(self.nome_tabela)
            # Ajuste explícito: converte coluna 'ano' existente para string
            df_existente = df_existente.withColumn("ano", F.col("ano").cast("string"))
            
            df_filtrado = df_existente.filter(F.col("ano") != str(ano))
            df_union = self.unir_dataframes_dinamicamente([df_filtrado, df_novo])

            df_union.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(self.nome_tabela)
            print(f"✅ [INFO] Ano {ano} sobrescrito com sucesso.")
        except Exception as e:
            print(f"   🔴 [ERRO] Ao salvar a tabela: {e}")

    def run_ingerir_ano_a_ano(self):
        from datetime import datetime
        ano_corrente = datetime.now().year

        print("🚀 [INFO] Iniciando fluxo incremental mensal.")
        self.descobrir_anos()

        for ano, url_xlsx in self.anos_encontrados:
            df_spark = self.baixar_e_converter_para_spark(ano, url_xlsx)
            if df_spark is None:
                continue

            if ano < ano_corrente:
                self.salvar_com_sobrescrita_parcial(df_spark, ano)
            elif ano == ano_corrente:
                self.salvar_com_sobrescrita_parcial(df_spark, ano)

        print("🏁 [INFO] Processo de ingestão concluído com sucesso!")


# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG dbw_prd_bra_01;
# MAGIC USE SCHEMA ssp_cloud;

# COMMAND ----------

url_base = "https://www.ssp.sp.gov.br"
padrao_excel = "assets/estatistica/transparencia/spDados/SPDadosCriminais_{}.xlsx"
ano_inicial = 2022
nome_tabela = "bronze_sp_dados_criminais"  # Apenas o nome da tabela

ingestor = IngestaoSSPIncrementalMensal(
    spark_session=spark,
    url_base=url_base,
    padrao_caminho_excel=padrao_excel,
    ano_inicial=ano_inicial,
    nome_tabela=nome_tabela
)

ingestor.run_ingerir_ano_a_ano()