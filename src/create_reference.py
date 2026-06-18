# src/create_reference.py
import pandas as pd
import os

print("⏳ Lendo o dataset de produção...")

caminho_dataset = "data/dataset_integrado.csv"
caminho_referencia = "data/reference.csv"

if not os.path.exists(caminho_dataset):
    print(f"❌ Erro: O arquivo {caminho_dataset} não foi encontrado na raiz do projeto.")
    exit()

df = pd.read_csv(caminho_dataset)

features = [
    "reprov_fund_total", "reprov_fund_anos_finais", "reprov_med_total",
    "reprov_med_1serie", "pct_internet", "pct_biblioteca",
    "pct_lab_informatica", "pct_quadra", "pct_agua_potavel",
    "pct_sem_esgoto", "pct_sem_acessibilidade", "pct_alimentacao",
    "qt_salas_media", "localizacao", "dependencia_adm"
]

df_filtrado = df[features]

df_ref = df_filtrado.sample(n=1000, random_state=42)

df_ref.to_csv(caminho_referencia, index=False)

print(f"✅ Sucesso! O gabarito de monitoramento foi salvo em: {caminho_referencia}")