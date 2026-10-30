# exportar_dados_pbi.ps1
# Extrai dados do Power BI Desktop aberto e exporta para JSON
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   MESA Intelligence - Extrator Local Power BI Desktop    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Detectar processo do Power BI Desktop
$pbi = Get-Process PBIDesktop -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pbi) {
    Write-Error "Power BI Desktop nao esta aberto! Abra o arquivo .pbix antes de rodar este script."
    exit 1
}

Write-Host "[1/4] Power BI Desktop detectado (PID: $($pbi.Id))" -ForegroundColor Green

# 2. Localizar porta do Analysis Services
$msmdsrv = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $pbi.Id -and $_.Name -eq 'msmdsrv.exe' }
if (-not $msmdsrv) {
    Write-Error "Processo msmdsrv.exe do Power BI nao encontrado."
    exit 1
}

$netConn = Get-NetTCPConnection -OwningProcess $msmdsrv.ProcessId -State Listen | Select-Object -First 1
if (-not $netConn) {
    Write-Error "Nao foi possivel identificar a porta local de conexao do Power BI."
    exit 1
}
$port = $netConn.LocalPort
Write-Host "[2/4] Instancia de dados conectada na porta: $port" -ForegroundColor Green

# 3. Carregar ADOMD.NET
$dll = "C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll"
if (-not (Test-Path $dll)) {
    $dll = (Get-ChildItem -Path "C:\Program Files\Microsoft Power BI Desktop" -Filter "*AdomdClient.dll" -Recurse | Select-Object -First 1).FullName
}
[System.Reflection.Assembly]::LoadFrom($dll) | Out-Null

$connStr = "Data Source=localhost:$port;"
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($connStr)
$conn.Open()
Write-Host "[3/4] Conexao DAX aberta com sucesso!" -ForegroundColor Green

function Query-ToObjects($daxQuery) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $daxQuery
    $adapter = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdDataAdapter($cmd)
    $ds = New-Object System.Data.DataSet
    $adapter.Fill($ds) | Out-Null
    
    $table = $ds.Tables[0]
    $cols = $table.Columns | ForEach-Object { $_.ColumnName }
    $rows = foreach ($r in $table.Rows) {
        $dict = [ordered]@{}
        foreach ($c in $cols) {
            $val = $r[$c]
            if ($val -eq [DBNull]::Value) {
                $dict[$c] = $null
            } else {
                $dict[$c] = $val
            }
        }
        [PSCustomObject]$dict
    }
    return $rows
}

Write-Host "[4/4] Extraindo tabelas via DAX..." -ForegroundColor Yellow

$exportData = [ordered]@{}

# 1. Lojas
Write-Host "  -> Extraindo lojas..." -ForegroundColor Gray
$exportData["lojas"] = Query-ToObjects "EVALUATE d_loja"

# 2. Vendas Mensais
Write-Host "  -> Extraindo vendas mensais..." -ForegroundColor Gray
$exportData["vendas"] = Query-ToObjects @"
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
"@

# 3. Produtos
Write-Host "  -> Extraindo produtos..." -ForegroundColor Gray
$exportData["produtos"] = Query-ToObjects @"
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
"@

# 4. Grupos
Write-Host "  -> Extraindo grupos..." -ForegroundColor Gray
$exportData["grupos"] = Query-ToObjects @"
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
"@

# 5. Horas
Write-Host "  -> Extraindo horas..." -ForegroundColor Gray
$exportData["horas"] = Query-ToObjects @"
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
"@

# 6. Exclusoes
Write-Host "  -> Extraindo exclusoes..." -ForegroundColor Gray
$exportData["excl"] = Query-ToObjects @"
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
"@

# 7. Financeiro
Write-Host "  -> Extraindo lancamentos financeiros..." -ForegroundColor Gray
$exportData["dre_lanc"] = Query-ToObjects @"
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
"@

# 8. Meios
Write-Host "  -> Extraindo meios de recebimento..." -ForegroundColor Gray
$exportData["fech_meio"] = Query-ToObjects @"
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
"@

$conn.Close()

$outFile = Join-Path $PSScriptRoot "raw_pbi_data.json"
$exportData | ConvertTo-Json -Depth 10 | Set-Content -Path $outFile -Encoding UTF8
Write-Host "Dados brutos exportados com sucesso para: $outFile" -ForegroundColor Green
