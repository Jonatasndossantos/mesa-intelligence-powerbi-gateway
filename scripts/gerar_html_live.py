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

    # Update with live data
    base_data["meta"] = meta
    base_data["vendas"] = vendas
    base_data["produtos"] = produtos
    base_data["grupos"] = grupos
    base_data["horas"] = horas
    base_data["excl"] = excl
    base_data["dre_lanc"] = dre_lanc
    base_data["fech_meio"] = fech_meio

    print("Injected live tables:")
    print(f"  - lojas: {len(lojas)} ({list(lojas.values())})")
    print(f"  - vendas: {len(vendas)} rows")
    print(f"  - produtos: {len(produtos)} rows")
    print(f"  - grupos: {len(grupos)} rows")
    print(f"  - horas: {len(horas)} rows")
    print(f"  - excl: {len(excl)} rows")
    print(f"  - dre_lanc: {len(dre_lanc)} rows")
    print(f"  - fech_meio: {len(fech_meio)} rows")

    # Serialize
    new_data_str = json.dumps(base_data, ensure_ascii=False)

    prefix = html[:idx + len("const DATA=")]
    suffix = html[idx + len("const DATA=") + end_idx:]
    final_html = prefix + new_data_str + suffix

    print(f"Writing final HTML to: {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"SUCCESS! File size: {len(final_html) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
