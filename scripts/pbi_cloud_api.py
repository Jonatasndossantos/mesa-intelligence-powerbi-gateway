#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MESA Intelligence · Conector Power BI Cloud REST API (Opção 1)
Permite extrair dados do dataset atualizado na nuvem pelo Gateway
sem necessidade de manter o Power BI Desktop aberto.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import webbrowser

CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Azure CLI Public Client ID
SCOPE = "https://analysis.windows.net/powerbi/api/.default offline_access"
TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
DEVICE_CODE_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
POWERBI_API_BASE = "https://api.powerbi.com/v1.0/myorg"

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPTS_DIR, ".pbi_token.json")
CONFIG_FILE = os.path.join(SCRIPTS_DIR, "cloud_config.json")
RAW_OUTPUT_FILE = os.path.join(SCRIPTS_DIR, "raw_pbi_data.json")

def http_post(url, data_dict, headers=None):
    if headers is None:
        headers = {}
    data_bytes = urllib.parse.urlencode(data_dict).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_get(url, token):
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post_json(url, json_dict, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data_bytes = json.dumps(json_dict).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def login():
    """Inicia autenticação via Device Code Flow no navegador"""
    print("\n==========================================================")
    print("   Autenticação Power BI Cloud (Microsoft Entra ID)       ")
    print("==========================================================")
    
    dev_res = http_post(DEVICE_CODE_ENDPOINT, {
        "client_id": CLIENT_ID,
        "scope": SCOPE
    })
    
    user_code = dev_res["user_code"]
    verification_uri = dev_res["verification_uri"]
    device_code = dev_res["device_code"]
    interval = dev_res.get("interval", 5)
    expires_in = dev_res.get("expires_in", 900)
    
    print(f"\n👉 Código de Autorização: {user_code}")
    print(f"👉 Link para Login: {verification_uri}")
    print("\nAbrindo página de autenticação no navegador...")
    try:
        webbrowser.open(verification_uri)
    except Exception:
        pass
    
    print("\nAguardando confirmação de login no navegador (pressione Ctrl+C para cancelar)...")
    
    start_time = time.time()
    while time.time() - start_time < expires_in:
        time.sleep(interval)
        try:
            token_res = http_post(TOKEN_ENDPOINT, {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": device_code
            })
            
            token_data = {
                "access_token": token_res["access_token"],
                "refresh_token": token_res["refresh_token"],
                "expires_at": time.time() + token_res.get("expires_in", 3600) - 60
            }
            
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(token_data, f)
                
            print("\n✅ Autenticação realizada com sucesso!")
            print(f"Token salvo em segurança em: {TOKEN_FILE}")
            return token_data["access_token"]
            
        except urllib.error.HTTPError as e:
            err_data = json.loads(e.read().decode("utf-8"))
            err = err_data.get("error")
            if err == "authorization_pending":
                continue
            elif err == "slow_down":
                interval += 5
            elif err == "expired_token":
                print("❌ O tempo de autorização expirou. Tente novamente.")
                sys.exit(1)
            else:
                print(f"❌ Erro na autenticação: {err_data.get('error_description')}")
                sys.exit(1)
                
    print("❌ Tempo limite excedido.")
    sys.exit(1)

def get_valid_token():
    """Obtém um access token válido, renovando pelo refresh token se necessário"""
    if not os.path.exists(TOKEN_FILE):
        return login()
        
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token_data = json.load(f)
    except Exception:
        return login()
        
    if time.time() < token_data.get("expires_at", 0):
        return token_data["access_token"]
        
    # Renovar token
    print("Renovando token de acesso do Power BI...")
    try:
        token_res = http_post(TOKEN_ENDPOINT, {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": token_data["refresh_token"],
            "scope": SCOPE
        })
        
        token_data["access_token"] = token_res["access_token"]
        if "refresh_token" in token_res:
            token_data["refresh_token"] = token_res["refresh_token"]
        token_data["expires_at"] = time.time() + token_res.get("expires_in", 3600) - 60
        
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_data, f)
            
        return token_data["access_token"]
    except Exception as e:
        print(f"Não foi possível renovar o token ({e}). Iniciando novo login...")
        return login()

