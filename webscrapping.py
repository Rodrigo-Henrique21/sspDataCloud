import logging
import re
import requests
import os
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient

# Credenciais atualizadas para Azure Blob Storage
CONNECT_STR = os.getenv("AZURE_STORAGE_KEY")
CONTAINER_NAME = "bronze"

# Anos para download
ANOS = [2022, 2023, 2024, 2025]

# URL base
url_base = "https://www.ssp.sp.gov.br"
url_consultas = f"{url_base}/estatistica/consultas"

try:
    logging.basicConfig(level=logging.INFO)

    logging.info('Iniciando scraping...')

    response = requests.get(url_consultas, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    blob_service_client = BlobServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_KEY")
    )

    container_name = CONTAINER_NAME

    anos_desejados = [str(ano) for ano in ANOS]

    pattern = re.compile(r'SPDadosCriminais_(\d{4})\.xlsx')

    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all("a", href=pattern)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for ano in anos_desejados:
        href = f"assets/estatistica/transparencia/spDados/SPDadosCriminais_{ano}.xlsx"
        download_url = f"{url_base}/{href}"

        logging.info(f"Baixando arquivo {download_url}")

        file_response = requests.get(download_url, headers=headers, timeout=120)
        file_response.raise_for_status()
        file_bytes = file_response.content

        blob_name = f"SPDadosCriminais_{ano}.xlsx"

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(file_bytes, overwrite=True)

        logging.info(f"Arquivo {blob_name} enviado com sucesso.")

    # Listar blobs para confirmação
    logging.info("Listando arquivos no container após upload:")
    blob_list = blob_service_client.get_container_client(container_name).list_blobs()
    for blob in blob_list:
        logging.info(f"- {blob.name}")

    logging.info('Processo finalizado com sucesso.')

except Exception as e:
    logging.error(f"Erro durante execução: {e}")