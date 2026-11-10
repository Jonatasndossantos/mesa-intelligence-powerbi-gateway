#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MESA Intelligence · Construtor do Web App Seguro + Login + Supabase Realtime
=============================================================================
Transforma o template estático em uma Aplicação Web Dinâmica (~95 KB) com:
  1. Zero dados sensíveis embutidos no código-fonte HTML.
  2. Tela de Login nativa conectada ao Supabase Auth (E-mail e Senha).
  3. Isolamento Multi-Tenant garantido por Row Level Security (RLS) no PostgreSQL.
  4. Atualização Ao Vivo via WebSockets (Supabase Realtime) sem recarregar a página.
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_HTML = os.path.join(BASE_DIR, "MESA_Intelligence_Live.html")
OUTPUT_APP = os.path.join(BASE_DIR, "app_ao_vivo.html")
OUTPUT_INDEX = os.path.join(BASE_DIR, "index.html")
AGENT_ENV = os.path.join(BASE_DIR, "mesa-sync-agent", "config.env")


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


AUTH_AND_REALTIME_CSS = """
<style id="mesa-live-auth-styles">
  #mesaAuthOverlay {
    position: fixed;
    inset: 0;
    z-index: 99999;
    background: radial-gradient(circle at 50% 20%, #172554 0%, #090d16 70%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #f8fafc;
  }
  #mesaAuthOverlay.hidden {
    display: none !important;
  }
  .mesa-auth-card {
    width: 100%;
    max-width: 430px;
    background: rgba(15, 23, 42, 0.92);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 16px;
    padding: 32px 28px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(12px);
  }
  .mesa-auth-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin-bottom: 14px;
  }
  .mesa-auth-card h1 {
    margin: 0 0 6px 0;
    font-size: 22px;
    font-weight: 700;
    color: #f8fafc;
  }
  .mesa-auth-card p.sub {
    margin: 0 0 22px 0;
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.5;
  }
  .mesa-field {
    margin-bottom: 14px;
  }
  .mesa-field label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: #cbd5e1;
    margin-bottom: 6px;
  }
  .mesa-field input {
    width: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid #334155;
    background: #090d16;
    color: #f8fafc;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .mesa-field input:focus {
    border-color: #38bdf8;
  }
  .mesa-btn-primary {
    width: 100%;
    padding: 11px 16px;
    border: none;
    border-radius: 8px;
    background: linear-gradient(135deg, #2563eb, #0284c7);
    color: #ffffff;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    margin-top: 6px;
    transition: opacity 0.2s, transform 0.1s;
  }
  .mesa-btn-primary:hover {
    opacity: 0.95;
  }
  .mesa-btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .mesa-auth-msg {
    margin-top: 12px;
    padding: 10px 12px;
    border-radius: 8px;
    font-size: 12.5px;
    line-height: 1.4;
    display: none;
  }
  .mesa-auth-msg.err {
    display: block;
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: #fca5a5;
  }
  .mesa-auth-msg.ok {
    display: block;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #6ee7b7;
  }
  .mesa-cfg-toggle {
    margin-top: 18px;
    padding-top: 14px;
    border-top: 1px solid #1e293b;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: #64748b;
  }
  .mesa-cfg-toggle button {
    background: none;
    border: none;
    color: #38bdf8;
    cursor: pointer;
    font-size: 12px;
    padding: 0;
    text-decoration: underline;
  }
  #mesaCfgBox {
    display: none;
    margin-top: 12px;
    padding: 12px;
    background: rgba(2, 6, 23, 0.65);
    border: 1px solid #1e293b;
    border-radius: 8px;
  }
  #mesaCfgBox.open {
    display: block;
  }
  .live-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #10b981;
    font-size: 11px;
    font-weight: 700;
  }
  .live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: mesaPulse 1.8s infinite;
  }
  @keyframes mesaPulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.35); opacity: 0.55; }
  }
  #mesaRealtimeToast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 99990;
    background: #0f172a;
    border: 1px solid #10b981;
    color: #f8fafc;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 12.5px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    display: none;
    align-items: center;
    gap: 10px;
  }
</style>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
"""


