# 🏫 Motor de Risco de Evasão Escolar (PE) - Arquitetura MLOps

Este repositório contém o projeto final da 2VA da disciplina de Aprendizado de Máquina. O objetivo deste sistema é operacionalizar um modelo preditivo capaz de identificar precocemente o risco de evasão escolar em municípios, utilizando dados do Censo Escolar da Educação Básica de 2024.

Além da modelagem, o foco central deste projeto é a aplicação rigorosa das práticas de **Machine Learning Operations (MLOps)**, garantindo que o modelo seja rastreável, reproduzível, servido de forma escalável e monitorado em tempo real contra degradação de dados (*Data Drift*).

---

## 🏗️ Decisões Arquiteturais e Tecnológicas

Para garantir a robustez do sistema e a conformidade com as melhores práticas de engenharia de software, a arquitetura foi desenhada com base no princípio de **Separação de Responsabilidades (Separation of Concerns)**. O ecossistema é 100% open-source e orquestrado via Docker.

### 1. Rastreamento e Registro (MLflow + Postgres + MinIO)
O modelo não é um artefato estático no código. O pipeline de treinamento (`train.py`) está integrado ao **MLflow**.
* **PostgreSQL:** Atua como *Backend Store*, guardando os parâmetros, métricas (AUC, Recall, F1) e metadados das execuções.
* **MinIO:** Atua como *Artifact Store* (compatível com S3), armazenando os binários serializados (`cloudpickle`) do modelo Scikit-Learn e do pré-processador (`scaler.joblib`).
* **Decisão:** Isso garante a governança completa do ciclo de vida do modelo. A API de produção consome dinamicamente o modelo que possui a tag/alias `production` diretamente do MLflow Registry.

### 2. Inferência de Baixa Latência (FastAPI)
O modelo é exposto através de uma API REST construída com **FastAPI** e **Uvicorn** (`model-api`).
* **Decisão de Negócio (Ajuste de Limiar):** Para o contexto de evasão escolar, o custo de um Falso Negativo (não identificar um município em crise) é inaceitável. Por isso, a API não utiliza o `.predict()` padrão. Ela extrai as probabilidades via `.predict_proba()` e aplica um limiar de decisão customizado (`0.35`) via software, maximizando o *Recall* sem a necessidade de retreinar o modelo com limiares fixos.
* A API foi projetada para ser enxuta: ela recebe a requisição, aplica o *One-Hot Encoding*, normaliza, classifica, salva a requisição num arquivo de log de produção e responde ao usuário. 

### 3. Monitoramento Desacoplado (Evidently + Prometheus + Grafana)
A monitoria de *Data Drift* envolve cálculos estatísticos pesados que poderiam estrangular o servidor web.
* **Decisão Arquitetural:** O serviço de monitoria (`monitoring`) foi **desacoplado** da API. Ele roda em um contêiner isolado, consumindo assincronamente os logs CSV gerados pela API.
* Ele utiliza a biblioteca **Evidently** para comparar as predições em produção com uma base de referência (Baseline). Se a distribuição das features mudar drasticamente, ele atualiza uma métrica exposta ao **Prometheus**, que por sua vez alimenta os alertas visuais em tempo real no **Grafana**.

### 4. Cliente e Interface de Usuário (Streamlit)
Atendendo ao requisito de usabilidade por não-cientistas de dados (gestores educacionais), foi desenvolvida uma interface interativa com **Streamlit**.
* O Streamlit não carrega o modelo em memória; ele atua puramente como um cliente HTTP consumindo o FastAPI.
* **Modos de Operação:** Permite a análise individual de um contexto escolar específico ou o processamento em Lote (Batch Inference) através do upload de planilhas, gerando um ranking de prioridade de intervenção.

---

## 📂 Estrutura do Repositório

```text
evasao-mlops/
├── data/
│   ├── dataset_integrado.csv    # Dataset processado para treinamento
│   └── reference.csv            # Amostra de baseline para o Evidently
├── config/
│   ├── Dockerfile.mlflow        # Receita do servidor de rastreamento
│   └── prometheus.yml           # Configuração de extração de métricas
├── src/
│   ├── train.py                 # Pipeline de treinamento e MLflow log
│   ├── app.py                   # Motor de Inferência FastAPI
│   ├── monitor.py               # Microsserviço assíncrono de observabilidade
│   ├── dashboard.py             # Cliente UI em Streamlit
│   ├── Dockerfile.api           # Imagem enxuta de inferência
│   ├── Dockerfile.monitoring    # Imagem com compiladores estatísticos
│   └── Dockerfile.frontend      # Imagem do cliente
├── docker-compose.yml           # Orquestrador unificado da infraestrutura
└── pyproject.toml               # Gerenciador de dependências reprodutíveis

```

---

## 🚀 Guia de Execução e Reprodução

**Pré-requisitos:** Docker e Docker Compose instalados no sistema.

### Passo 1: Subir a Infraestrutura Base

Na raiz do repositório, inicie todos os contêineres em segundo plano:

```bash
docker compose up -d

```

*Nota: Aguarde aproximadamente 30 segundos para que os bancos de dados (PostgreSQL e MinIO) fiquem plenamente operacionais antes de prosseguir.*

### Passo 2: Treinar e Registrar o Modelo

Com o ambiente Python virtual ativado e as dependências instaladas (`pip install .`), execute o pipeline de treinamento. O script conectará automaticamente ao MinIO (criando o bucket se necessário) e ao MLflow:

```bash
python src/train.py

```

1. Acesse o MLflow em `http://localhost:5050`.
2. Navegue até **Models** > **RiscoEvasaoModel**.
3. Selecione a versão recém-criada e adicione o *Alias* `production` para sinalizar ao FastAPI que este é o modelo a ser servido.

### Passo 3: Reiniciar a API para Carregamento (Cold Start)

Como o modelo agora possui a tag de produção, reinicie a API para que ela faça o download dos artefatos:

```bash
docker compose restart model-api

```

### Passo 4: Acessar as Interfaces

A sua suíte MLOps agora está no ar e pronta para uso:

* 🖥️ **Painel do Gestor (Frontend):** [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)
* ⚙️ **Documentação OpenAPI (Swagger):** [http://localhost:8001/docs](https://www.google.com/search?q=http://localhost:8001/docs)
* 📈 **Monitoramento (Grafana):** [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000) *(Credenciais: admin/admin)*
* 🧠 **Rastreamento de Experimentos:** [http://localhost:5050](https://www.google.com/search?q=http://localhost:5050)

---

## 🚨 Demonstração de Observabilidade (Data Drift)

Para validar o funcionamento do ciclo de feedback e monitoramento do sistema:

1. Acesse o **Grafana**, conecte o Data Source do Prometheus (`http://prometheus:9090`) e crie um painel observando a métrica `evasao_data_drift_share`.
2. Acesse a interface do **Streamlit** na aba "Análise em Lote".
3. Faça o upload de um arquivo CSV simulando uma catástrofe institucional (escolas com indicadores de reprovação altíssimos e infraestrutura crítica).
4. Submeta o lote.
5. Retorne ao Grafana. Dentro de até 10 segundos, o serviço de `monitoring` detectará a alteração severa na distribuição dos dados em relação ao `reference.csv` e o painel registrará um salto estatístico de *Data Drift*.
