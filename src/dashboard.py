import streamlit as st
import requests
import pandas as pd
import time

# Configuração da página
st.set_page_config(page_title="Prevenção de Evasão Escolar", page_icon="🏫", layout="wide")

API_URL = "http://fastapi_backend:8000/predict"

st.title("🏫 Painel de Triagem de Evasão Escolar")
st.markdown("Plataforma de Inteligência Artificial para identificação precoce de risco de abandono escolar.")

# Criando abas para separar a análise individual da análise em lote
tab1, tab2 = st.tabs(["🔍 Análise Individual", "📁 Análise em Lote (Planilha)"])

# ---------------------------------------------------------
# ABA 1: ANÁLISE INDIVIDUAL
# ---------------------------------------------------------
with tab1:
    st.markdown("Insira os indicadores de um município ou escola específica para avaliação instantânea.")
    with st.form("form_municipio"):
        st.subheader("📊 Indicadores Educacionais e de Infraestrutura")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Taxas de Reprovação (%)**")
            reprov_fund_total = st.number_input("Ensino Fund. (Total)", min_value=0.0, max_value=100.0, value=5.0)
            reprov_fund_anos_finais = st.number_input("Ensino Fund. (Anos Finais)", min_value=0.0, max_value=100.0,
                                                      value=7.0)
            reprov_med_total = st.number_input("Ensino Médio (Total)", min_value=0.0, max_value=100.0, value=10.0)
            reprov_med_1serie = st.number_input("Ensino Médio (1ª Série)", min_value=0.0, max_value=100.0, value=12.0)

            st.markdown("**Contexto**")
            localizacao = st.selectbox("Localização", ["Rural", "Urbana", "Total"])
            dependencia_adm = st.selectbox("Dependência Administrativa", ["Estadual", "Municipal", "Privada", "Total"])

        with col2:
            st.markdown("**Infraestrutura Básica (%)**")
            pct_internet = st.number_input("Acesso à Internet", min_value=0.0, max_value=100.0, value=80.0)
            pct_biblioteca = st.number_input("Possui Biblioteca", min_value=0.0, max_value=100.0, value=60.0)
            pct_lab_informatica = st.number_input("Laboratório de Informática", min_value=0.0, max_value=100.0,
                                                  value=50.0)
            pct_quadra = st.number_input("Quadra de Esportes", min_value=0.0, max_value=100.0, value=70.0)
            qt_salas_media = st.number_input("Média de Salas de Aula", min_value=0.0, value=10.0)

        with col3:
            st.markdown("**Saneamento e Acessibilidade (%)**")
            pct_agua_potavel = st.number_input("Água Potável", min_value=0.0, max_value=100.0, value=95.0)
            pct_sem_esgoto = st.number_input("Sem Rede de Esgoto", min_value=0.0, max_value=100.0, value=20.0)
            pct_sem_acessibilidade = st.number_input("Sem Acessibilidade", min_value=0.0, max_value=100.0, value=30.0)
            pct_alimentacao = st.number_input("Oferece Alimentação", min_value=0.0, max_value=100.0, value=100.0)

        submit_button = st.form_submit_button(label="🔍 Analisar Risco de Evasão", use_container_width=True)

    if submit_button:
        dados_entrada = {
            "reprov_fund_total": reprov_fund_total,
            "reprov_fund_anos_finais": reprov_fund_anos_finais,
            "reprov_med_total": reprov_med_total,
            "reprov_med_1serie": reprov_med_1serie,
            "pct_internet": pct_internet,
            "pct_biblioteca": pct_biblioteca,
            "pct_lab_informatica": pct_lab_informatica,
            "pct_quadra": pct_quadra,
            "pct_agua_potavel": pct_agua_potavel,
            "pct_sem_esgoto": pct_sem_esgoto,
            "pct_sem_acessibilidade": pct_sem_acessibilidade,
            "pct_alimentacao": pct_alimentacao,
            "qt_salas_media": qt_salas_media,
            "localizacao": localizacao,
            "dependencia_adm": dependencia_adm
        }

        with st.spinner("Consultando Motor de Risco MLOps..."):
            try:
                resposta = requests.post(API_URL, json=dados_entrada)
                if resposta.status_code == 200:
                    resultado = resposta.json()
                    st.markdown("---")
                    st.subheader("Resultado da Triagem")
                    status = resultado['status']
                    probabilidade = resultado['probabilidade'] * 100

                    if status == "ALTO RISCO":
                        st.error(f"🚨 **{status} DETECTADO**")
                        st.markdown(f"**Probabilidade de Evasão:** `{probabilidade:.1f}%`")
                        st.warning("Este município exige intervenção pedagógica e estrutural imediata.")
                    else:
                        st.success(f"✅ **{status}**")
                        st.markdown(f"**Probabilidade de Evasão:** `{probabilidade:.1f}%`")
                        st.info("O contexto escolar está dentro da margem de segurança e retenção.")
                else:
                    st.error(f"Erro na API: {resposta.text}")
            except Exception:
                st.error("❌ Não foi possível conectar ao Backend (FastAPI).")

