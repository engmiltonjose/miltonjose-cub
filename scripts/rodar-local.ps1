# Coleta, no PC do Milton, as fontes que bloqueiam o GitHub Actions (hoje: Sinduscon-SE) e publica no repositório.
#   powershell -File rodar-local.ps1            → roda uma vez
#   powershell -File rodar-local.ps1 -Instalar  → registra a tarefa agendada "Milton - CUB local" (dias úteis, 10:30)
param([switch]$Instalar)
$repo = Split-Path -Parent $PSScriptRoot
if ($Instalar) {
    $acao = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    $gat = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 10:30
    Register-ScheduledTask -TaskName "Milton - CUB local" -Action $acao -Trigger $gat -Description "Coleta o CUB das fontes que bloqueiam o GitHub (SE) e publica em engmiltonjose/miltonjose-cub" -Force | Out-Null
    Write-Output "Tarefa 'Milton - CUB local' registrada (dias úteis, 10:30)."
    exit 0
}
Set-Location $repo
git pull -q
$log = Join-Path $env:TEMP "cub-local.log"
python scripts/atualizar_cub.py --ufs SE --so-proprios *> $log
git add dados/
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -q -m "CUB: atualizacao local (SE) $(Get-Date -Format yyyy-MM-dd)"
    git push -q
}
