# src/app.py (Versão Enxuta e Correta)
import os
import joblib
import pandas as pd
import mlflow
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Motor de Risco de Evasão Escolar (PE)")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
model = None
scaler = None
LIMIAR_RISCO = 0.35
LOG_FILE = "data/production_logs.csv"

class MunicipioInput(BaseModel):
    reprov_fund_total: float
    reprov_fund_anos_finais: float
    reprov_med_total: float
    reprov_med_1serie: float
    pct_internet: float
    pct_biblioteca: float
    pct_lab_informatica: float
    pct_quadra: float
    pct_agua_potavel: float
    pct_sem_esgoto: float
    pct_sem_acessibilidade: float
    pct_alimentacao: float
    qt_salas_media: float
    localizacao: str
    dependencia_adm: str


@app.on_event("startup")
def carregar_modelos():
    global model, scaler
    try:
        client = mlflow.MlflowClient()
        model_version = client.get_model_version_by_alias("RiscoEvasaoModel", "production")
        model = mlflow.sklearn.load_model(f"models:/RiscoEvasaoModel@production")
        scaler_path = mlflow.artifacts.download_artifacts(run_id=model_version.run_id,
                                                          artifact_path="preprocessor/scaler.joblib")
        scaler = joblib.load(scaler_path)

        if not os.path.exists(LOG_FILE):
            pd.DataFrame(columns=list(MunicipioInput.schema()["properties"].keys())).to_csv(LOG_FILE, index=False)

        print("✅ API Pronta para Inferência!")
    except Exception as e:
        print(f"❌ Erro no startup: {e}")


@app.post("/predict")
def prever_risco(dados: MunicipioInput):
    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="Modelo offline.")

    try:
        dados_dict = dados.dict()
        df = pd.DataFrame([dados_dict])

        df.to_csv(LOG_FILE, mode='a', header=False, index=False)

        todas_features = [
            "reprov_fund_total", "reprov_fund_anos_finais", "reprov_med_total", "reprov_med_1serie",
            "pct_internet", "pct_biblioteca", "pct_lab_informatica", "pct_quadra", "pct_agua_potavel",
            "pct_sem_esgoto", "pct_sem_acessibilidade", "pct_alimentacao", "qt_salas_media",
            "localizacao_Rural", "localizacao_Total", "localizacao_Urbana", "dependencia_adm_Estadual",
            "dependencia_adm_Federal", "dependencia_adm_Municipal", "dependencia_adm_Privada", "dependencia_adm_Total"
        ]
        df_encoded = pd.get_dummies(df, columns=["localizacao", "dependencia_adm"])
        for col in todas_features:
            if col not in df_encoded.columns: df_encoded[col] = 0

        X_novo = df_encoded[todas_features]
        probabilidade = model.predict_proba(scaler.transform(X_novo))[0][1]
        classificacao = 1 if probabilidade >= LIMIAR_RISCO else 0

        return {
            "risco_evasao": classificacao,
            "probabilidade": float(probabilidade),
            "status": "ALTO RISCO" if classificacao == 1 else "BAIXO RISCO"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))