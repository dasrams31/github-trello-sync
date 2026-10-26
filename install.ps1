# Installer github-trello-sync untuk Windows PowerShell.
# Pemakaian dari folder repo target:
#   irm https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.ps1 | iex
# Sengaja memakai return, bukan exit, agar jendela PowerShell tidak tertutup saat dijalankan lewat iex.
$ErrorActionPreference = 'Stop'
$raw = 'https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.py'

$python = $null
foreach ($candidate in 'py', 'python', 'python3') {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        & $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
    }
}
if (-not $python) {
    Write-Host 'Python 3.8 atau lebih baru belum terpasang. Unduh di https://www.python.org/downloads/' -ForegroundColor Red
    return
}

$script = if ($PSScriptRoot) { Join-Path $PSScriptRoot 'install.py' } else { '' }
$temporary = $false
if (-not $script -or -not (Test-Path $script)) {
    $script = Join-Path ([System.IO.Path]::GetTempPath()) 'github-trello-sync-install.py'
    Invoke-WebRequest -Uri $raw -OutFile $script -UseBasicParsing
    $temporary = $true
}

try {
    & $python $script @args
} finally {
    if ($temporary) { Remove-Item $script -ErrorAction SilentlyContinue }
}
