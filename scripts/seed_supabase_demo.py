#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MESA Intelligence · Carga Inicial e Simulador Ao Vivo para o Supabase
=====================================================================
Permite popular o seu projeto Supabase a partir desta máquina usando os dados
reais já extraídos das lojas piloto (WORLD CAFE - 10603 e TEMPLO DO RAIMUNDAO - 15173)
e simular novas vendas em tempo real para testar o WebSocket no navegador!

Modos de uso:
  python scripts/seed_supabase_demo.py --seed           (Sobe todos os dados para o Supabase)
  python scripts/seed_supabase_demo.py --simulate-live  (Simula vendas ao vivo a cada 5s)
"""

import os
import sys
import json
import time
import random
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_ENV = os.path.join(BASE_DIR, "mesa-sync-agent", "config.env")
LOCAL_HTML = os.path.join(BASE_DIR, "MESA_Intelligence_Live.html")


def load_env(path):
    cfg = {}
    if not os.path.exists(path):
        return cfg
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def compute_md5(obj):
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def supabase_upsert(base_url, service_key, table, payload, on_conflict=None):
    endpoint = f"{base_url.rstrip('/')}/rest/v1/{table}"
    if on_conflict:
        endpoint += f"?on_conflict={urllib.parse.quote(on_conflict)}"

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Erro Supabase HTTP {e.code} em '{table}': {err_body}")


def load_data_from_live_html():
    if not os.path.exists(LOCAL_HTML):
        raise FileNotFoundError(f"Arquivo {LOCAL_HTML} não encontrado.")
    with open(LOCAL_HTML, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    idx = text.find("const DATA=")
    if idx == -1:
        raise ValueError("Bloco 'const DATA=' não encontrado no HTML.")
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(text[idx + len("const DATA="):])
    return data


def get_supabase_credentials():
    cfg = load_env(AGENT_ENV)
    url = os.environ.get("SUPABASE_URL") or cfg.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or cfg.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or "SEU-PROJETO" in url or not key or key.endswith("..."):
        print("\n============================================================")
        print(" 🔧 CONFIGURAÇÃO INICIAL DO SUPABASE")
        print("============================================================")
        url = input("👉 Cole a Project URL do Supabase (ex: https://xyz.supabase.co): ").strip()
        key = input("👉 Cole a chave SERVICE_ROLE (secret) para carga do banco: ").strip()
        anon = input("👉 Cole a chave ANON (public) para o Site Web (opcional agora): ").strip()

        # Salva em mesa-sync-agent/config.env para não precisar digitar de novo
        example_path = os.path.join(BASE_DIR, "mesa-sync-agent", "config.env.example")
        base_text = ""
        if os.path.exists(example_path):
            with open(example_path, "r", encoding="utf-8") as f:
                base_text = f.read()
        base_text = base_text.replace("https://SEU-PROJETO.supabase.co", url)
        base_text = base_text.replace("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", key)
        if anon:
            base_text += f"\nSUPABASE_ANON_KEY={anon}\n"
        with open(AGENT_ENV, "w", encoding="utf-8") as f:
            f.write(base_text)
        print(f"[OK] Credenciais salvas em {AGENT_ENV}!\n")

    return url, key


def seed_all_data():
    url, key = get_supabase_credentials()
    print("Carregando base real extraída (World Café & Templo do Raimundão)...")
    data = load_data_from_live_html()

    lojas_dict = data.get("meta", {}).get("lojas", {})
    corte = data.get("meta", {}).get("corte", datetime.now().strftime("%Y-%m-%d"))

    # 1. Sobe cadastro das lojas
    lojas_payload = []
    for lid, nome in lojas_dict.items():
        lojas_payload.append({
            "idloja": int(lid),
            "nome": nome,
            "ativo": True,
            "agent_status": "online",
            "agent_version": "1.0.0-seed",
            "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
            "corte": corte,
        })
    print(f"[1/3] Sincronizando {len(lojas_payload)} lojas em 'public.lojas'...")
    supabase_upsert(url, key, "lojas", lojas_payload, on_conflict="idloja")

    # 2. Sobe vendas_mensais
    vendas = data.get("vendas", [])
    print(f"[2/3] Sincronizando {len(vendas)} registros em 'public.vendas_mensais'...")
    supabase_upsert(url, key, "vendas_mensais", vendas, on_conflict="idloja,mes")

    # 3. Sobe todos os módulos analíticos particionados por loja em 'public.loja_modulos'
    modulos_keys = [
        k for k in data.keys()
        if k not in ("meta", "vendas") and isinstance(data[k], list)
    ]

    print(f"[3/3] Sincronizando {len(modulos_keys)} módulos analíticos por loja em 'public.loja_modulos'...")
    for lid in lojas_dict.keys():
        lid_int = int(lid)
        batch_modulos = []
        for mod in modulos_keys:
            rows = data[mod]
            # Se os itens possuem 'idloja', filtra apenas daquela loja; senão (ex: lacunas/aud), envia compartilhado
            if rows and isinstance(rows[0], dict) and "idloja" in rows[0]:
                loja_rows = [r for r in rows if int(r.get("idloja", 0)) == lid_int]
            else:
                loja_rows = rows

            batch_modulos.append({
                "idloja": lid_int,
                "modulo": mod,
                "dados": loja_rows,
                "hash_md5": compute_md5(loja_rows),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        # Envia um módulo por vez para evitar payloads gigantes em conexões lentas
        for item in batch_modulos:
            supabase_upsert(url, key, "loja_modulos", [item], on_conflict="idloja,modulo")
            print(f"   ✔️  Loja {lid} ({lojas_dict[lid]}) -> módulo '{item['modulo']}' ({len(item['dados'])} itens)")

    print("\n✅ Carga completa realizada com sucesso no Supabase!")


def simulate_live_pos():
    url, key = get_supabase_credentials()
    data = load_data_from_live_html()
    vendas = data.get("vendas", [])
    if not vendas:
        print("Nenhuma venda encontrada para simular.")
        return

    # Pega o último mês da loja 10603 (WORLD CAFE)
    vendas_10603 = [v for v in vendas if int(v["idloja"]) == 10603]
    alvo = sorted(vendas_10603, key=lambda x: x["mes"])[-1]

    print("\n============================================================")
    print(" ⚡ SIMULADOR DE PDV AO VIVO (GARÇOM WEB -> SUPABASE REALTIME)")
    print(f" 🏪 Loja Alvo: 10603 (WORLD CAFE) | Mês: {alvo['mes']}")
    print(" 👀 Abra o site no navegador e veja os números subindo sozinhos!")
    print(" (Pressione Ctrl+C para parar a simulação)")
    print("============================================================\n")

    while True:
        try:
            incremento = round(random.uniform(85.0, 420.0), 2)
            taxa_serv = round(incremento * 0.10, 2)
            alvo["pedidos_validos"] = int(alvo["pedidos_validos"]) + 1
            alvo["lancado"] = round(float(alvo["lancado"]) + incremento, 2)
            alvo["venda_bruta"] = round(float(alvo["venda_bruta"]) + incremento, 2)
            alvo["venda_liquida"] = round(float(alvo["venda_liquida"]) + incremento, 2)
            alvo["servico"] = round(float(alvo["servico"]) + taxa_serv, 2)
            alvo["total_com_servico"] = round(float(alvo["total_com_servico"]) + incremento + taxa_serv, 2)

            supabase_upsert(url, key, "vendas_mensais", [alvo], on_conflict="idloja,mes")
            agora = datetime.now().strftime("%H:%M:%S")
            print(
                f"[{agora}] 🔔 Nova comanda fechada (+R$ {incremento:.2f}) -> "
                f"Venda Líquida ({alvo['mes']}): R$ {alvo['venda_liquida']:,.2f} | "
                f"Pedidos: {alvo['pedidos_validos']}"
            )
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nSimulação encerrada.")
            break
        except Exception as e:
            print(f"Erro na simulação: {e}")
            time.sleep(5)


if __name__ == "__main__":
    if "--simulate-live" in sys.argv:
        simulate_live_pos()
    else:
        seed_all_data()
