# 🍽️ MESA Intelligence · Integração Garçom Web via Power BI Gateway

[![Status](https://img.shields.io/badge/Status-MVP%20Validado-success.svg?style=flat-square)]()
[![Custo Mensal](https://img.shields.io/badge/Custo%20de%20Infra-R%24%200%20(Pro)-blue.svg?style=flat-square)]()
[![Power BI](https://img.shields.io/badge/Power%20BI-Desktop%20%2F%20Gateway-yellow.svg?style=flat-square)]()
[![Tecnologias](https://img.shields.io/badge/Stack-DAX%20%7C%20PowerShell%20%7C%20Python%20%7C%20HTML5-informational.svg?style=flat-square)]()

Projeto de inteligência gerencial e consolidação financeira para restaurantes da **Consultoria MESA**. Conecta diretamente ao banco de dados dos clientes (**Garçom Web - MySQL/ODBC**) através do **Microsoft On-premises Data Gateway**, alimentando um painel executivo interativo de alta fidelidade.

---

## 📌 Contexto e Desafio de Arquitetura

* **Escala:** ~1.200 clientes finais (piloto iniciado com 10 lojas selecionadas).
* **Segurança e Rede:** Restaurantes possuem IP dinâmico e firewalls locais. O **On-premises Data Gateway** já instalado resolve o tunelamento seguro sem necessidade de portas abertas ou VPNs dedicadas.
* **Licenciamento:** Operação viabilizada 100% sobre o **Power BI Pro** existente, eliminando os custos proibitivos de capacidades Microsoft Fabric (US$ 260+/mês) na fase de validação do MVP.

---

## 🧭 Comparativo dos 3 Formatos Estratégicos

Para atender ao plano de testes da consultoria sem investimento inicial em infraestrutura em nuvem, definimos 3 caminhos complementares:

```mermaid
flowchart TD
    GW["MySQL do Restaurante\n(Garçom Web)"] -->|Gateway On-premises| PBI_Service["Power BI Pro Service (Nuvem)"]
    GW -->|Gateway / Atualização Local| PBI_Desktop["Power BI Desktop (Local)"]

    subgraph OP2["OPÇÃO 2 · Extração Local 1-Clique (IMPLEMENTADA)"]
        PBI_Desktop -->|DAX Query local via ADOMD| ExtratorLocal["PowerShell + Python Engine"]
        ExtratorLocal -->|Injeção cirúrgica de dados| HTML_Live["MESA_Intelligence_Live.html\n(Dashboard Interativo)"]
    end

    subgraph OP1["OPÇÃO 1 · Automação Cloud (Power BI REST API)"]
        PBI_Service -->|API executeQueries (DAX)| ExtratorCloud["Script Python / Rotina Noturna"]
        ExtratorCloud -->|Gera HTML por cliente| HTML_Cloud["Dashboard Web Automatizado"]
    end

    subgraph OP3["OPÇÃO 3 · Dashboard Único Nativo no Power BI"]
        PBI_Desktop -->|Unificação de Modelos DAX| PBI_Report["Painel Consolidado no .pbix\n(Vendas + DRE + Caixa)"]
    end
```

### 📊 Matriz Comparativa

| Critério | Opção 1: Nuvem Pro (REST API) | Opção 2: Local 1-Clique (Desktop DAX) ⚡ | Opção 3: Dashboard Único PBI |
|---|---|---|---|
| **Status** | Roteiro pronto para ativação | **✅ Implementado e Validado** | Em modelagem visual |
| **Custo Mensal** | **R$ 0** (incluso no Power BI Pro) | **R$ 0** (incluso no Power BI Desktop) | **R$ 0** (incluso no Power BI Pro) |
| **Interface de Entrega** | HTML MESA Intelligence (Web) | HTML MESA Intelligence (Web) | Relatório Nativo Power BI (.pbix) |
| **Dependência Local** | Nenhuma (roda na nuvem) | Requer Power BI Desktop aberto | Requer Power BI Service ou App |
| **Velocidade de Execução** | ~5 a 10s via API REST | **~3 a 8s via porta local** | Instantâneo ao abrir o relatório |
| **Automação** | 100% autônomo (via cron/scheduler) | Manual (1 duplo-clique no `.bat`) | Automático via agendamento do Pro |
| **Ideal para...** | Envio de relatórios em escala | **Reuniões de consultoria e diagnósticos rápidos** | Analistas que já operam no Power BI |

---

## ⚡ Opção 2: Detalhes da Solução Implementada

A **Opção 2** foi implementada com foco em fricção zero para a equipe de consultoria:

1. **Auto-detecção de Instância:** O script local localiza o processo do Power BI Desktop (`PBIDesktop.exe`), descobre o processo filho do Analysis Services (`msmdsrv.exe`) e identifica dinamicamente a porta TCP ativa (ex: `50566`, `64009`), dispensando configurações manuais.
2. **Conexão Nativa ADOMD.NET:** Utiliza a biblioteca oficial `Microsoft.PowerBI.AdomdClient.dll` para submeter consultas DAX ultrarrápidas diretamente contra a engine de dados em memória.
3. **Resiliência a Schemas Dinâmicos:** As consultas utilizam agregações nativas sobre as tabelas acumuladas (`gw_vendas_acumulado`, `gw_caixa_detalha_acumulado`, `Financeiro`), imunes a variações regionais ou renomeações de colunas do calendário.
4. **Injeção Cirúrgica no HTML:** O script Python substitui apenas o payload da variável `const DATA = { ... }` dentro do template da consultoria, mantendo 100% da reatividade, gráficos e regras de negócio da interface.

### 📈 Métricas Reais Extraídas das Lojas Piloto

No teste executado com os restaurantes **WORLD CAFE** e **TEMPLO DO RAIMUNDAO**, foram consolidados:

* **2 Lojas Ativas:** Histórico unificado com alternância instantânea por filtro.
* **118 Períodos Mensais:** Vendas líquidas, brutas, descontos, comandas válidas e taxas de serviço.
* **33.713 Registros de Produtos:** Curva ABC e participação por grupos (Alimentos, Bebidas, etc.).
* **2.000 Motivos de Exclusão:** Rastreamento de cancelamentos e perdas operacionais no PDV.
* **5.000 Lançamentos Financeiros:** Detalhamento de contas a pagar, centros de custo e DRE.
* **1.652 Fechamentos de Caixa:** Abertura por meio de pagamento (Cartões, Pix, Dinheiro).
* **Arquivo Resultante:** `MESA_Intelligence_Live.html` (~8.2 MB autônomo, roda offline em qualquer navegador).

---

## 🚀 Como Executar

### Pré-requisitos
* Sistema Operacional: Windows 10/11
* Power BI Desktop instalado e aberto com o relatório conectado ao Gateway
* Python 3.8+ instalado

### Execução em 1 Clique (Recomendado)
Dê um duplo clique no arquivo:
```cmd
atualizar_dashboard.bat
```
O script irá:
1. Conectar-se automaticamente ao Power BI Desktop aberto.
2. Extrair todas as tabelas em ~5 segundos.
3. Injetar os dados no dashboard e salvar o arquivo `MESA_Intelligence_Live.html`.
4. Abrir automaticamente a visualização atualizada no seu navegador padrão.

---

## 📂 Estrutura do Repositório

```text
powerbi_gateway_mysql_mvp/
├── atualizar_dashboard.bat       # Executável de 1 clique para extração e abertura
├── MESA_Intelligence_Live.html   # Dashboard executivo gerado com dados reais
├── README.md                     # Documentação técnica e arquitetural
├── .gitignore                    # Filtro de dados temporários e caches
└── scripts/
    ├── exportar_dados_pbi.ps1    # Extrator DAX via ADOMD.NET (PowerShell)
    ├── gerar_html_live.py        # Motor de formatação e injeção do JSON (Python)
    └── build_extractor.py        # Utilitário de regeneração de scripts
```

---

## 🔮 Roteiro de Expansão (Próximas Fases)

### Ativação da Opção 1 (Automação Nuvem)
* Registrar um aplicativo no Microsoft Entra ID (Azure AD) com permissão `Dataset.Read.All`.
* Utilizar o endpoint `POST https://api.powerbi.com/v1.0/myorg/groups/{groupId}/datasets/{datasetId}/executeQueries` para executar as mesmas consultas DAX da Opção 2 diretamente na nuvem.
* Configurar pipeline em GitHub Actions ou agendador local para gerar os dashboards por cliente toda madrugada após o refresh do Gateway.

### Ativação da Opção 3 (Dashboard Nativo)
* Modelar uma página executiva "MESA Master" dentro do próprio `.pbix`.
* Combinar as medidas de `Medidas Vendas`, `Medidas Caixa` e `Medidas DRE` em um layout executivo escuro equivalente ao padrão visual do HTML.

---

*Desenvolvido para **Consultoria MESA** · Gestão Financeira e Inteligência para Hospitalidade.*
