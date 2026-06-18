# 🏫 Motor de Risco de Evasão Escolar (PE) - Arquitetura MLOps

Este repositório contém o projeto final da 2VA da disciplina de Aprendizado de Máquina. O objetivo deste sistema é operacionalizar um modelo preditivo capaz de identificar precocemente o risco de evasão escolar em municípios (utilizando dados do Censo Escolar da Educação Básica), com aplicação rigorosa das práticas de **Machine Learning Operations (MLOps)**.

---

## 🏗️ A Arquitetura (Separation of Concerns)

Para refletir um ambiente de produção real, o sistema foi estruturado separando o pipeline de treinamento do serviço de inferência e do monitoramento assíncrono:
1. **Tracking & Registry:** MLflow + PostgreSQL + MinIO (S3).
2. **Serving:** FastAPI + Uvicorn (O modelo não é embutido no código; ele é baixado dinamicamente do Registry).
3. **Monitoring:** Evidently + Prometheus + Grafana (Microsserviço totalmente desacoplado da API, lendo logs de forma assíncrona na porta `8002` para não onerar a inferência).
4. **Client/Frontend:** Streamlit (Atua puramente como cliente, consumindo a API via REST).

---

## 🚀 Guia de Execução do Zero (Cold Start)

Como a infraestrutura é criada do zero (bancos de dados e storages vazios), o fluxo de inicialização segue a ordem cronológica de MLOps: **Subir a Infraestrutura Base -> Executar o Pipeline de Treinamento -> Ativar o Motor de Inferência**.

### Passo 1: Iniciar os Contêineres da Stack
Na raiz do repositório, levante toda a infraestrutura orquestrada:
```bash
docker compose up -d

```

*Observação de Engenharia: Neste momento, o contêiner da API (`model-api`) subirá, mas identificará no log que o banco de dados do MLflow está virgem e o alias de produção não existe. Ela apresentará um aviso no log, mas permanecerá rodando (resiliência ativa), aguardando o primeiro registro.*

### Passo 2: Executar o Pipeline de Treinamento

Com os contêineres rodando de fundo, execute o pipeline de treinamento na sua máquina (certifique-se de ter ativado seu ambiente virtual e instalado as dependências fixadas do projeto):

```bash
python src/train.py

```

*Nota de Automação: O script irá carregar o dataset integrado, normalizar os dados, treinar o Random Forest ajustado, salvá-lo no MinIO S3 e, através do MLflowClient, irá promover essa versão de forma 100% automatizada para o alias `production` no Model Registry.*

### Passo 3: Reiniciar a API para Carregamento (Warm Up)

Agora que o modelo campeão está registrado com a tag oficial de produção, reinicie o contêiner da API para forçar o gatilho de *startup* que baixa os artefatos para a memória:

```bash
docker compose restart model-api

```

---

## 🖥️ Portas de Acesso às Interfaces

Com a stack completamente aquecida, você pode acessar os serviços nas seguintes URLs locais:

* 👨‍🏫 **Painel do Gestor (Streamlit UI):** [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)
* ⚙️ **Documentação OpenAPI (Swagger API):** [http://localhost:8001/docs](https://www.google.com/search?q=http://localhost:8001/docs)
* 📈 **Observabilidade de Produção (Grafana):** [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000) *(Credenciais: admin / admin)*
* 🧠 **Rastreamento de Modelos (MLflow):** [http://localhost:5050](https://www.google.com/search?q=http://localhost:5050)

---

## 🚨 Validação do Monitoramento (Simulando Data Drift)

O painel do Grafana já nasce pré-provisionado de forma automatizada via código, eliminando a necessidade de qualquer configuração manual em tela. Para validar o circuito de feedback:

1. Acesse o **Grafana** (`http://localhost:3000`) e abra o dashboard **"Motor de Risco MLOps"**.
2. Acesse a interface do **Streamlit** e mude para a aba **"📁 Análise em Lote (Planilha)"**.
3. Faça o upload de um arquivo CSV simulando uma degradação estatística severa (por exemplo, enviando municípios com taxas de reprovação elevadas e infraestrutura básica zerada).
4. Clique em **"Processar Lote"**.
5. Retorne imediatamente ao Grafana. Como o microsserviço `monitor.py` realiza o cálculo estatístico via **Evidently** de maneira assíncrona, aguarde a janela de varredura (até 10 segundos). O velocímetro de **Data Drift** registrará o desvio populacional e mudará visualmente para a zona de alerta.
