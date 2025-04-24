# 📊 sspDataCloud

Projeto de análise de dados criminais da **Secretaria de Segurança Pública do Estado de São Paulo (SSP-SP)** utilizando **Python**, **Databricks** e infraestrutura em nuvem com **Microsoft Azure**.

---

## 📌 Visão Geral

O objetivo deste projeto é **extrair, transformar e analisar** dados públicos sobre ocorrências criminais, promovendo insights relevantes para a segurança pública do estado de São Paulo. A arquitetura foi desenhada para ser **escalável, automatizada e de alta performance**, utilizando tecnologias modernas de Big Data e Cloud Computing.

---

## 🧱 Arquitetura da Solução

A arquitetura do projeto foi pensada para alto desempenho e integração total com a nuvem:

- **Azure Databricks**  
  Plataforma principal para desenvolvimento em Python com suporte ao Apache Spark, permitindo processamento distribuído de grandes volumes de dados.

- **Azure Data Lake Storage (ADLS)**  
  Camadas de dados brutos (`raw`), tratados (`curated`) e analíticos (`analytics`), garantindo governança e versionamento dos dados.

- **Azure Databricks Workflow**  
  Responsável pela orquestração dos pipelines de ETL (Extract, Transform, Load), automatizando todo o fluxo de ingestão de dados.


---

## 🧪 Tecnologias Utilizadas

- **Python 3.x**
- **PySpark**
- **Azure SDK (para Python)**
- **Databricks Notebooks**
- **Azure CLI e ARM Templates**

---

## 🛠️ Funcionalidades

- Extração de dados da SSP-SP via `requests` e `parsing`.
- Transformações com **PySpark** no **Databricks**.
- Armazenamento em múltiplas camadas no **Azure Data Lake**.
- Organização dos dados por diretórios particionados por `ano/mês`.
- Deploy e configuração de infraestrutura via **Infraestrutura como Código (IaC)** com **ARM Templates** e **Azure CLI**.

---

## 📂 Estrutura do Projeto

```
sspDataCloud/
├── docs/                 # Documentação do projeto
├── infra/                # Scripts de infraestrutura e provisionamento
├── src/                  # Código-fonte principal
│   ├── extraction/       # Scripts de extração de dados
│   ├── transformation/   # Scripts de transformação e limpeza
│   └── analysis/         # Scripts de análise e visualização
├── workflow/             # Definições de pipelines e workflows
├── requirements.txt      # Dependências do projeto
└── README.md             # Este arquivo
```

## 🚀 Como Executar
- Clone o repositório:

```
  git clone https://github.com/Rodrigo-Henrique21/sspDataCloud.git
cd sspDataCloud
```

### Instale as dependências:

- Certifique-se de que você tenha o Python 3.8 ou superior instalado. Em seguida, instale as dependências:

```
pip install -r requirements.txt
```

- Configure as credenciais:

- Adicione suas credenciais da Azure e configurações necessárias nos arquivos de configuração apropriados.

### Execute os scripts:

- Utilize os notebooks no Databricks ou execute os scripts diretamente para iniciar o processo de ETL.

---

## 📈 Resultados Esperados

- Extração automatizada de dados criminais da SSP-SP.
- Transformação e limpeza dos dados para facilitar a análise.
- Armazenamento estruturado e particionado no **Azure Data Lake**.
- Visualizações e insights analíticos sobre a criminalidade no estado de São Paulo.

---

## 📄 Licença

Este projeto está licenciado sob a **Licença MIT**. Consulte o arquivo [LICENSE](./LICENSE) para mais detalhes.

---

> Para mais informações, acesse o repositório: `sspDataCloud`  

