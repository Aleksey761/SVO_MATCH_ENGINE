$ErrorActionPreference = 'Stop'

$root = 'f:\SVO\AI\SVO_MATCH_ENGINE'
$source = Join-Path $root 'output\FINANCE_RESULT.xlsx'
$target = Join-Path $root 'output\INVENTORY_ALIAS_FINANCE_BEFORE_AFTER.xlsx'
$report = Join-Path $root 'output\INVENTORY_ALIAS_FINANCE_BEFORE_AFTER.txt'

$beforeWithStock = 79
$beforeFinanceComplete = 63
$wanted = @(
    'SKU with stock',
    'Finance-complete SKU',
    'Inventory alias rows applied',
    'Total SKU',
    'Missing MASTER for PRICE SKU'
)

$excel = $null
$workbook = $null
$outWorkbook = $null

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false

    $workbook = $excel.Workbooks.Open($source)
    $sheet = $workbook.Worksheets.Item('FINANCE_LINEAGE')
    $usedRows = $sheet.UsedRange.Rows.Count

    $metrics = @{}
    for ($row = 1; $row -le $usedRows; $row++) {
        $key = [string]$sheet.Cells.Item($row, 1).Text
        if ($wanted -contains $key) {
            $metrics[$key] = [int]$sheet.Cells.Item($row, 2).Value2
        }
    }

    foreach ($name in $wanted) {
        if (-not $metrics.ContainsKey($name)) {
            throw "Missing FINANCE_LINEAGE metric: $name"
        }
    }

    $afterWithStock = $metrics['SKU with stock']
    $afterFinanceComplete = $metrics['Finance-complete SKU']
    $aliasRows = $metrics['Inventory alias rows applied']
    $regressions = ($afterWithStock -lt $beforeWithStock) -or ($afterFinanceComplete -lt $beforeFinanceComplete)

    if (Test-Path $target) {
        Remove-Item $target -Force
    }

    $outWorkbook = $excel.Workbooks.Add()
    $outSheet = $outWorkbook.Worksheets.Item(1)
    $outSheet.Name = 'SUMMARY'
    $rows = @(
        @('Metric', 'Value'),
        @('Alias applied', $(if ($aliasRows -gt 0) { 'YES' } else { 'NO' })),
        @('Stock improved', $(if ($afterWithStock -gt $beforeWithStock) { 'YES' } else { 'NO' })),
        @('Finance complete improved', $(if ($afterFinanceComplete -gt $beforeFinanceComplete) { 'YES' } else { 'NO' })),
        @('Regressions', $(if ($regressions) { 'YES' } else { 'NO' })),
        @('WITH_STOCK BEFORE', $beforeWithStock),
        @('WITH_STOCK AFTER', $afterWithStock),
        @('FINANCE_COMPLETE BEFORE', $beforeFinanceComplete),
        @('FINANCE_COMPLETE AFTER', $afterFinanceComplete),
        @('Inventory alias rows applied', $aliasRows),
        @('Total SKU', $metrics['Total SKU']),
        @('Missing MASTER for PRICE SKU', $metrics['Missing MASTER for PRICE SKU'])
    )

    for ($i = 0; $i -lt $rows.Count; $i++) {
        $outSheet.Cells.Item($i + 1, 1).Value2 = $rows[$i][0]
        $outSheet.Cells.Item($i + 1, 2).Value2 = $rows[$i][1]
    }

    $outWorkbook.SaveAs($target, 51)

    $lines = @(
        "AFTER_WITH_STOCK=$afterWithStock",
        "AFTER_FINANCE_COMPLETE=$afterFinanceComplete",
        "AFTER_ALIAS_ROWS=$aliasRows",
        "AFTER_TOTAL_SKU=$($metrics['Total SKU'])",
        "AFTER_MISSING_MASTER=$($metrics['Missing MASTER for PRICE SKU'])",
        "REGRESSIONS=$(if ($regressions) { 'YES' } else { 'NO' })",
        "WORKBOOK_CREATED=$(if (Test-Path $target) { 'YES' } else { 'NO' })"
    )
    Set-Content -Path $report -Value $lines -Encoding UTF8
    $lines | ForEach-Object { Write-Output $_ }
}
finally {
    if ($workbook) { $workbook.Close($false) }
    if ($outWorkbook) { $outWorkbook.Close($false) }
    if ($excel) { $excel.Quit() }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}