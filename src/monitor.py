# src/monitor.py
import time
import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from prometheus_client import start_http_server, Gauge, Counter


DRIFT_GAUGE = Gauge("evasao_data_drift_share", "Porcentagem de Data Drift")
PREDICTION_COUNT = Counter("evasao_predicoes_total", "Total de predições monitoradas")


def run_monitoring():
    print("Iniciando serviço de monitoramento Evidently na porta 8002...")
    start_http_server(8002)

    # Carrega a base padrão
    try:
        reference = pd.read_csv("data/reference.csv")
    except Exception as e:
        print("Erro ao carregar reference.csv. Verifique os dados.")
        return

    linhas_processadas = 0

    while True:
        try:
            current = pd.read_csv("data/production_logs.csv")
            linhas_atuais = len(current)

            if linhas_atuais >= linhas_processadas + 5:
                print(f"Calculando Drift para {linhas_atuais} instâncias em produção...")
                report = Report(metrics=[DataDriftPreset()])

                colunas = reference.columns.tolist()
                current_filtered = current[colunas]

                report.run(reference_data=reference, current_data=current_filtered)
                drift_share = report.as_dict()["metrics"][0]["result"]["share_of_drifted_columns"]

                DRIFT_GAUGE.set(drift_share)
                PREDICTION_COUNT.inc(linhas_atuais - linhas_processadas)
                linhas_processadas = linhas_atuais
                print(f"Drift Atualizado: {drift_share:.2f}")

        except pd.errors.EmptyDataError:
            pass
        except Exception as e:
            print(f"Aguardando logs de produção: {e}")

        time.sleep(10)


if __name__ == '__main__':
    run_monitoring()