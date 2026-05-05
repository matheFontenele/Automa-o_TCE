import os
import sys
import time
import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json

# --- CONFIGURAÇÕES GERAIS ---
def carregar_municipios():
    with open('municipios.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['elements']

# Função de Extração (Core) usando Parquet
def extrair_dados(nome_dataset, url_base, params_base, nome_arquivo_base, municipios, log_func=print):
    log_func(f"\n--- Iniciando extração: {nome_dataset} ---")
    
    os.makedirs('data', exist_ok=True)
    
    for m in municipios:
        log_func(f"[{nome_dataset}] Buscando: {m['nome_municipio']} ({m['codigo_municipio']})")
        
        params = params_base.copy()
        params["codigo_municipio"] = m['codigo_municipio']
        
        try:
            response = requests.get(url_base, headers={"Accept": "application/json"}, params=params)
            
            if response.status_code == 200:
                dados = response.json().get("elements", [])
                
                if dados:
                    for item in dados:
                        item['municipio_referencia'] = m['nome_municipio']
                    
                    # Convertendo para DataFrame
                    df = pd.DataFrame(dados)
                    
                    # Salva arquivo único por município (Ex: notas_empenho_2025_01_049.parquet)
                    # Isso evita problemas de memória e corrupção de arquivos
                    nome_arquivo_final = f"{nome_arquivo_base}_{m['codigo_municipio']}.parquet"
                    caminho_parquet = os.path.join('data', nome_arquivo_final)
                    
                    df.to_parquet(caminho_parquet, engine='pyarrow', compression='snappy')
                    
                    log_func(f" -> {len(dados)} registros salvos em {nome_arquivo_final}")
                else:
                    log_func(" -> Sem registros.")
            else:
                log_func(f" -> Erro {response.status_code}")
        except Exception as e:
            log_func(f" -> Erro de conexão no mun {m['codigo_municipio']}: {e}")
            
        time.sleep(0.3) # Respeito à API

# Função Wrapper facilitada
def executar_pipeline(ano, mes_selecionado=None, municipio_selecionado=None, log_func=print):
    municipios = carregar_municipios()
    
    if municipio_selecionado:
        municipios = [municipio_selecionado]
        log_func(f"Filtrando extração apenas para: {municipio_selecionado['nome_municipio']}")

    exercicio = int(f"{ano}00")
    
    if mes_selecionado and mes_selecionado != "Todos":
        meses_para_processar = [int(mes_selecionado)]
    else:
        meses_para_processar = range(1, 13)

    for mes in meses_para_processar:
        data_ref = int(f"{ano}{str(mes).zfill(2)}")
        log_func(f"\n==================================================")
        log_func(f"   INICIANDO EXTRAÇÃO DO MÊS {mes:02d}/{ano}")
        log_func(f"==================================================")

        # 1. Notas de Empenho
        extrair_dados("Notas de Empenho", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_empenhos", 
                      {"exercicio_orcamento": exercicio, "data_referencia_doc": data_ref, "$format": "json"}, 
                      f"notas_empenho_{ano}_{mes:02d}", municipios, log_func=log_func)

        # 2. Notas Fiscais
        extrair_dados("Notas Fiscais", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_fiscais", 
                      {"exercicio_orcamento": exercicio, "data_referencia_doc": data_ref, "$format": "json"}, 
                      f"notas_fiscais_{ano}_{mes:02d}", municipios, log_func=log_func)
        
        # 3. Notas de Pagamento
        extrair_dados("Notas de Pagamento", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_pagamentos", 
                      {"exercicio_orcamento": exercicio, "data_referencia_doc": data_ref, "$format": "json"}, 
                      f"notas_pagamentos_{ano}_{mes:02d}", municipios, log_func=log_func)
        
        # 4. Liquidações
        extrair_dados("Liquidações", "https://api-dados-abertos.tce.ce.gov.br/sim/pagamentos_liquidacoes", 
                      {"exercicio_orcamento": exercicio, "data_referencia_doc": data_ref, "$format": "json"}, 
                      f"liquidacoes_{ano}_{mes:02d}", municipios, log_func=log_func)

    # 5. Itens de Notas Fiscais (Anual)
    extrair_dados("Itens de Notas Fiscais", "https://api-dados-abertos.tce.ce.gov.br/sim/itens_notas_fiscais", 
                  {"exercicio_orcamento": exercicio, "$format": "json"}, f"itens_notas_fiscais_{ano}", municipios, log_func=log_func)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            ano_escolhido = int(sys.argv[1])
        except ValueError:
            print("Erro: O ano deve ser um número inteiro (ex: 2026)")
            sys.exit(1)
    else:
        ano_escolhido = 2025
        print(f"Nenhum ano informado. Usando padrão: {ano_escolhido}")

    print(f"\nIniciando extração total para o ano: {ano_escolhido}")
    executar_pipeline(ano_escolhido)
    print("\nProcesso finalizado com sucesso!")