def list_workspaces_and_datasets():
    """Lista todos os workspaces e datasets disponíveis na conta Power BI Pro"""
    token = get_valid_token()
    print("\nConsultando workspaces do Power BI Pro...")
    groups = http_get(f"{POWERBI_API_BASE}/groups", token).get("value", [])
    
    print(f"\nEncontrados {len(groups)} workspaces:")
    print("=" * 60)
    for g in groups:
        gid = g["id"]
        gnome = g["name"]
        print(f"\n📂 Workspace: '{gnome}' (ID: {gid})")
        datasets = http_get(f"{POWERBI_API_BASE}/groups/{gid}/datasets", token).get("value", [])
        for d in datasets:
            did = d["id"]
            dnome = d["name"]
            is_refreshable = d.get("isRefreshable", False)
            print(f"   📊 Dataset: '{dnome}' (ID: {did}) - Atualizável: {is_refreshable}")
            
    print("\n" + "=" * 60)
    print("💡 Para configurar o extrator da nuvem, copie o Workspace ID e Dataset ID para o arquivo scripts/cloud_config.json")

def execute_dax_cloud(group_id, dataset_id, query):
    """Executa consulta DAX no dataset via REST API executeQueries"""
    token = get_valid_token()
    url = f"{POWERBI_API_BASE}/groups/{group_id}/datasets/{dataset_id}/executeQueries"
    payload = {
        "queries": [{"query": query}],
        "serializerSettings": {"includeNulls": True}
    }
    res = http_post_json(url, payload, token)
    tables = res.get("results", [{}])[0].get("tables", [{}])
    if tables:
        return tables[0].get("rows", [])
    return []

