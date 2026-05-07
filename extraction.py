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
        
        if mes == "Todos":
            mes_str = "*" 
        else:
            # Garante que 1 vire "01" para bater com o nome do arquivo
            mes_str = str(mes).zfill(2)
        
        if mun == "Todos":
            mun_str = "*"
        else:
            # Extrai apenas o número entre parênteses, ex: (043) -> 043
            match = re.search(r'\((\d+)\)', mun)
            mun_str = match.group(1) if match else "*"

        # 3. Determinar o padrão de nome (Glob)
        if "itens_notas_fiscais" in tipo_arquivo_prefixo:
            # Itens não tem mês no nome
            nome_busca = f"{tipo_arquivo_prefixo}_{ano_str}_{mun_str}.parquet"
        else:
            # Padrão: prefixo_ano_mes_municipio.parquet
            nome_busca = f"{tipo_arquivo_prefixo}_{ano_str}_{mes_str}_{mun_str}.parquet"

        padrao = os.path.join('data', nome_busca)
        
        # O glob.glob precisa do caminho absoluto ou relativo correto
        arquivos = glob.glob(padrao)

        with st.expander("Ver detalhes da busca"):
            st.write(f"Buscando por: `{nome_busca}`")
            st.write(f"Caminho completo: `{padrao}`")
            st.write(f"Arquivos encontrados no disco: {len(arquivos)}")
            if len(arquivos) > 0:
                st.write("Exemplos encontrados:", arquivos[:3])

        if not arquivos:
            st.warning(f"Nenhum arquivo de {tipo_arquivo_prefixo} encontrado para os filtros selecionados.")
            st.info("Dica: Verifique se o Ano Base e o Município conferem com o que você baixou no terminal.")
            return

        # 4. Botão de carga
        if st.button(f"Carregar {len(arquivos)} arquivos", key=f"btn_{tipo_arquivo_prefixo}"):
            with st.spinner("Consolidando..."):
                try:
                    df_lista = [pd.read_parquet(f) for f in arquivos]
                    df = pd.concat(df_lista, ignore_index=True)
                    df = df.astype(str)

                    st.success(f"Sucesso! {len(df)} registros totais.")

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