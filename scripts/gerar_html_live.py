import json
import os
import sys
from datetime import datetime

def get_idloja(r):
    val = (
        r.get("garcomweb gw_vendas_acumulado[idloja]") or 
        r.get("garcomweb gw_caixa_detalha_acumulado[idloja]") or 
        r.get("d_loja[idloja]") or 
        r.get("[idloja]") or 
        0
    )
    return int(val)

def get_loja_nome(r):
    return (
        r.get("d_loja[loja]") or 
        r.get("d_loja[Nome Loja]") or 
        r.get("d_loja[fantasia]") or 
        str(get_idloja(r))
    )

def apply_resilience(suffix):
    """Torna o JavaScript do template resiliente para qualquer quantidade de lojas (1, 2 ou 10+)."""
    suffix = suffix.replace(
        "${LNOME[IDS[0]].split(' ')[0]} parado em ${RWH}; ${LNOME[IDS[1]].split(' ')[0]} em ${RTE}",
        "${(LNOME[IDS[0]]||\"Loja\").split(\" \")[0]} parado em ${RWH}${IDS[1] ? \"; \" + (LNOME[IDS[1]]||\"Loja 2\").split(\" \")[0] + \" em \" + RTE : \"\"}"
    )
    suffix = suffix.replace(
        "PEND=D.concil.filter(r=>String(r.idloja)===IDS[1])",
        "PEND=D.concil.filter(r=>IDS[1] ? String(r.idloja)===IDS[1] : String(r.idloja)===IDS[0])"
    )
    suffix = suffix.replace(
        "B=derive(aggRange([IDS[1]],w,'venc'))",
        "B=derive(aggRange([IDS[1]||IDS[0]],w,'venc'))"
    )
    return suffix

