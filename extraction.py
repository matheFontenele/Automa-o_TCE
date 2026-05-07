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

        # 2. Configurar wildcards (Ajustado para ser mais flexível)
        ano_str = str(ano) if ano != "Todos" else "*"
        
        if mes == "Todos":
            mes_str = "*" 
        else:
            mes_str = str(mes).zfill(2)
        
        # O segredo está aqui: se for "Todos", usamos um padrão que aceita qualquer final
        if mun == "Todos":
            mun_pattern = "*"
        else:
            match = re.search(r'\((\d+)\)', mun)
            mun_pattern = match.group(1) if match else "*"

        # 3. Determinar o padrão de nome (Glob)
        # Ajustamos para aceitar arquivos que podem ou não ter o código do município no fim
        if "itens_notas_fiscais" in tipo_arquivo_prefixo:
            nome_busca = f"{tipo_arquivo_prefixo}_{ano_str}_{mun_pattern}.parquet"
        else:
            # Tenta encontrar o padrão completo: prefixo_ano_mes_municipio.parquet
            nome_busca = f"{tipo_arquivo_prefixo}_{ano_str}_{mes_str}_{mun_pattern}.parquet"

        padrao = os.path.join('data', nome_busca)
        arquivos = glob.glob(padrao)

        # SE NÃO ENCONTRAR COM O CÓDIGO DO MUNICIPIO, tenta uma busca mais genérica
        if not arquivos:
            nome_busca_generica = f"{tipo_arquivo_prefixo}_{ano_str}_{mes_str}*.parquet"
            padrao = os.path.join('data', nome_busca_generica)
            arquivos = glob.glob(padrao)

        with st.expander("Ver detalhes da busca", expanded=False):
            st.write(f"Buscando por: `{nome_busca}`")
            st.write(f"Arquivos encontrados: {len(arquivos)}")
            if arquivos:
                st.write("Caminhos encontrados:", arquivos[:5])

        if not arquivos:
            st.warning(f"Nenhum arquivo encontrado para `{tipo_arquivo_prefixo}` com esses filtros.")
            return

        # 4. CARREGAMENTO E VISUALIZAÇÃO DO DATAFRAME
        # Criamos um container para o DataFrame não sumir após o clique
        if st.button(f"📊 Visualizar {len(arquivos)} arquivos de {tipo_arquivo_prefixo}", key=f"btn_{tipo_arquivo_prefixo}"):
            with st.spinner("Consolidando dados..."):
                try:
                    # Carrega todos os arquivos encontrados
                    df_lista = [pd.read_parquet(f) for f in arquivos]
                    df = pd.concat(df_lista, ignore_index=True)
                    
                    st.success(f"Foram consolidados {len(df):,} registros.")
                    
                    # Formatação para exibição
                    # Limitamos a 500 linhas na visualização para não travar o navegador, mas o download é completo
                    st.dataframe(df.head(500), use_container_width=True)
                    
                    if len(df) > 500:
                        st.info("💡 Mostrando apenas as primeiras 500 linhas. Use o botão abaixo para baixar o arquivo completo.")

                    # Botão de Download
                    st.download_button(
                        label="📥 Baixar Base Consolidada (CSV)",
                        data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
                        file_name=f"consolidado_{tipo_arquivo_prefixo}_{ano}.csv",
                        mime='text/csv',
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao processar arquivos: {e}")

    # Criação dinâmica das abas usando o dicionário
    abas = st.tabs(list(DATA_MAP.keys()))
    
    for i, nome_aba in enumerate(DATA_MAP.keys()):
        with abas[i]:
            # Passa o valor real do arquivo (prefixo) para a função
            carregar_e_exibir_dados(DATA_MAP[nome_aba])