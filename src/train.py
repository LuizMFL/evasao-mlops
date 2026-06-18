# src/train.py
import pandas as pd
import joblib
import mlflow.sklearn
import boto3
from botocore.exceptions import ClientError
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, recall_score, f1_score
import os

os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
os.environ["AWS_ACCESS_KEY_ID"] = "admin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "adminpassword"

s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
)
try:
    s3_client.head_bucket(Bucket="mlflow-artifacts")
except ClientError:
    print("🛠️ Bucket 'mlflow-artifacts' não encontrado. Criando automaticamente no MinIO...")
    s3_client.create_bucket(Bucket="mlflow-artifacts")
# --------------------------------------

mlflow.set_tracking_uri("http://localhost:5050")
mlflow.set_experiment("Risco_Evasao_Pernambuco")

print("Carregando o dataset integrado...")
df = pd.read_csv("data/dataset_integrado.csv")

features_numericas = [
    "reprov_fund_total", "reprov_fund_anos_finais", "reprov_med_total",
    "reprov_med_1serie", "pct_internet", "pct_biblioteca",
    "pct_lab_informatica", "pct_quadra", "pct_agua_potavel",
    "pct_sem_esgoto", "pct_sem_acessibilidade", "pct_alimentacao",
    "qt_salas_media"
]

features_categoricas = ["localizacao", "dependencia_adm"]

df = df[features_numericas + features_categoricas + ["risco_evasao"]].dropna()

df_encoded = pd.get_dummies(df, columns=features_categoricas, dtype=int)

todas_features = [
    "reprov_fund_total", "reprov_fund_anos_finais", "reprov_med_total",
    "reprov_med_1serie", "pct_internet", "pct_biblioteca",
    "pct_lab_informatica", "pct_quadra", "pct_agua_potavel",
    "pct_sem_esgoto", "pct_sem_acessibilidade", "pct_alimentacao",
    "qt_salas_media", "localizacao_Rural", "localizacao_Total",
    "localizacao_Urbana", "dependencia_adm_Estadual", "dependencia_adm_Federal",
    "dependencia_adm_Municipal", "dependencia_adm_Privada", "dependencia_adm_Total"
]

for col in todas_features:
    if col not in df_encoded.columns:
        df_encoded[col] = 0

X = df_encoded[todas_features]
y = df_encoded["risco_evasao"]

print(f"Shape de X: {X.shape} | Shape de y: {y.shape}")

# Separação
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

print("Iniciando treinamento e registro no MLflow...")
with mlflow.start_run(run_name="RandomForest_Tuned_Producao") as run:
    # Normalização
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Salvar e logar o scaler
    joblib.dump(scaler, "scaler.joblib")
    mlflow.log_artifact("scaler.joblib", artifact_path="preprocessor")

    # Treinar o Random Forest Campeão
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        class_weight='balanced',
        random_state=42
    )
    rf_model.fit(X_train_scaled, y_train)

    # Previsões
    y_pred = rf_model.predict(X_test_scaled)
    y_proba = rf_model.predict_proba(X_test_scaled)[:, 1]

    # Calcular Métricas
    auc = roc_auc_score(y_test, y_proba)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    # Registrar no MLflow
    mlflow.log_param("algoritmo", "Random Forest")
    mlflow.log_param("class_weight", "balanced")
    mlflow.log_metric("roc_auc", auc)
    mlflow.log_metric("recall_base", recall)
    mlflow.log_metric("f1_score", f1)

    # Registrar o Modelo no Registry
    mlflow.sklearn.log_model(
        sk_model=rf_model,
        artifact_path="random_forest_model",
        registered_model_name="RiscoEvasaoModel",
        serialization_format = "cloudpickle"
    )

    print(f"✅ Sucesso! Run ID: {run.info.run_id}")
    print(f"📊 AUC: {auc:.3f} | Recall Base: {recall:.3f}")

    print("⚙️ Automatizando a tag de Produção no Model Registry...")
    client = mlflow.MlflowClient()

    versoes = client.search_model_versions("name='RiscoEvasaoModel'")
    ultima_versao = max([int(v.version) for v in versoes])

    client.set_registered_model_alias("RiscoEvasaoModel", "production", str(ultima_versao))
    print(f"🚀 Versão {ultima_versao} promovida para 'production' com sucesso!")