AUTH_OVERLAY_HTML = """
<div id="mesaAuthOverlay">
  <div class="mesa-auth-card">
    <div class="mesa-auth-badge">
      <span class="live-dot"></span> CONECTIVIDADE AO VIVO · SUPABASE + GARÇOM WEB
    </div>
    <h1>🍽️ MESA Intelligence</h1>
    <p class="sub">Acesse com suas credenciais para carregar os dados em tempo real das lojas autorizadas para o seu perfil.</p>

    <form id="mesaLoginForm">
      <div class="mesa-field">
        <label for="mesaEmail">E-mail corporativo</label>
        <input type="email" id="mesaEmail" placeholder="seuemail@restaurante.com.br" required autocomplete="username" />
      </div>
      <div class="mesa-field">
        <label for="mesaPassword">Senha</label>
        <input type="password" id="mesaPassword" placeholder="••••••••" required autocomplete="current-password" />
      </div>
      <button type="submit" class="mesa-btn-primary" id="mesaLoginBtn">Entrar e Conectar Ao Vivo &rarr;</button>
    </form>

    <div id="mesaAuthMsg" class="mesa-auth-msg"></div>

    <div class="mesa-cfg-toggle">
      <span id="mesaConnStatusLbl">Servidor Supabase</span>
      <button type="button" id="mesaToggleCfgBtn">⚙️ Configurar URL / Key</button>
    </div>

    <div id="mesaCfgBox">
      <div class="mesa-field">
        <label for="mesaSupaUrl">Supabase Project URL</label>
        <input type="url" id="mesaSupaUrl" placeholder="https://xyzcompany.supabase.co" />
      </div>
      <div class="mesa-field">
        <label for="mesaSupaAnon">Supabase Anon Public Key</label>
        <input type="text" id="mesaSupaAnon" placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." />
      </div>
      <button type="button" class="mesa-btn-primary" id="mesaSaveCfgBtn" style="background:#334155;font-size:12.5px;padding:8px 12px;">Salvar Conexão no Navegador</button>
    </div>
  </div>
</div>

<div id="mesaRealtimeToast">
  <span class="live-dot"></span>
  <span id="mesaRealtimeToastTxt">Atualização em tempo real recebida!</span>
</div>
"""


