import streamlit as st
import pandas as pd
import os
import glob
import re
from main import executar_pipeline, carregar_municipios

def render_extraction_page():
    # --- SIDEBAR (CONFIGURAÇÕES) ---
    with st.sidebar:
        st.header("Configurações")
        
        # Salvando inputs no session_state para persistir entre as abas/páginas
        if 'ano_input' not in st.session_state: st.session_state.ano_input = 2025
        st.session_state.ano_input = st.number_input("Ano Base", min_value=2000, max_value=2030, value=st.session_state.ano_input)

        lista_municipios = carregar_municipios()
        opcoes_mun = {f"{m['nome_municipio']} ({m['codigo_municipio']})": m for m in lista_municipios}
        
        if 'mun_input' not in st.session_state: st.session_state.mun_input = "Todos"
        st.session_state.mun_input = st.selectbox("Município", options=["Todos"] + list(opcoes_mun.keys()))

        if 'mes_input' not in st.session_state: st.session_state.mes_input = "Todos"
        st.session_state.mes_input = st.selectbox("Mês de Extração", options=["Todos"] + list(range(1, 13)))

        if st.button("Executar Extração"):
            log_container = st.empty()
            log_messages = []
            def stream_log(msg):
                log_messages.append(msg)
                log_container.code("\n".join(log_messages[-50:]))

            municipio_selecionado = None if st.session_state.mun_input == "Todos" else opcoes_mun[st.session_state.mun_input]
            with st.spinner("Buscando dados no TCE..."):
                executar_pipeline(st.session_state.ano_input, mes_selecionado=st.session_state.mes_input, municipio_selecionado=municipio_selecionado, log_func=stream_log)
                st.success("Extração concluída!")

    # --- ÁREA PRINCIPAL ---
    st.header("Visualizar Dados")
    
    def carregar_e_exibir_dados(tipo_dado):
        # Usando os valores do session_state
        ano = st.session_state.ano_input
        mun_input = st.session_state.mun_input
        mes_input = st.session_state.mes_input

        if mun_input == "Todos":
            mun_code = "*"
        else:
            match = re.search(r'\((\d+)\)', mun_input)
            mun_code = match.group(1) if match else "*"

        mes_str = "*" if mes_input == "Todos" else str(mes_input).zfill(2)
        padrao = os.path.join('data', f"{tipo_dado}_{ano}_{mes_str}_{mun_code}.parquet")
        arquivos = glob.glob(padrao)

        st.write(f"Buscando: {padrao}")

        if not arquivos:
            st.warning(f"Nenhum arquivo encontrado.")
            return

        if st.button(f"Filtrar e Carregar ({len(arquivos)} arquivos)", key=f"btn_{tipo_dado}"):
            with st.spinner("Carregando..."):
                df = pd.concat([pd.read_parquet(f) for f in arquivos], ignore_index=True)
                df = df.astype(str)
                st.success(f"Carregados {len(df)} registros!")
                st.dataframe(df, use_container_width=True)
                st.download_button("Baixar (CSV)", data=df.to_csv(index=False, sep=';').encode('utf-8-sig'), file_name=f"dados_{tipo_dado}.csv", mime='text/csv')

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Notas de Empenho", "Notas Fiscais", "Notas de Pagamento", "Pagamento e Liquidações", "Liquidações", "Itens de Notas Fiscais"])
    with tab1: carregar_e_exibir_dados("notas_empenho")
    with tab2: carregar_e_exibir_dados("notas_fiscais")
    with tab3: carregar_e_exibir_dados("notas_pagamentos")
    with tab4: carregar_e_exibir_dados("Pagamento e Liquidações")
    with tab5: carregar_e_exibir_dados("liquidacoes")
    with tab6: carregar_e_exibir_dados("itens_notas_fiscais")