#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MESA Intelligence · MESA Sync Agent (Conector Direto Garçom Web -> Supabase)
=============================================================================
Deve ser executado na máquina onde o banco de dados do Garçom Web (MySQL/ODBC)
está instalado. Realiza leitura somente-leitura (SELECT) em tempo real e envia
as atualizações (Outbound Push via HTTPS) para o Supabase.
"""

import os
import sys
import time
import json
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

AGENT_VERSION = "1.0.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.env")


def load_env(path):
    """Carrega variáveis do arquivo config.env sem depender de bibliotecas externas."""
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


class SupabaseClient:
    """Cliente REST nativo para o Supabase usando apenas bibliotecas padrão do Python."""

    def __init__(self, url, service_key):
        self.base_url = url.rstrip("/")
        self.service_key = service_key

    def upsert(self, table, payload, on_conflict=None):
        endpoint = f"{self.base_url}/rest/v1/{table}"
        if on_conflict:
            endpoint += f"?on_conflict={urllib.parse.quote(on_conflict)}"

        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Erro Supabase HTTP {e.code} em '{table}': {err_body}")


def connect_garcomweb(cfg):
    """Abre conexão somente-leitura com o banco local do Garçom Web (MySQL ou ODBC)."""
    modo = cfg.get("CONEXAO_MODO", "MYSQL").upper()

    if modo == "ODBC":
        import pyodbc
        dsn = cfg.get("ODBC_DSN", "GarcomWeb")
        user = cfg.get("ODBC_USER", "")
        pwd = cfg.get("ODBC_PASSWORD", "")
        conn_str = f"DSN={dsn};"
        if user:
            conn_str += f"UID={user};PWD={pwd};"
        return pyodbc.connect(conn_str), "ODBC"
    else:
        import pymysql
        import pymysql.cursors
        conn = pymysql.connect(
            host=cfg.get("MYSQL_HOST", "127.0.0.1"),
            port=int(cfg.get("MYSQL_PORT", "3306")),
            user=cfg.get("MYSQL_USER", "root"),
            password=cfg.get("MYSQL_PASSWORD", ""),
            database=cfg.get("MYSQL_DATABASE", "garcomweb"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=30,
        )
        return conn, "MYSQL"


def query_dicts(conn, modo, sql):
    """Executa SELECT e retorna lista de dicionários independente do driver."""
    cur = conn.cursor()
    cur.execute(sql)
    if modo == "MYSQL":
        rows = cur.fetchall()
        cur.close()
        return list(rows)
    else:
        cols = [col[0] for col in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        return rows


def detect_table_name(conn, modo, preferred, candidates):
    """Descobre automaticamente o nome exato da tabela no MySQL do Garçom Web."""
    try:
        rows = query_dicts(conn, modo, "SHOW TABLES")
        existing = [list(r.values())[0] for r in rows]
        existing_lower = {t.lower(): t for t in existing}
        if preferred.lower() in existing_lower:
            return existing_lower[preferred.lower()]
        for c in candidates:
            if c.lower() in existing_lower:
                return existing_lower[c.lower()]
    except Exception:
        pass
    return preferred


def extract_from_garcomweb(conn, modo, cfg):
    """
    Executa as agregações SQL diretamente no MySQL local do Garçom Web,
    retornando os dados já estruturados e leves para envio ao Supabase.
    """
    idloja = int(cfg.get("ID_LOJA", 10603))
    tb_vendas = detect_table_name(
        conn, modo,
        cfg.get("TABELA_VENDAS", "gw_vendas_acumulado"),
        ["gw_vendas_acumulado", "vendas_acumulado", "gw_vendas", "vendas"]
    )
    tb_caixa = detect_table_name(
        conn, modo,
        cfg.get("TABELA_CAIXA", "gw_caixa_detalha_acumulado"),
        ["gw_caixa_detalha_acumulado", "caixa_detalha_acumulado", "gw_caixa_detalha", "caixa_detalha"]
    )

    # 1. Vendas Mensais
    sql_vendas = f"""
        SELECT
            {idloja} AS idloja,
            DATE_FORMAT(datahora_pedido, '%Y-%m') AS mes,
            COUNT(DISTINCT numero_pedido) AS pedidos_validos,
            ROUND(SUM(COALESCE(subtotal, 0)), 2) AS lancado,
            ROUND(SUM(CASE WHEN CAST(excluido AS CHAR) = '1' THEN COALESCE(subtotal, 0) ELSE 0 END), 2) AS excluidos,
            ROUND(SUM(CASE WHEN CAST(excluido AS CHAR) = '0' OR excluido IS NULL THEN COALESCE(subtotal, 0) ELSE 0 END), 2) AS venda_bruta,
            ROUND(SUM(COALESCE(desconto, 0)), 2) AS descontos,
            ROUND(SUM(COALESCE(total, 0)), 2) AS venda_liquida,
            ROUND(SUM(COALESCE(servico, 0)), 2) AS servico,
            ROUND(SUM(COALESCE(total_com_servico, 0)), 2) AS total_com_servico
        FROM `{tb_vendas}`
        WHERE datahora_pedido IS NOT NULL
        GROUP BY DATE_FORMAT(datahora_pedido, '%Y-%m')
        HAVING venda_liquida > 0
        ORDER BY mes ASC
    """
    vendas_raw = query_dicts(conn, modo, sql_vendas)
    vendas = []
    for r in vendas_raw:
        vendas.append({
            "idloja": idloja,
            "mes": str(r["mes"]),
            "pedidos_validos": int(r["pedidos_validos"] or 0),
            "lancado": float(r["lancado"] or 0),
            "excluidos": float(r["excluidos"] or 0),
            "venda_bruta": float(r["venda_bruta"] or 0),
            "descontos": float(r["descontos"] or 0),
            "venda_liquida": float(r["venda_liquida"] or 0),
            "servico": float(r["servico"] or 0),
            "total_com_servico": float(r["total_com_servico"] or 0),
        })

    # 2. Grupos Mensais
    sql_grupos = f"""
        SELECT
            DATE_FORMAT(datahora_pedido, '%Y-%m') AS mes,
            COALESCE(NULLIF(TRIM(grupo), ''), 'OUTROS') AS grupo,
            ROUND(SUM(COALESCE(total, 0)), 2) AS v,
            ROUND(SUM(COALESCE(quantidade, 0)), 1) AS qtd
        FROM `{tb_vendas}`
        WHERE datahora_pedido IS NOT NULL AND COALESCE(total, 0) > 0
        GROUP BY DATE_FORMAT(datahora_pedido, '%Y-%m'), COALESCE(NULLIF(TRIM(grupo), ''), 'OUTROS')
    """
    grupos = [
        {
            "idloja": idloja,
            "mes": str(r["mes"]),
            "grupo": str(r["grupo"]),
            "v": float(r["v"] or 0),
            "qtd": float(r["qtd"] or 0),
        }
        for r in query_dicts(conn, modo, sql_grupos)
    ]

    # 3. Produtos Mensais
    sql_produtos = f"""
        SELECT
            DATE_FORMAT(datahora_pedido, '%Y-%m') AS mes,
            COALESCE(NULLIF(TRIM(grupo), ''), 'OUTROS') AS grupo,
            COALESCE(NULLIF(TRIM(descricao_produto), ''), 'OUTROS') AS produto,
            ROUND(SUM(COALESCE(total, 0)), 2) AS v,
            ROUND(SUM(COALESCE(quantidade, 0)), 1) AS qtd
        FROM `{tb_vendas}`
        WHERE datahora_pedido IS NOT NULL AND COALESCE(total, 0) > 0
        GROUP BY
            DATE_FORMAT(datahora_pedido, '%Y-%m'),
            COALESCE(NULLIF(TRIM(grupo), ''), 'OUTROS'),
            COALESCE(NULLIF(TRIM(descricao_produto), ''), 'OUTROS')
    """
    produtos = [
        {
            "idloja": idloja,
            "mes": str(r["mes"]),
            "grupo": str(r["grupo"]),
            "produto": str(r["produto"]),
            "v": float(r["v"] or 0),
            "qtd": float(r["qtd"] or 0),
        }
        for r in query_dicts(conn, modo, sql_produtos)
    ]

    # 4. Horas / Dia da Semana
    sql_horas = f"""
        SELECT
            DATE_FORMAT(datahora_pedido, '%Y-%m') AS mes,
            WEEKDAY(datahora_pedido) AS dow,
            HOUR(datahora_pedido) AS hora,
            ROUND(SUM(COALESCE(total, 0)), 2) AS v
        FROM `{tb_vendas}`
        WHERE datahora_pedido IS NOT NULL AND COALESCE(total, 0) > 0
        GROUP BY DATE_FORMAT(datahora_pedido, '%Y-%m'), WEEKDAY(datahora_pedido), HOUR(datahora_pedido)
    """
    horas = [
        {
            "idloja": idloja,
            "mes": str(r["mes"]),
            "dow": int(r["dow"] or 0),
            "hora": int(r["hora"] or 0),
            "v": float(r["v"] or 0),
        }
        for r in query_dicts(conn, modo, sql_horas)
    ]

    # 5. Exclusões e Motivos de Cancelamento
    sql_excl = f"""
        SELECT
            DATE_FORMAT(datahora_pedido, '%Y-%m') AS mes,
            TRIM(motivo_exclusao) AS motivo,
            COUNT(*) AS n,
            ROUND(SUM(COALESCE(subtotal, 0)), 2) AS v
        FROM `{tb_vendas}`
        WHERE motivo_exclusao IS NOT NULL AND TRIM(motivo_exclusao) <> ''
        GROUP BY DATE_FORMAT(datahora_pedido, '%Y-%m'), TRIM(motivo_exclusao)
        ORDER BY v DESC
        LIMIT 2000
    """
    excl = [
        {
            "idloja": idloja,
            "mes": str(r["mes"]),
            "motivo": str(r["motivo"]),
            "cat": "Motivo Registrado",
            "n": int(r["n"] or 0),
            "v": float(r["v"] or 0),
            "n_pos_fech": int(r["n"] or 0),
            "n_min": int(r["n"] or 0),
            "min_med": 0.0,
        }
        for r in query_dicts(conn, modo, sql_excl)
    ]

    # 6. Meios de Pagamento (Caixa)
    fech_meio = []
    try:
        sql_caixa = f"""
            SELECT
                DATE_FORMAT(data, '%Y-%m') AS mes,
                COALESCE(NULLIF(TRIM(descricao), ''), 'OUTROS') AS meio,
                ROUND(SUM(COALESCE(valor, 0)), 2) AS v
            FROM `{tb_caixa}`
            WHERE COALESCE(valor, 0) > 0
            GROUP BY DATE_FORMAT(data, '%Y-%m'), COALESCE(NULLIF(TRIM(descricao), ''), 'OUTROS')
        """
        fech_meio = [
            {
                "idloja": idloja,
                "mes": str(r["mes"]),
                "meio": str(r["meio"]),
                "v": float(r["v"] or 0),
            }
            for r in query_dicts(conn, modo, sql_caixa)
        ]
    except Exception as e:
        print(f"  [Aviso] Tabela de caixa ({tb_caixa}) ignorada ou com coluna de data diferente: {e}")

    return {
        "vendas": vendas,
        "modulos": {
            "grupos": grupos,
            "produtos": produtos,
            "horas": horas,
            "excl": excl,
            "fech_meio": fech_meio,
        },
    }


def run_test_mode(cfg):
    print("\n============================================================")
    print("   DIAGNÓSTICO DE CONEXÃO · MESA SYNC AGENT (GARÇOM WEB)    ")
    print("============================================================")
    try:
        conn, modo = connect_garcomweb(cfg)
        print(f"[OK] Conectado ao banco local do Garçom Web via {modo}!")
        tables = query_dicts(conn, modo, "SHOW TABLES")
        print(f"[OK] Encontradas {len(tables)} tabelas no banco:")
        for t in tables[:25]:
            print(f"     - {list(t.values())[0]}")
        conn.close()
    except Exception as e:
        print(f"[ERRO] Falha ao conectar no Garçom Web local: {e}")
        sys.exit(1)

    supa_url = cfg.get("SUPABASE_URL", "")
    supa_key = cfg.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supa_url or "SEU-PROJETO" in supa_url:
        print("[AVISO] SUPABASE_URL ainda não configurada no config.env.")
    else:
        try:
            supa = SupabaseClient(supa_url, supa_key)
            idloja = int(cfg.get("ID_LOJA", 10603))
            nome = cfg.get("NOME_LOJA", f"LOJA {idloja}")
            supa.upsert("lojas", [{
                "idloja": idloja,
                "nome": nome,
                "ativo": True,
                "agent_status": "online",
                "agent_version": AGENT_VERSION,
                "last_heartbeat_at": datetime.now(timezone.utc).isoformat()
            }], on_conflict="idloja")
            print(f"[OK] Conectado ao Supabase ({supa_url}) e heartbeat da loja {idloja} enviado!")
        except Exception as e:
            print(f"[ERRO] Falha ao comunicar com Supabase: {e}")
            sys.exit(1)


def run_sync_loop(cfg, once=False):
    idloja = int(cfg.get("ID_LOJA", 10603))
    nome_loja = cfg.get("NOME_LOJA", f"LOJA {idloja}")
    interval = int(cfg.get("SYNC_INTERVAL_SECONDS", 10))
    supa = SupabaseClient(cfg["SUPABASE_URL"], cfg["SUPABASE_SERVICE_ROLE_KEY"])

    hashes_memoria = {}
    print("\n============================================================")
    print(f" ⚡ MESA SYNC AGENT ATIVO · LOJA {idloja} ({nome_loja})")
    print(f" 📡 Transmitindo ao vivo para: {cfg['SUPABASE_URL']}")
    print(f" ⏱️  Intervalo de varredura: a cada {interval} segundos")
    print("============================================================\n")

    while True:
        ciclo_inicio = datetime.now().strftime("%H:%M:%S")
        try:
            conn, modo = connect_garcomweb(cfg)
            payload = extract_from_garcomweb(conn, modo, cfg)
            conn.close()

            alteracoes = 0

            # 1. Verifica se vendas_mensais mudou
            vendas = payload["vendas"]
            h_vendas = compute_md5(vendas)
            if hashes_memoria.get("vendas_mensais") != h_vendas:
                if vendas:
                    supa.upsert("vendas_mensais", vendas, on_conflict="idloja,mes")
                hashes_memoria["vendas_mensais"] = h_vendas
                alteracoes += 1
                print(f"[{ciclo_inicio}] 🚀 [AO VIVO] Vendas mensais sincronizadas ({len(vendas)} meses)")

            # 2. Verifica cada módulo analítico
            for mod_name, mod_rows in payload["modulos"].items():
                if not mod_rows:
                    continue
                h_mod = compute_md5(mod_rows)
                if hashes_memoria.get(mod_name) != h_mod:
                    supa.upsert("loja_modulos", [{
                        "idloja": idloja,
                        "modulo": mod_name,
                        "dados": mod_rows,
                        "hash_md5": h_mod,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }], on_conflict="idloja,modulo")
                    hashes_memoria[mod_name] = h_mod
                    alteracoes += 1
                    print(f"[{ciclo_inicio}] 🚀 [AO VIVO] Módulo '{mod_name}' atualizado ({len(mod_rows)} registros)")

            # 3. Envia Heartbeat da loja
            supa.upsert("lojas", [{
                "idloja": idloja,
                "nome": nome_loja,
                "ativo": True,
                "agent_status": "online",
                "agent_version": AGENT_VERSION,
                "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
                "corte": datetime.now().strftime("%Y-%m-%d")
            }], on_conflict="idloja")

            if alteracoes == 0:
                print(f"[{ciclo_inicio}] ✔️  Sem novas alterações no Garçom Web (Heartbeat OK)")

        except KeyboardInterrupt:
            print("\nEncerrando MESA Sync Agent a pedido do usuário...")
            break
        except Exception as e:
            print(f"[{ciclo_inicio}] ❌ Erro no ciclo de sincronização: {e}")

        if once:
            break
        time.sleep(interval)


if __name__ == "__main__":
    if not os.path.exists(CONFIG_PATH):
        example_path = os.path.join(BASE_DIR, "config.env.example")
        if os.path.exists(example_path):
            import shutil
            shutil.copyfile(example_path, CONFIG_PATH)
            print(f"⚠️  Arquivo 'config.env' criado a partir do modelo em:\n   {CONFIG_PATH}")
            print("👉 Edite o arquivo 'config.env' com a senha do MySQL e a chave do Supabase antes de iniciar.")
            sys.exit(1)

    cfg = load_env(CONFIG_PATH)
    if "--test" in sys.argv:
        run_test_mode(cfg)
    elif "--once" in sys.argv:
        run_sync_loop(cfg, once=True)
    else:
        run_sync_loop(cfg, once=False)