def build_html_for_dataset(base_data, prefix, suffix, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    new_data_str = json.dumps(base_data, ensure_ascii=False)
    final_html = prefix + new_data_str + suffix
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    return len(final_html)

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    scripts_dir = os.path.join(base_dir, "scripts")
    raw_path = os.path.join(scripts_dir, "raw_pbi_data.json")
    template_path = r"c:\Users\Note\Documents\antigravity\kind-shannon\MESA Intelligence · Demonstração.html"
    output_path = os.path.join(base_dir, "MESA_Intelligence_Live.html")

    if not os.path.exists(raw_path):
        print(f"Error: Raw data file not found at {raw_path}")
        sys.exit(1)

    print(f"Loading raw DAX data from {raw_path}...")
    with open(raw_path, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)

    # 1. Lojas
    lojas = {}
    ordem_lojas = []
    for r in raw.get("lojas", []):
        lid = str(get_idloja(r))
        nome = get_loja_nome(r)
        lojas[lid] = nome
        if lid not in ordem_lojas:
            ordem_lojas.append(lid)

    # 2. Vendas
    vendas = []
    for r in raw.get("vendas", []):
        vendas.append({
            "idloja": get_idloja(r),
            "mes": r["[mes]"],
            "pedidos_validos": int(r.get("[pedidos_validos]") or 0),
            "lancado": round(float(r.get("[lancado]") or 0), 2),
            "excluidos": round(float(r.get("[excluidos]") or 0), 2),
            "venda_bruta": round(float(r.get("[venda_bruta]") or 0), 2),
            "descontos": round(float(r.get("[descontos]") or 0), 2),
            "venda_liquida": round(float(r.get("[venda_liquida]") or 0), 2),
            "servico": round(float(r.get("[servico]") or 0), 2),
            "total_com_servico": round(float(r.get("[total_com_servico]") or 0), 2)
        })

    vendas.sort(key=lambda x: (x["idloja"], x["mes"]))

    # 3. Produtos
    produtos = []
    for r in raw.get("produtos", []):
        produtos.append({
            "idloja": get_idloja(r),
            "mes": r["[mes]"],
            "grupo": r.get("garcomweb gw_vendas_acumulado[grupo]") or "OUTROS",
            "produto": r.get("garcomweb gw_vendas_acumulado[descricao_produto]") or "OUTROS",
            "v": round(float(r.get("[v]") or 0), 2),
            "qtd": round(float(r.get("[qtd]") or 0), 1)
        })

    # 4. Grupos
    grupos = []
    for r in raw.get("grupos", []):
        grupos.append({
            "idloja": get_idloja(r),
            "mes": r["[mes]"],
            "grupo": r.get("garcomweb gw_vendas_acumulado[grupo]") or "OUTROS",
            "v": round(float(r.get("[v]") or 0), 2),
            "qtd": round(float(r.get("[qtd]") or 0), 1)
        })

    # 5. Horas
    horas = []
    for r in raw.get("horas", []):
        horas.append({
            "idloja": get_idloja(r),
            "mes": r["[mes]"],
            "dow": int(r.get("[dow]") or 0),
            "hora": int(r.get("[hora]") or 0),
            "v": round(float(r.get("[v]") or 0), 2)
        })

    # 6. Exclusoes
    excl = []
    for r in raw.get("excl", []):
        n = int(r.get("[n]") or 0)
        excl.append({
            "idloja": get_idloja(r),
            "mes": r["[mes]"],
            "motivo": r.get("garcomweb gw_vendas_acumulado[motivo_exclusao]") or "Sem motivo informado",
            "cat": "Motivo Registrado",
            "n": n,
            "v": round(float(r.get("[v]") or 0), 2),
            "n_pos_fech": n,
            "n_min": n,
            "min_med": 0.0
        })

    # 7. DRE Lançamentos
    dre_lanc = []
    for r in raw.get("dre_lanc", []):
        dre_lanc.append({
            "idloja": get_idloja(r),
            "id": int(r.get("[id]") or 1),
            "forn": r.get("[forn]") or "Diversos",
            "v": round(float(r.get("[v]") or 0), 2),
            "em": r.get("[em]") or "",
            "vc": r.get("[vc]") or "",
            "cx": r.get("[cx]") or "",
            "p1": r.get("[p1]") or "OUTROS",
            "p2": r.get("[p2]") or "OUTROS",
            "p3": r.get("[p3]") or "OUTROS",
            "p4": r.get("[p4]") or "OUTROS",
            "g": r.get("[g]") or "OUTROS",
            "s": r.get("[s]") or "OUTROS",
            "rn_dup": 1,
            "qt_dup": 1,
            "fd": 0,
            "cp": 1
        })

    # 8. Fechamento por meio de pagamento
    fech_meio = []
    for r in raw.get("fech_meio", []):
        fech_meio.append({
            "idloja": get_idloja(r),
            "mes": r["[mes]"],
            "meio": r.get("garcomweb gw_caixa_detalha_acumulado[descricao]") or "OUTROS",
            "v": round(float(r.get("[v]") or 0), 2)
        })

    # Determine latest month
    all_months = sorted(list(set(v["mes"] for v in vendas)))
    latest_month = all_months[-1] if all_months else "2026-08"

    today_str = datetime.now().strftime("%Y-%m-%d")

    meta = {
        "corte": today_str,
        "gerado": today_str,
        "lojas": lojas,
        "ordem": ordem_lojas,
        "mes_detalhe": latest_month,
        "base": "DADOS REAIS GARÇOM WEB · POWER BI GATEWAY",
        "provisorio": False,
        "versao": "3.9.4-live",
        "demo": False
    }

    print(f"Reading template HTML from {template_path}...")
    with open(template_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    idx = html.find("const DATA=")
    if idx == -1:
        raise ValueError("Could not find 'const DATA=' in template HTML!")

    decoder = json.JSONDecoder()
    base_data, end_idx = decoder.raw_decode(html[idx + len("const DATA="):])

    prefix = html[:idx + len("const DATA=")]
    raw_suffix = html[idx + len("const DATA=") + end_idx:]
    suffix = apply_resilience(raw_suffix)

    # 1. Update Master dataset (todas as lojas consolidadas)
    master_data = dict(base_data)
    master_data["meta"] = meta
    master_data["vendas"] = vendas
    master_data["produtos"] = produtos
    master_data["grupos"] = grupos
    master_data["horas"] = horas
    master_data["excl"] = excl
    master_data["dre_lanc"] = dre_lanc
    master_data["fech_meio"] = fech_meio

    # Escreve MESA_Intelligence_Live.html e index.html
    sz1 = build_html_for_dataset(master_data, prefix, suffix, output_path)
    index_path = os.path.join(base_dir, "index.html")
    sz2 = build_html_for_dataset(master_data, prefix, suffix, index_path)
    print(f"SUCCESS! Master dashboard: {output_path} ({sz1 / 1024 / 1024:.2f} MB)")
    print(f"SUCCESS! GitHub Pages index: {index_path} ({sz2 / 1024 / 1024:.2f} MB)")

    # 2. Multi-tenant: Gera arquivos individuais isolados para cada loja em lojas/<idloja>.html
    lojas_dir = os.path.join(base_dir, "lojas")
    os.makedirs(lojas_dir, exist_ok=True)
    portal_links = []

    for lid, nome in lojas.items():
        lid_int = int(lid)
        loja_meta = dict(meta)
        loja_meta["lojas"] = {lid: nome}
        loja_meta["ordem"] = [lid]

        loja_data = dict(base_data)
        loja_data["meta"] = loja_meta
        loja_data["vendas"] = [r for r in vendas if r["idloja"] == lid_int]
        loja_data["produtos"] = [r for r in produtos if r["idloja"] == lid_int]
        loja_data["grupos"] = [r for r in grupos if r["idloja"] == lid_int]
        loja_data["horas"] = [r for r in horas if r["idloja"] == lid_int]
        loja_data["excl"] = [r for r in excl if r["idloja"] == lid_int]
        loja_data["dre_lanc"] = [r for r in dre_lanc if r["idloja"] == lid_int]
        loja_data["fech_meio"] = [r for r in fech_meio if r["idloja"] == lid_int]

        # Salva o arquivo individual
        loja_file = os.path.join(lojas_dir, f"{lid}.html")
        sz = build_html_for_dataset(loja_data, prefix, suffix, loja_file)
        print(f"  -> Gerado painel isolado da Loja {lid} ({nome}): {loja_file} ({sz / 1024 / 1024:.2f} MB)")
        portal_links.append({"id": lid, "nome": nome, "file": f"{lid}.html", "size_mb": round(sz / 1024 / 1024, 2)})

    # 3. Gera um portal simples de navegação em lojas/index.html
    portal_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MESA Intelligence · Painéis Isolados por Cliente</title>
    <style>
        :root {{ --bg: #0b0f19; --card: #151d30; --accent: #2563eb; --text: #f8fafc; --sub: #94a3b8; --border: #1e293b; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 40px 20px; margin: 0; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 8px; }}
        p {{ color: var(--sub); font-size: 14px; margin-bottom: 30px; line-height: 1.5; }}
        .badge {{ background: #1e293b; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; color: #38bdf8; }}
        .grid {{ display: flex; flex-direction: column; gap: 14px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: inherit; transition: all 0.2s; }}
        .card:hover {{ border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
        .card-info h3 {{ margin: 0 0 6px 0; font-size: 17px; }}
        .card-info span {{ color: var(--sub); font-size: 13px; }}
        .btn {{ background: var(--accent); color: white; padding: 9px 18px; border-radius: 8px; font-weight: 600; font-size: 13px; }}
        .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: var(--sub); }}
        .master-card {{ border: 1px solid #3b82f6; background: linear-gradient(135deg, #172554, #151d30); }}
    </style>
</head>
<body>
    <div class="container">
        <span class="badge">CONSULTORIA MESA · PORTAL MULTI-TENANT</span>
        <h1>🍽️ MESA Intelligence · Acesso por Cliente</h1>
        <p>Selecione a loja piloto para acessar o dashboard interativo exclusivo com dados auditados do Garçom Web.</p>

        <div class="grid">
            <a href="../index.html" class="card master-card">
                <div class="card-info">
                    <h3>👑 Visão Consolidada (Master Consultoria)</h3>
                    <span>Acesso com comparativo e todas as lojas ativas</span>
                </div>
                <div class="btn" style="background: #3b82f6;">Abrir Master &rarr;</div>
            </a>
"""
    for p in portal_links:
        portal_html += f"""
            <a href="{p['file']}" class="card">
                <div class="card-info">
                    <h3>🏪 {p['nome']}</h3>
                    <span>ID Loja: {p['id']} · Arquivo isolado ({p['size_mb']} MB)</span>
                </div>
                <div class="btn">Abrir Painel &rarr;</div>
            </a>
"""
    portal_html += """
        </div>
        <div class="footer">
            MESA Intelligence · Alimentado via Microsoft On-premises Data Gateway & Power BI
        </div>
    </div>
</body>
</html>
"""
    with open(os.path.join(lojas_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(portal_html)
    print(f"SUCCESS! Multi-tenant portal generated at {os.path.join(lojas_dir, 'index.html')}")

if __name__ == "__main__":
    main()