def build_webapp():
    if not os.path.exists(SOURCE_HTML):
        print(f"Erro: {SOURCE_HTML} não encontrado.")
        sys.exit(1)

    with open(SOURCE_HTML, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    cfg = load_env(AGENT_ENV)
    default_supa_url = cfg.get("SUPABASE_URL", "")
    if "SEU-PROJETO" in default_supa_url:
        default_supa_url = ""
    default_supa_anon = cfg.get("SUPABASE_ANON_KEY", "")

    # 1. Injeta CSS + SDK do Supabase antes de </head>
    html = html.replace("</head>", AUTH_AND_REALTIME_CSS + "\n</head>", 1)

    # 2. Adiciona botão Sair e indicador Ao Vivo no topo, ao lado de Tema
    html = html.replace(
        '<button class="btn" id="bTema" type="button">Tema</button>',
        '<span class="live-pill" id="mesaLiveBadge" style="display:none"><span class="live-dot"></span> <span id="mesaLiveTxt">AO VIVO</span></span>'
        '<button class="btn" id="bTema" type="button">Tema</button>'
        '<button class="btn" id="bLogout" type="button" style="display:none;color:#f87171;border-color:rgba(248,113,113,0.3)">Sair</button>',
        1
    )

    # 3. Localiza e remove o payload gigante `const DATA={...};`
    idx_data = html.find("const DATA=")
    if idx_data == -1:
        raise ValueError("Não foi possível localizar 'const DATA=' no template.")

    decoder = json.JSONDecoder()
    _, end_idx = decoder.raw_decode(html[idx_data + len("const DATA="):])

    prefix = html[:idx_data]
    after_data = html[idx_data + len("const DATA=") + end_idx:]

    # 4. Modifica o bloco (function(){ 'use strict'; ... })() para:
    #    - ser inicializado sob demanda via window.__bootMesaEngine()
    #    - expor window.__refreshMesaRealtime() para atualizar índices e tela em 2ms via WebSocket!
    after_data = after_data.replace(
        "(function(){\n'use strict';\nconst D=DATA,",
        "window.__bootMesaEngine = function(){\n'use strict';\nconst DATA=window.DATA;\nconst D=DATA,",
        1
    )

    realtime_hook_js = """
window.__refreshMesaRealtime = function() {
  for (const k in vIdx) delete vIdx[k];
  for (const k in cIdx) delete cIdx[k];
  for (const k in covIdx) delete covIdx[k];
  for (const k in taxIdx) delete taxIdx[k];
  for (const k in dIdx) delete dIdx[k];
  for (const k in rIdx) delete rIdx[k];
  for (const k in dcIdx) delete dcIdx[k];
  D.vendas.forEach(r=>vIdx[r.idloja+'|'+r.mes]=r);
  D.concil.forEach(r=>cIdx[r.idloja+'|'+r.mes]=r);
  D.cobertura.forEach(r=>covIdx[r.idloja+'|'+r.mes]=r);
  D.taxas.forEach(r=>{const k=r.idloja+'|'+r.mes;(taxIdx[k]=taxIdx[k]||{taxas:0,bruto:0});taxIdx[k].taxas+=r.taxas;taxIdx[k].bruto+=r.bruto});
  D.desp.forEach(r=>{const k=r.idloja+'|'+r.base+'|'+r.mes;(dIdx[k]=dIdx[k]||[]).push(r)});
  D.receb.forEach(r=>{const k=r.idloja+'|'+r.mes;(rIdx[k]=rIdx[k]||{})[r.tipo]=(rIdx[k][r.tipo]||0)+r.valor});
  D.desc_classe.forEach(r=>{const k=r.idloja+'|'+r.mes;(dcIdx[k]=dcIdx[k]||{})[r.classe]=r.desconto});
  rerender();
};
fillSelects();render();
};
"""
    after_data = after_data.replace("fillSelects();render();\n})();", realtime_hook_js, 1)

    # Atualiza o texto do selo de origem dos dados para mostrar conexão ao vivo
    after_data = after_data.replace(
        "document.getElementById('srcTag').textContent='DEMONSTRAÇÃO · dados anonimizados e em escala · PROVISÓRIO · corte '+D.meta.corte.split('-').reverse().join('/');",
        "document.getElementById('srcTag').textContent='CONECTADO AO VIVO · SUPABASE RLS + GARÇOM WEB · corte '+D.meta.corte.split('-').reverse().join('/');",
        1
    )

    # 5. Constrói o controlador de Autenticação + Hidratação + Supabase Realtime
    supabase_controller_js = f"""window.DATA = null;
window.MESA_DEFAULT_SUPABASE = {{
  url: {json.dumps(default_supa_url)},
  anonKey: {json.dumps(default_supa_anon)}
}};

(function() {{
  'use strict';
  const ALL_LIST_KEYS = [
    'vendas','receb','concil','desp','taxas','cobertura','desc_classe',
    'grupos','produtos','horas','aging','dup_top','indic','contas','saldos',
    'dfc','compromissos','aud','dre_lanc','dre_conc','dre_semdata','vprod',
    'excl','excl_gerente','atend','custocob','excl_top','sobrep','fech',
    'fech_meio','fech_cmp','caixa_ev','troco_extra','repique_ev','lacunas'
  ];

  let supaClient = null;
  let realtimeChannel = null;
  let engineBooted = false;

  function getSupaCredentials() {{
    const url = localStorage.getItem('mesa_supa_url') || window.MESA_DEFAULT_SUPABASE.url || '';
    const anonKey = localStorage.getItem('mesa_supa_anon') || window.MESA_DEFAULT_SUPABASE.anonKey || '';
    return {{ url: url.trim(), anonKey: anonKey.trim() }};
  }}

  function showMsg(text, type) {{
    const el = document.getElementById('mesaAuthMsg');
    if (!el) return;
    el.textContent = text;
    el.className = 'mesa-auth-msg ' + (type || 'err');
  }}

  function showToast(text) {{
    const t = document.getElementById('mesaRealtimeToast');
    const txt = document.getElementById('mesaRealtimeToastTxt');
    if (!t || !txt) return;
    txt.textContent = text;
    t.style.display = 'inline-flex';
    clearTimeout(window.__mesaToastTimer);
    window.__mesaToastTimer = setTimeout(() => {{ t.style.display = 'none'; }}, 4000);
  }}

  function initSupabaseClient() {{
    const creds = getSupaCredentials();
    const urlInput = document.getElementById('mesaSupaUrl');
    const anonInput = document.getElementById('mesaSupaAnon');
    const statusLbl = document.getElementById('mesaConnStatusLbl');

    if (urlInput) urlInput.value = creds.url;
    if (anonInput) anonInput.value = creds.anonKey;

    if (!creds.url || !creds.anonKey) {{
      if (statusLbl) statusLbl.textContent = '⚠️ Configure URL e Key do Supabase';
      const box = document.getElementById('mesaCfgBox');
      if (box) box.classList.add('open');
      return null;
    }}
    if (statusLbl) statusLbl.textContent = '🔗 ' + creds.url.replace('https://', '');
    try {{
      supaClient = window.supabase.createClient(creds.url, creds.anonKey);
      return supaClient;
    }} catch (err) {{
      showMsg('Erro ao inicializar cliente Supabase: ' + err.message, 'err');
      return null;
    }}
  }}

  async function fetchAndHydrateDashboard(user) {{
    const btn = document.getElementById('mesaLoginBtn');
    if (btn) {{ btn.disabled = true; btn.textContent = 'Carregando dados criptografados (RLS)...'; }}

    try {{
      const [lojasRes, vendasRes, modulosRes] = await Promise.all([
        supaClient.from('lojas').select('*').eq('ativo', true).order('idloja'),
        supaClient.from('vendas_mensais').select('*').order('mes'),
        supaClient.from('loja_modulos').select('idloja, modulo, dados')
      ]);

      if (lojasRes.error) throw lojasRes.error;
      if (vendasRes.error) throw vendasRes.error;
      if (modulosRes.error) throw modulosRes.error;

      const lojasRows = lojasRes.data || [];
      if (lojasRows.length === 0) {{
        throw new Error(
          'Seu usuário (' + user.email + ') está autenticado, mas ainda não possui lojas vinculadas em public.user_lojas (ou o banco está vazio). Rode o comando SELECT public.vincular_usuario_por_email() no SQL Editor do Supabase.'
        );
      }}

      const lojasMap = {{}};
      const ordem = [];
      let corte = new Date().toISOString().slice(0, 10);

      lojasRows.forEach(r => {{
        const lid = String(r.idloja);
        lojasMap[lid] = r.nome;
        ordem.push(lid);
        if (r.corte) corte = String(r.corte).slice(0, 10);
      }});

      const vendas = (vendasRes.data || []).map(r => ({{
        idloja: Number(r.idloja),
        mes: String(r.mes),
        pedidos_validos: Number(r.pedidos_validos || 0),
        lancado: Number(r.lancado || 0),
        excluidos: Number(r.excluidos || 0),
        venda_bruta: Number(r.venda_bruta || 0),
        descontos: Number(r.descontos || 0),
        venda_liquida: Number(r.venda_liquida || 0),
        servico: Number(r.servico || 0),
        total_com_servico: Number(r.total_com_servico || 0)
      }}));

      const months = [...new Set(vendas.map(v => v.mes))].sort();
      const latestMonth = months.length ? months[months.length - 1] : '2026-08';

      const assembled = {{
        meta: {{
          corte: corte,
          gerado: new Date().toISOString().slice(0, 10),
          lojas: lojasMap,
          ordem: ordem,
          mes_detalhe: latestMonth,
          base: 'GARÇOM WEB AO VIVO · SUPABASE RLS',
          provisorio: false,
          versao: '4.0.0-realtime',
          demo: false
        }}
      }};

      ALL_LIST_KEYS.forEach(k => {{ assembled[k] = []; }});
      assembled.vendas = vendas;

      (modulosRes.data || []).forEach(row => {{
        const mod = row.modulo;
        const arr = Array.isArray(row.dados) ? row.dados : [];
        if (!assembled[mod]) assembled[mod] = [];
        if (mod === 'aud' || mod === 'lacunas') {{
          if (assembled[mod].length === 0) assembled[mod] = arr;
        }} else {{
          assembled[mod].push(...arr);
        }}
      }});

      window.DATA = assembled;

      // Oculta tela de login e exibe controles de sessão
      document.getElementById('mesaAuthOverlay').classList.add('hidden');
      const liveBadge = document.getElementById('mesaLiveBadge');
      const liveTxt = document.getElementById('mesaLiveTxt');
      const logoutBtn = document.getElementById('bLogout');
      if (liveBadge) liveBadge.style.display = 'inline-flex';
      if (liveTxt) liveTxt.textContent = 'AO VIVO · ' + user.email;
      if (logoutBtn) logoutBtn.style.display = 'inline-block';

      if (!engineBooted) {{
        engineBooted = true;
        window.__bootMesaEngine();
      }} else if (window.__refreshMesaRealtime) {{
        window.__refreshMesaRealtime();
      }}

      subscribeRealtime();
    }} catch (err) {{
      showMsg(err.message || 'Falha ao carregar dados do Supabase.', 'err');
    }} finally {{
      if (btn) {{ btn.disabled = false; btn.textContent = 'Entrar e Conectar Ao Vivo →'; }}
    }}
  }}

  function subscribeRealtime() {{
    if (!supaClient || realtimeChannel) return;
    realtimeChannel = supaClient
      .channel('mesa-intelligence-live')
      .on('postgres_changes', {{ event: '*', schema: 'public', table: 'vendas_mensais' }}, payload => {{
        if (!window.DATA) return;
        const row = payload.new;
        if (!row || !row.idloja) return;
        const up = {{
          idloja: Number(row.idloja),
          mes: String(row.mes),
          pedidos_validos: Number(row.pedidos_validos || 0),
          lancado: Number(row.lancado || 0),
          excluidos: Number(row.excluidos || 0),
          venda_bruta: Number(row.venda_bruta || 0),
          descontos: Number(row.descontos || 0),
          venda_liquida: Number(row.venda_liquida || 0),
          servico: Number(row.servico || 0),
          total_com_servico: Number(row.total_com_servico || 0)
        }};
        const idx = window.DATA.vendas.findIndex(v => Number(v.idloja) === up.idloja && v.mes === up.mes);
        if (idx >= 0) window.DATA.vendas[idx] = up;
        else window.DATA.vendas.push(up);

        if (window.__refreshMesaRealtime) window.__refreshMesaRealtime();
        const nomeLoja = (window.DATA.meta.lojas && window.DATA.meta.lojas[String(up.idloja)]) || ('Loja ' + up.idloja);
        showToast('⚡ Vendas atualizadas ao vivo: ' + nomeLoja + ' (' + up.mes + ')');
      }})
      .on('postgres_changes', {{ event: '*', schema: 'public', table: 'loja_modulos' }}, payload => {{
        if (!window.DATA) return;
        const row = payload.new;
        if (!row || !row.modulo) return;
        const mod = row.modulo;
        const lid = Number(row.idloja);
        const novos = Array.isArray(row.dados) ? row.dados : [];
        if (mod === 'aud' || mod === 'lacunas') {{
          window.DATA[mod] = novos;
        }} else if (Array.isArray(window.DATA[mod])) {{
          window.DATA[mod] = window.DATA[mod].filter(item => Number(item.idloja) !== lid).concat(novos);
        }}
        if (window.__refreshMesaRealtime) window.__refreshMesaRealtime();
        showToast('⚡ Módulo "' + mod + '" sincronizado ao vivo!');
      }})
      .subscribe();
  }}

  window.addEventListener('DOMContentLoaded', async () => {{
    // Injeta overlay de autenticação no body
    document.body.insertAdjacentHTML('afterbegin', {json.dumps(AUTH_OVERLAY_HTML)});

    document.getElementById('mesaToggleCfgBtn').onclick = () => {{
      document.getElementById('mesaCfgBox').classList.toggle('open');
    }};

    document.getElementById('mesaSaveCfgBtn').onclick = () => {{
      const u = document.getElementById('mesaSupaUrl').value.trim();
      const k = document.getElementById('mesaSupaAnon').value.trim();
      if (!u || !k) {{
        showMsg('Preencha a Project URL e a Anon Key do Supabase.', 'err');
        return;
      }}
      localStorage.setItem('mesa_supa_url', u);
      localStorage.setItem('mesa_supa_anon', k);
      initSupabaseClient();
      document.getElementById('mesaCfgBox').classList.remove('open');
      showMsg('Conexão Supabase salva com sucesso! Faça login abaixo.', 'ok');
    }};

    document.getElementById('mesaLoginForm').onsubmit = async (e) => {{
      e.preventDefault();
      if (!supaClient && !initSupabaseClient()) {{
        showMsg('Configure primeiro a URL e Anon Key do seu projeto Supabase.', 'err');
        return;
      }}
      const email = document.getElementById('mesaEmail').value.trim();
      const password = document.getElementById('mesaPassword').value;
      const btn = document.getElementById('mesaLoginBtn');
      btn.disabled = true;
      btn.textContent = 'Autenticando no Supabase...';
      showMsg('', '');
      document.getElementById('mesaAuthMsg').style.display = 'none';

      const {{ data, error }} = await supaClient.auth.signInWithPassword({{ email, password }});
      if (error) {{
        btn.disabled = false;
        btn.textContent = 'Entrar e Conectar Ao Vivo →';
        showMsg('Erro de autenticação: ' + error.message, 'err');
        return;
      }}
      await fetchAndHydrateDashboard(data.user);
    }};

    const logoutBtn = document.getElementById('bLogout');
    if (logoutBtn) {{
      logoutBtn.onclick = async () => {{
        if (supaClient) await supaClient.auth.signOut();
        window.location.reload();
      }};
    }}

    if (initSupabaseClient()) {{
      const {{ data }} = await supaClient.auth.getSession();
      if (data && data.session && data.session.user) {{
        await fetchAndHydrateDashboard(data.session.user);
      }}
    }}
  }});
}})()"""

    final_html = prefix + supabase_controller_js + after_data

    with open(OUTPUT_APP, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"SUCCESS! Secure Live Web App generated at: {OUTPUT_APP}")
    print(f"Size reduction: {len(html)/1024/1024:.2f} MB -> {len(final_html)/1024:.1f} KB (0 bytes of exposed client data!)")


if __name__ == "__main__":
    build_webapp()