def extract_all_cloud():
    """Executa extração completa de todas as tabelas direto da nuvem"""
    if not os.path.exists(CONFIG_FILE):
        print("❌ Arquivo scripts/cloud_config.json não encontrado!")
        sys.exit(1)
        
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    group_id = cfg.get("workspace_id")
    dataset_id = cfg.get("dataset_id")
    
    if not group_id or not dataset_id:
        print("❌ Por favor configure o 'workspace_id' e 'dataset_id' no arquivo scripts/cloud_config.json")
        print("Execute: python scripts/pbi_cloud_api.py --list para listar seus IDs.")
        sys.exit(1)
        
    print(f"Iniciando extração do Power BI Service (Workspace: {group_id}, Dataset: {dataset_id})...")
    
    queries = {
        "lojas": "EVALUATE d_loja",
        "vendas": """
            EVALUATE 
            FILTER(
                SUMMARIZECOLUMNS(
                    'garcomweb gw_vendas_acumulado'[idloja],
                    'Calendario'[Ano],
                    'Calendario'[Month Short],
                    "mes", FORMAT(MIN('Calendario'[Date]), "yyyy-MM"),
                    "pedidos_validos", DISTINCTCOUNT('garcomweb gw_vendas_acumulado'[numero_pedido]),
                    "lancado", SUM('garcomweb gw_vendas_acumulado'[subtotal]),
                    "excluidos", CALCULATE(SUM('garcomweb gw_vendas_acumulado'[subtotal]), 'garcomweb gw_vendas_acumulado'[excluido] = "1"),
                    "venda_bruta", CALCULATE(SUM('garcomweb gw_vendas_acumulado'[subtotal]), 'garcomweb gw_vendas_acumulado'[excluido] = "0"),
                    "descontos", SUM('garcomweb gw_vendas_acumulado'[desconto]),
                    "venda_liquida", SUM('garcomweb gw_vendas_acumulado'[total]),
                    "servico", SUM('garcomweb gw_vendas_acumulado'[servico]),
                    "total_com_servico", SUM('garcomweb gw_vendas_acumulado'[total_com_servico])
                ),
                NOT(ISBLANK([venda_liquida])) && [venda_liquida] > 0
            )
        """,
        "produtos": """
            EVALUATE 
            FILTER(
                SUMMARIZECOLUMNS(
                    'garcomweb gw_vendas_acumulado'[idloja],
                    'Calendario'[Ano],
                    'Calendario'[Month Short],
                    'garcomweb gw_vendas_acumulado'[grupo],
                    'garcomweb gw_vendas_acumulado'[descricao_produto],
                    "mes", FORMAT(MIN('Calendario'[Date]), "yyyy-MM"),
                    "v", SUM('garcomweb gw_vendas_acumulado'[total]),
                    "qtd", SUM('garcomweb gw_vendas_acumulado'[quantidade])
                ),
                NOT(ISBLANK([v])) && [v] > 0
            )
        """,
        "grupos": """
            EVALUATE 
            FILTER(
                SUMMARIZECOLUMNS(
                    'garcomweb gw_vendas_acumulado'[idloja],
                    'Calendario'[Ano],
                    'Calendario'[Month Short],
                    'garcomweb gw_vendas_acumulado'[grupo],
                    "mes", FORMAT(MIN('Calendario'[Date]), "yyyy-MM"),
                    "v", SUM('garcomweb gw_vendas_acumulado'[total]),
                    "qtd", SUM('garcomweb gw_vendas_acumulado'[quantidade])
                ),
                NOT(ISBLANK([v])) && [v] > 0
            )
        """,
        "horas": """
            EVALUATE 
            FILTER(
                SUMMARIZECOLUMNS(
                    'garcomweb gw_vendas_acumulado'[idloja],
                    'Calendario'[Ano],
                    'Calendario'[Month Short],
                    "mes", FORMAT(MIN('Calendario'[Date]), "yyyy-MM"),
                    "dow", WEEKDAY(MIN('garcomweb gw_vendas_acumulado'[datahora_pedido]), 2) - 1,
                    "hora", HOUR(MIN('garcomweb gw_vendas_acumulado'[datahora_pedido])),
                    "v", SUM('garcomweb gw_vendas_acumulado'[total])
                ),
                NOT(ISBLANK([v])) && [v] > 0
            )
        """,
        "excl": """
            EVALUATE 
            TOPN(
                2000,
                FILTER(
                    SUMMARIZECOLUMNS(
                        'garcomweb gw_vendas_acumulado'[idloja],
                        'Calendario'[Ano],
                        'Calendario'[Month Short],
                        'garcomweb gw_vendas_acumulado'[motivo_exclusao],
                        "mes", FORMAT(MIN('Calendario'[Date]), "yyyy-MM"),
                        "n", COUNTROWS('garcomweb gw_vendas_acumulado'),
                        "v", SUM('garcomweb gw_vendas_acumulado'[subtotal])
                    ),
                    NOT(ISBLANK('garcomweb gw_vendas_acumulado'[motivo_exclusao])) && 'garcomweb gw_vendas_acumulado'[motivo_exclusao] <> ""
                ),
                [v], DESC
            )
        """,
        "dre_lanc": """
            EVALUATE 
            TOPN(
                5000,
                SELECTCOLUMNS(
                    'Financeiro',
                    "idloja", 'Financeiro'[idloja],
                    "id", 'Financeiro'[ID Pedido],
                    "forn", 'Financeiro'[Cliente/Fornecedor],
                    "v", 'Financeiro'[Valor],
                    "em", FORMAT('Financeiro'[Data competencia], "yyyy-MM-dd"),
                    "vc", FORMAT('Financeiro'[Data Prevista], "yyyy-MM-dd"),
                    "cx", FORMAT('Financeiro'[Data Pagamento/Recebimento], "yyyy-MM-dd"),
                    "p1", 'Financeiro'[Centro de Custo],
                    "p2", 'Financeiro'[setor_financeiro],
                    "p3", 'Financeiro'[Centro de Custo],
                    "p4", 'Financeiro'[Centro de Custo],
                    "g", 'Financeiro'[Centro de Custo],
                    "s", 'Financeiro'[setor_financeiro]
                )
            )
        """,
        "fech_meio": """
            EVALUATE 
            FILTER(
                SUMMARIZECOLUMNS(
                    'garcomweb gw_caixa_detalha_acumulado'[idloja],
                    'Calendario'[Ano],
                    'Calendario'[Month Short],
                    'garcomweb gw_caixa_detalha_acumulado'[descricao],
                    "mes", FORMAT(MIN('Calendario'[Date]), "yyyy-MM"),
                    "v", SUM('garcomweb gw_caixa_detalha_acumulado'[valor])
                ),
                NOT(ISBLANK([v])) && [v] > 0
            )
        """
    }
    
    extracted = {}
    for table_name, q in queries.items():
        print(f"  -> Extraindo via REST API: '{table_name}'...")
        rows = execute_dax_cloud(group_id, dataset_id, q)
        extracted[table_name] = rows
        print(f"     Carregados {len(rows)} registros.")
        
    with open(RAW_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False)
        
    print(f"\n✅ Dados da nuvem extraídos com sucesso para: {RAW_OUTPUT_FILE}")
    
    # Chama o gerador de HTML
    import gerar_html_live
    gerar_html_live.main()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_workspaces_and_datasets()
    elif len(sys.argv) > 1 and sys.argv[1] == "--login":
        login()
    elif len(sys.argv) > 1 and sys.argv[1] == "--extract":
        extract_all_cloud()
    else:
        print("Uso:")
        print("  python scripts/pbi_cloud_api.py --login    (Faz login na conta do Power BI Pro)")
        print("  python scripts/pbi_cloud_api.py --list     (Lista seus workspaces e datasets na nuvem)")
        print("  python scripts/pbi_cloud_api.py --extract  (Extrai direto da nuvem e gera o dashboard)")
