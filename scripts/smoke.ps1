<#
.SYNOPSIS
  Test de bout en bout : santé des services, pipeline API -> Kafka -> worker -> Ollama -> WebSocket,
  aller-retour RAG (rien n'est conservé), puis la même liaison vue depuis Godot (headless).
  Si l'API ne répond pas, l'API et le worker system_ping sont démarrés le temps du test.
#>
param([switch]$KeepRunning, [switch]$NoGodot)
. "$PSScriptRoot\_common.ps1"
Assert-Venv
$api = Get-ApiUrl

function Test-Api {
    try { $null = Invoke-RestMethod "$api/health" -TimeoutSec 10; return $true } catch { return $false }
}

$started = @()
if (-not (Test-Api)) {
    Write-Step "API absente : démarrage temporaire de l'API"
    $started += Start-Process -FilePath $VenvPython -WorkingDirectory $BackendDir -WindowStyle Hidden -PassThru `
        -ArgumentList @('-m', 'uvicorn', 'gmix.api.main:app', '--host', (Get-DotEnv 'API_HOST' '127.0.0.1'), '--port', (Get-DotEnv 'API_PORT' '8000'))
    for ($i = 0; $i -lt 60 -and -not (Test-Api); $i++) { Start-Sleep -Milliseconds 500 }
}

# Worker system_ping : lancé seulement s'il ne tourne pas (même si l'API répond déjà), non arrêté ici : stop.ps1 s'en charge
$pingRunning = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and [string]$_.CommandLine -match 'gmix\.workers\.system_ping' }).Count -gt 0
if (-not $pingRunning) {
    Write-Step 'Worker system_ping absent : démarrage'
    $null = Start-Process -FilePath $VenvPython -WorkingDirectory $BackendDir -WindowStyle Hidden -PassThru `
        -ArgumentList @('-m', 'gmix.workers.system_ping')
    Start-Sleep -Seconds 5
}

# Worker generation : même règle que system_ping (un seul exemplaire, arrêté par stop.ps1)
$genRunning = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and [string]$_.CommandLine -match 'gmix\.workers\.generation' }).Count -gt 0
if (-not $genRunning) {
    Write-Step 'Worker generation absent : démarrage'
    $null = Start-Process -FilePath $VenvPython -WorkingDirectory $BackendDir -WindowStyle Hidden -PassThru `
        -ArgumentList @('-m', 'gmix.workers.generation')
    Start-Sleep -Seconds 5
}

$code = 0
try {
    Write-Step 'Backend (Python) puis client Godot headless, avec un compte admin jetable'
    $smokeArgs = @('-m', 'gmix.tools.smoke', '--api', $api)
    if (-not $NoGodot) { $smokeArgs += @('--godot', (Get-GodotExe -Console)) }
    & $VenvPython @smokeArgs
    if ($LASTEXITCODE -ne 0) { $code = 1 }
} finally {
    if (-not $KeepRunning) { $started | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } }
}
Write-Step 'Bilan'
if ($code -eq 0) { Write-Ok 'Environnement opérationnel de bout en bout' } else { Write-Ko 'Au moins un test a échoué (voir ci-dessus)' }
exit $code