with tab2:
    st.markdown(
        "Faça o upload de uma planilha contendo os dados de várias escolas/municípios para gerar um ranking de prioridade.")

    uploaded_file = st.file_uploader("Envie seu arquivo CSV", type=["csv"])

    if uploaded_file is not None:
        df_batch = pd.read_csv(uploaded_file)
        st.write(f"Arquivo carregado com **{len(df_batch)}** registros.")

        if st.button("🚀 Processar Lote", type="primary"):
            progress_bar = st.progress(0)
            resultados_lista = []

            registros = df_batch.to_dict('records')

            for i, reg in enumerate(registros):
                try:
                    # Garantir que nulos se tornem 0
                    for k, v in reg.items():
                        if pd.isna(v): reg[k] = 0.0

                    if "localizacao" not in reg or str(reg["localizacao"]) == "nan": reg["localizacao"] = "Total"
                    if "dependencia_adm" not in reg or str(reg["dependencia_adm"]) == "nan": reg[
                        "dependencia_adm"] = "Total"

                    dados_api = {
                        "reprov_fund_total": float(reg.get("reprov_fund_total", 0)),
                        "reprov_fund_anos_finais": float(reg.get("reprov_fund_anos_finais", 0)),
                        "reprov_med_total": float(reg.get("reprov_med_total", 0)),
                        "reprov_med_1serie": float(reg.get("reprov_med_1serie", 0)),
                        "pct_internet": float(reg.get("pct_internet", 0)),
                        "pct_biblioteca": float(reg.get("pct_biblioteca", 0)),
                        "pct_lab_informatica": float(reg.get("pct_lab_informatica", 0)),
                        "pct_quadra": float(reg.get("pct_quadra", 0)),
                        "pct_agua_potavel": float(reg.get("pct_agua_potavel", 0)),
                        "pct_sem_esgoto": float(reg.get("pct_sem_esgoto", 0)),
                        "pct_sem_acessibilidade": float(reg.get("pct_sem_acessibilidade", 0)),
                        "pct_alimentacao": float(reg.get("pct_alimentacao", 0)),
                        "qt_salas_media": float(reg.get("qt_salas_media", 0)),
                        "localizacao": str(reg.get("localizacao", "Total")),
                        "dependencia_adm": str(reg.get("dependencia_adm", "Total"))
                    }

                    resposta = requests.post(API_URL, json=dados_api)
                    if resposta.status_code == 200:
                        pred = resposta.json()
                        reg["Risco (IA)"] = pred["status"]
                        reg["Probabilidade (%)"] = round(pred["probabilidade"] * 100, 2)
                    else:
                        reg["Risco (IA)"] = "Erro"
                        reg["Probabilidade (%)"] = 0.0

                except Exception as e:
                    reg["Risco (IA)"] = "Erro de Conexão"
                    reg["Probabilidade (%)"] = 0.0

                resultados_lista.append(reg)
                progress_bar.progress((i + 1) / len(registros))

            st.success("✅ Processamento concluído!")

            df_resultados = pd.DataFrame(resultados_lista)
            df_resultados = df_resultados.sort_values(by="Probabilidade (%)", ascending=False)

            st.subheader("🏆 Ranking de Prioridade de Intervenção")
            st.dataframe(
                df_resultados.style.applymap(
                    lambda val: 'background-color: #ffcccc' if val == 'ALTO RISCO' else (
                        'background-color: #ccffcc' if val == 'BAIXO RISCO' else ''),
                    subset=['Risco (IA)']
                ),
                use_container_width=True
            )

            csv = df_resultados.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Relatório Analítico",
                data=csv,
                file_name='ranking_evasao_mlops.csv',
                mime='text/csv',
            )