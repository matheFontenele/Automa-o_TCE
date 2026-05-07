import streamlit as st
import pandas as pd
import os
import glob
import re
from main import executar_pipeline, carregar_municipios

# Mapeamento para garantir que o nome da aba encontre o arquivo correto no disco
DATA_MAP = {
    "Notas de Empenho": "notas_empenho",
    "Notas Fiscais": "notas_fiscais",
    "Notas de Pagamento": "notas_pagamentos",
    "Pagamento e Liquidações": "pagamento_e_liquidacoes",
    "Liquidações": "liquidacoes",
    "Itens de Notas Fiscais": "itens_notas_fiscais"
}

def render_extraction_page():
    # --- SIDEBAR (CONFIGURAÇÕES) ---
    with st.sidebar:
        st.header("Configurações")
        
        # Persistência de estado
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

    def carregar_e_exibir_dados(tipo_arquivo_prefixo):
        # 1. Recuperar valores do session_state
        ano = st.session_state.ano_input
        mes = st.session_state.mes_input
        mun = st.session_state.mun_input

        # 2. Configurar wildcards
        ano_str = "*" if ano == "Todos" else str(ano)
        mes_str = "*" if mes == "Todos" else str(mes).zfill(2)
        
        if mun == "Todos":
            mun_str = "*"
        else:
            match = re.search(r'\((\d+)\)', mun)
            mun_str = match.group(1) if match else "*"

        # 3. Determinar o padrão de nome
        # Se for itens de notas fiscais ou algo sem mês no nome, ajusta o padrão
        if "itens_notas_fiscais" in tipo_arquivo_prefixo:
            padrao = os.path.join('data', f"{tipo_arquivo_prefixo}_{ano_str}_{mun_str}.parquet")
        else:
            padrao = os.path.join('data', f"{tipo_arquivo_prefixo}_{ano_str}_{mes_str}_{mun_str}.parquet")

        arquivos = glob.glob(padrao)

        with st.expander("Ver detalhes da busca"):
            st.write(f"Padrão: `{padrao}`")
            st.write(f"Arquivos encontrados: {len(arquivos)}")

        if not arquivos:
            st.warning("Nenhum arquivo encontrado.")
            return

        # 4. Botão de carga
        if st.button(f"Carregar {len(arquivos)} arquivos", key=f"btn_{tipo_arquivo_prefixo}"):
            with st.spinner("Consolidando..."):
                try:
                    df_lista = [pd.read_parquet(f) for f in arquivos]
                    df = pd.concat(df_lista, ignore_index=True)
                    df = df.astype(str)

                    st.success(f"Sucesso! {len(df)} registros totais.")

                    # --- FILTROS INTERNOS ---
                    st.divider()
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'municipio_referencia' in df.columns:
                            mun_filter = st.multiselect("Filtrar por Município no Resultado:", options=sorted(df['municipio_referencia'].unique()))
                            if mun_filter:
                                df = df[df['municipio_referencia'].isin(mun_filter)]

                    with col2:
                        # Filtro de busca textual geral
                        busca = st.text_input("Busca rápida (CPF, CNPJ, Nome...):")
                        if busca:
                            # Filtra em todas as colunas
                            df = df[df.apply(lambda row: row.astype(str).str.contains(busca, case=False).any(), axis=1)]

                    st.info(f"Exibindo {min(1000, len(df))} de {len(df)} registros filtrados.")
                    st.dataframe(df.head(1000), use_container_width=True)
                    # ------------------------------

                    # Download do arquivo filtrado
                    st.download_button(
                        label="Baixar resultado atual (CSV)",
                        data=df.to_csv(index=False, sep=';').encode('utf-8-sig'),
                        file_name=f"filtro_{tipo_arquivo_prefixo}.csv",
                        mime='text/csv'
                    )
                except Exception as e:
                    st.error(f"Erro ao carregar: {e}")

    # Criação dinâmica das abas usando o dicionário
    abas = st.tabs(list(DATA_MAP.keys()))
    
    for i, nome_aba in enumerate(DATA_MAP.keys()):
        with abas[i]:
            # Passa o valor real do arquivo (prefixo) para a função
            carregar_e_exibir_dados(DATA_MAP[nome_aba])