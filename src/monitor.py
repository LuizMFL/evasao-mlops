# src/monitor.py
import time
import os
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from prometheus_client import start_http_server, Gauge, Counter

DRIFT_GAUGE = Gauge("evasao_data_drift_share", "Porcentagem de Data Drift")
PREDICTION_COUNT = Counter("evasao_predicoes", "Total de predições monitoradas")

def run_monitoring():
    print("Iniciando serviço de monitoramento Evidently na porta 8002...")
    start_http_server(8002)

    # Inicia os ponteiros no zero para o Grafana acordar vivo
    DRIFT_GAUGE.set(0.0)

    # LOOP DE SOBREVIVÊNCIA: O contêiner não morre mais se o arquivo faltar!
    while not os.path.exists("data/reference.csv"):
        print("⏳ Aguardando a geração da base de referência (data/reference.csv)...")
        time.sleep(5)

    try:
        reference = pd.read_csv("data/reference.csv")
        print("✅ Base de referência carregada com sucesso! Iniciando auditoria contínua...")
    except Exception as e:
        print(f"❌ Erro fatal ao carregar reference.csv: {e}")
        return

    linhas_processadas = 0

    while True:
        try:
            current = pd.read_csv("data/production_logs.csv")
            linhas_atuais = len(current)

            # Reage imediatamente a qualquer clique novo
            if linhas_atuais > linhas_processadas:
                novas_linhas = linhas_atuais - linhas_processadas
                PREDICTION_COUNT.inc(novas_linhas)
                linhas_processadas = linhas_atuais
                print(f"Novas predições registradas: {novas_linhas}. Total em produção: {linhas_atuais}")

                # Drift só é calculado se houver uma amostra mínima de 5 predições
                if linhas_atuais >= 5:
                    print("Calculando Drift estatístico do lote...")
                    report = Report(metrics=[DataDriftPreset()])
                    colunas = reference.columns.tolist()
                    current_filtered = current[colunas]

                    report.run(reference_data=reference, current_data=current_filtered)
                    drift_share = report.as_dict()["metrics"][0]["result"]["share_of_drifted_columns"]

                    DRIFT_GAUGE.set(drift_share)
                    print(f"Drift Atualizado para o Grafana: {drift_share:.2f}")

        except pd.errors.EmptyDataError:
            pass # Arquivo existe mas está vazio
        except Exception as e:
            print(f"Aguardando novas predições na API...")

        time.sleep(5) # Atualiza a cada 5s para ser rápido na apresentação

if __name__ == '__main__':
    run_monitoring()