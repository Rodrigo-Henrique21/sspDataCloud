import logging
import re
import requests
import os
import azure.functions as func
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient

# Constantes
CONTAINER_NAME = "bronze"
ANOS = [2022, 2023, 2024, 2025]
URL_BASE = "https://www.ssp.sp.gov.br"
URL_CONSULTAS = f"{URL_BASE}/estatistica/consultas"


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Azure Function iniciada.')

    connect_str = os.getenv("AZURE_STORAGE_KEY")
    if not connect_str:
        logging.error("Azure Storage connection string não configurada.")
        return func.HttpResponse(
            "Azure Storage connection string não configurada.",
            status_code=500
        )

    try:
        response = requests.get(URL_CONSULTAS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        anos_desejados = [str(ano) for ano in ANOS]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        for ano in anos_desejados:
            href = f"assets/estatistica/transparencia/spDados/SPDadosCriminais_{ano}.xlsx"
            download_url = f"{URL_BASE}/{href}"

            logging.info(f"Baixando arquivo: {download_url}")

            file_response = requests.get(download_url, headers=headers, timeout=120)
            file_response.raise_for_status()

            blob_name = f"SPDadosCriminais_{ano}.xlsx"
            blob_client = blob_service_client.get_blob_client(
                container=CONTAINER_NAME, blob=blob_name
            )

            blob_client.upload_blob(file_response.content, overwrite=True)

            logging.info(f"Arquivo {blob_name} enviado com sucesso.")

        blobs_enviados = [blob.name for blob in blob_service_client.get_container_client(CONTAINER_NAME).list_blobs()]
        logging.info(f"Blobs atuais no container '{CONTAINER_NAME}': {blobs_enviados}")

        return func.HttpResponse(
            f"Arquivos processados e enviados com sucesso: {', '.join(blobs_enviados)}.",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Erro durante execução: {str(e)}")
        return func.HttpResponse(
            f"Erro durante execução: {str(e)}",
            status_code=500
        )
