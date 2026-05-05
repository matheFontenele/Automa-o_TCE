import os
import sys
import time
import requests
import pandas as pd
import concurrent.futures
import json

# --- CONFIGURAÇÕES GERAIS ---
def carregar_municipios():
    with open('municipios.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['elements']

# Função de processamento em lote
def processar_lote(task):
    
    dataset_nome = task['dataset_nome']
    url = task['url']
    params = task['params']
    caminho_arquivo = task['caminho_arquivo']
    municipio_nome = task['municipio_nome']

    # 1. CHECKPOINT: Se já existe, não baixa novamente (Resiliência)
    if os.path.exists(caminho_arquivo):
        return f"[SKIP] {dataset_nome} - {municipio_nome} (Já existe)"

    try:
        response = requests.get(url, headers={"Accept": "application/json"}, params=params, timeout=30)
        
        if response.status_code == 200:
            dados = response.json().get("elements", [])
            
            if dados:
                for item in dados:
                    item['municipio_referencia'] = municipio_nome
                
                df = pd.DataFrame(dados)
                # Salva em Parquet com compressão snappy
                df.to_parquet(caminho_arquivo, engine='pyarrow', compression='snappy')
                return f"[OK] {dataset_nome} - {municipio_nome} ({len(dados)} reg)"
            else:
                return f"[VAZIO] {dataset_nome} - {municipio_nome}"
        else:
            return f"[ERRO {response.status_code}] {dataset_nome} - {municipio_nome}"
            
    except Exception as e:
        return f"[FALHA] {dataset_nome} - {municipio_nome}: {str(e)}"

# Função Principal
def executar_pipeline(ano, max_workers=5):
    municipios = carregar_municipios()
    os.makedirs('data', exist_ok=True)
    
    exercicio = int(f"{ano}00")
    lista_de_tarefas = []

    # Configuração dos Endpoints
    endpoints = [
        ("Notas de Empenho", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_empenhos"),
        ("Notas Fiscais", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_fiscais"),
        ("Notas de Pagamento", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_pagamentos"),
        ("Pagamento e Liquidações", "https://api-dados-abertos.tce.ce.gov.br/sim/pagamentos_liquidacoes"),
        ("Liquidações", "https://api-dados-abertos.tce.ce.gov.br/sim/pagamentos_liquidacoes"),
        ("Itens de Notas Fiscais", "https://api-dados-abertos.tce.ce.gov.br/sim/itens_notas_fiscais")
    ]

    # Prepara a fila de tarefas (Tudo que precisa ser baixado)
    for mes in range(1, 13):
        data_ref = int(f"{ano}{str(mes).zfill(2)}")
        for endpoint in endpoints:
            nome_dataset, url = endpoint
            for m in municipios:
                caminho = os.path.join('data', f"{nome_dataset.replace(' ', '_').lower()}_{ano}_{mes:02d}_{m['codigo_municipio']}.parquet")
                
                lista_de_tarefas.append({
                    'dataset_nome': nome_dataset,
                    'url': url,
                    'params': {"exercicio_orcamento": exercicio, "data_referencia_doc": data_ref, "$format": "json", "codigo_municipio": m['codigo_municipio']},
                    'caminho_arquivo': caminho,
                    'municipio_nome': m['nome_municipio']
                })

    print(f"Total de tarefas a processar: {len(lista_de_tarefas)}")
    
    # Execução Paralela (ThreadPoolExecutor)
    # max_workers controla quantas requisições ocorrem simultaneamente
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        resultados = list(executor.map(processar_lote, lista_de_tarefas))
    
    # Relatório final
    for res in resultados:
        print(res)

if __name__ == "__main__":
    ano = 2025
    if len(sys.argv) > 1:
        ano = int(sys.argv[1])
    
    print(f"Iniciando pipeline de extração paralela para {ano}...")
    executar_pipeline(ano)
    print("\nProcesso finalizado!")