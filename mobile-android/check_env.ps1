$ErrorActionPreference = "SilentlyContinue"

Write-Host "== Verane Mobile Android - Environment Check ==" -ForegroundColor Cyan

function Check-Command($name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) {
    Write-Host "[OK] $name encontrado: $($cmd.Source)" -ForegroundColor Green
    return $true
  }
  Write-Host "[WARN] $name no encontrado en PATH" -ForegroundColor Yellow
  return $false
}

Check-Command "java" | Out-Null
Check-Command "adb" | Out-Null
Check-Command "git" | Out-Null
Check-Command "docker" | Out-Null

Write-Host ""
Write-Host "Sugerencias:" -ForegroundColor Cyan
Write-Host "1) Instala Android Studio + Android SDK Platform 34."
Write-Host "2) Crea/usa un emulador desde Device Manager."
Write-Host "3) Abre C:\\verane-whatsapp-ai\\mobile-android en Android Studio."
Write-Host "4) Si el backend es local, usa API Base URL: http://10.0.2.2:8000"
