# Importação para revisão; nunca remove ou sobrescreve o scaffold versionado.
param(
    [string]$Projeto,
    [string]$ProjetoScripts,
    [string]$GlobalMcp,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
foreach ($origem in @($Projeto, $ProjetoScripts, $GlobalMcp)) {
    if ([string]::IsNullOrWhiteSpace($origem) -or -not (Test-Path -LiteralPath $origem -PathType Container)) {
        Write-Error 'Informe -Projeto (.claude), -ProjetoScripts e -GlobalMcp com diretórios existentes. Nenhuma importação iniciada.'
        exit 2
    }
}
$importador = Join-Path $PSScriptRoot 'scripts/importar_scaffold.py'
& $Python $importador --projeto $Projeto --scripts $ProjetoScripts --mcps-globais $GlobalMcp
exit $LASTEXITCODE
