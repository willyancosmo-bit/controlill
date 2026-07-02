# Control.ILL — Iniciador do Sistema
# Execute com botao direito > Executar com PowerShell

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BasePython = "C:\Users\willy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$VenvDir    = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Set-Location $ProjectDir
$env:PYTHONPATH       = ""
$env:PYTHONNOUSERSITE = "1"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Preparando o ambiente pela primeira vez..." -ForegroundColor Cyan
    & $BasePython -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Write-Host "Erro ao criar ambiente." -ForegroundColor Red; exit $LASTEXITCODE }
}

Write-Host "Verificando dependencias..." -ForegroundColor Cyan
& $VenvPython -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "Erro ao instalar dependencias." -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Control.ILL  |  Iniciando...       " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Acesso:  http://127.0.0.1:8501"       -ForegroundColor Yellow
Write-Host ""

Start-Process "http://127.0.0.1:8501"
& $VenvPython -m streamlit run app.py --server.address 0.0.0.0 --server.headless true
