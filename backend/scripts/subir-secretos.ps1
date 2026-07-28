# Sube en BLOQUE a Secret Manager los valores del Modulo D + core, leidos del .env.
#
# Por que no sube el .env entero: cloudbuild.yaml solo consume estas claves como
# secretos. Lo que NO va aqui: ENVIRONMENT, CORS_* y GOOGLE_DRIVE_REDIRECT_URI, que
# son especificos del entorno (la redirect de prod NO es la de tu .env local, que
# apunta a localhost) -> esos siguen como env vars en cloudbuild.yaml --set-env-vars.
#
# Cada ejecucion AGREGA una nueva version del secreto (:latest) => sobrescribe el
# valor viejo. Crea el secreto si no existe. NO imprime valores. Escribe a un temp
# sin BOM y sin salto de linea final (un \n al final rompe DATABASE_URL: ver DEPLOY.md).
#
# Uso (desde backend/):
#   .\scripts\subir-secretos.ps1              # solo sube los secretos
#   .\scripts\subir-secretos.ps1 -Redeploy    # sube y rueda una revision nueva
#   .\scripts\subir-secretos.ps1 -EnvFile ..\otro.env
param(
    [string]$EnvFile = ".env",
    [string]$Project = "project-e4ebe808-25e7-4d10-844",
    [string]$Service = "kiosko-backend",
    [string]$Region  = "us-west2",
    [switch]$Redeploy
)

# Continue (NO Stop): gcloud es un ejecutable nativo y escribe a stderr en casos
# NORMALES (p. ej. NOT_FOUND al verificar si un secreto existe todavia). Con "Stop",
# PowerShell 5.1 convierte ese stderr en error terminante y aborta el script. Aqui se
# controla el exito de cada llamada por su exit code ($LASTEXITCODE), no por stderr.
$ErrorActionPreference = "Continue"

# Ejecuta gcloud capturando salida + exit code; no aborta aunque escriba a stderr.
function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GArgs)
    $salida = & gcloud @GArgs 2>&1
    return [pscustomobject]@{ Code = $LASTEXITCODE; Out = ($salida | Out-String).Trim() }
}

# Mapeo CLAVE_EN_.ENV -> nombre-del-secreto. Si agregas un secreto nuevo, solo anade
# la linea aqui (debe coincidir con el --set-secrets de cloudbuild.yaml).
$MAP = [ordered]@{
    # Core
    "DATABASE_URL"               = "kiosko-database-url"
    "SECRET_KEY"                 = "kiosko-secret-key"
    # Modulo D - Google Drive (OAuth). OJO: GOOGLE_DRIVE_REDIRECT_URI NO va aqui.
    "GOOGLE_DRIVE_CLIENT_ID"     = "kiosko-drive-client-id"
    "GOOGLE_DRIVE_CLIENT_SECRET" = "kiosko-drive-client-secret"
    "GOOGLE_DRIVE_FOLDER_ID"     = "kiosko-drive-folder-id"
    # Modulo D - Telegram
    "TELEGRAM_BOT_TOKEN"         = "kiosko-telegram-bot-token"
    "TELEGRAM_CHAT_ID"           = "kiosko-telegram-chat-id"
    # Modulo D - Correo (SMTP)
    "SMTP_HOST"                  = "kiosko-smtp-host"
    "SMTP_PORT"                  = "kiosko-smtp-port"
    "SMTP_USER"                  = "kiosko-smtp-user"
    "SMTP_PASS"                  = "kiosko-smtp-pass"
    "CORREO_REMITENTE"           = "kiosko-correo-remitente"
    "CORREO_DESTINO"             = "kiosko-correo-destino"
}

if (-not (Test-Path $EnvFile)) { throw "No encuentro '$EnvFile'. Corre el script desde la carpeta backend/." }

# --- Parsear .env -> hashtable (ignora comentarios y lineas vacias) ---
$vals = @{}
foreach ($line in Get-Content -LiteralPath $EnvFile) {
    $t = $line.Trim()
    if ($t -eq "" -or $t.StartsWith("#")) { continue }
    $i = $t.IndexOf("=")
    if ($i -lt 1) { continue }
    $k = $t.Substring(0, $i).Trim()
    $v = $line.Substring($line.IndexOf("=") + 1)   # el valor puede contener "="
    # quitar comillas envolventes si las hubiera
    if ($v.Length -ge 2 -and (($v[0] -eq '"' -and $v[-1] -eq '"') -or ($v[0] -eq "'" -and $v[-1] -eq "'"))) {
        $v = $v.Substring(1, $v.Length - 2)
    }
    $vals[$k] = $v
}

$tmp = Join-Path $env:TEMP ("kiosko_secret_" + [guid]::NewGuid().ToString() + ".txt")
$subidos = 0
$faltantes = 0
$fallidos = 0
try {
    foreach ($k in $MAP.Keys) {
        $secret = $MAP[$k]
        if (-not $vals.ContainsKey($k)) {
            Write-Host ("  FALTA   {0,-28} (no esta en {1})" -f $k, $EnvFile) -ForegroundColor DarkYellow
            $faltantes++
            continue
        }
        # Quitar SOLO salto de linea final (no espacios: podrian ser parte del valor)
        $value = $vals[$k].TrimEnd("`r", "`n")
        if ($value -eq "") {
            Write-Host ("  VACIO   {0,-28} (valor vacio en {1})" -f $k, $EnvFile) -ForegroundColor DarkYellow
            $faltantes++
            continue
        }
        # UTF-8 sin BOM y sin newline final
        [System.IO.File]::WriteAllText($tmp, $value, (New-Object System.Text.UTF8Encoding($false)))

        # Crear el secreto si no existe (describe != 0 => no existe todavia)
        $desc = Invoke-Gcloud secrets describe $secret --project $Project
        if ($desc.Code -ne 0) {
            $cre = Invoke-Gcloud secrets create $secret --replication-policy=automatic --project $Project
            if ($cre.Code -ne 0) {
                Write-Host ("  ERROR   {0,-28} -> no se pudo crear {1}" -f $k, $secret) -ForegroundColor Red
                if ($cre.Out) { Write-Host ("          {0}" -f $cre.Out) -ForegroundColor DarkGray }
                $fallidos++
                continue
            }
            Write-Host ("  CREADO  {0}" -f $secret) -ForegroundColor Cyan
        }

        $add = Invoke-Gcloud secrets versions add $secret --data-file=$tmp --project $Project
        if ($add.Code -ne 0) {
            Write-Host ("  ERROR   {0,-28} -> {1}" -f $k, $secret) -ForegroundColor Red
            if ($add.Out) { Write-Host ("          {0}" -f $add.Out) -ForegroundColor DarkGray }
            $fallidos++
            continue
        }
        Write-Host ("  OK      {0,-28} -> {1} (nueva version, {2} chars)" -f $k, $secret, $value.Length) -ForegroundColor Green
        $subidos++
    }
}
finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
}

Write-Host ""
$color = if ($fallidos) { "Red" } elseif ($faltantes) { "Yellow" } else { "Green" }
Write-Host ("Subidos: {0}   Faltan/vacios: {1}   Errores: {2}" -f $subidos, $faltantes, $fallidos) -ForegroundColor $color
if ($faltantes -gt 0) {
    Write-Host "Aviso: faltan claves en el .env; el deploy fallara al referenciar esos secretos." -ForegroundColor Yellow
}

if ($Redeploy) {
    if ($fallidos -gt 0 -or $subidos -eq 0) {
        Write-Host "No se redeploya: hubo errores o no se subio ningun secreto." -ForegroundColor Yellow
        exit 1
    }
    $pares = ($MAP.GetEnumerator() | ForEach-Object { "{0}={1}:latest" -f $_.Key, $_.Value }) -join ","
    Write-Host "`nRodando revision nueva de $Service con los secretos :latest..." -ForegroundColor Cyan
    gcloud run services update $Service --region $Region --project $Project --update-secrets=$pares
    Write-Host "`nVerifica:  curl https://kiosko-backend-1049232196871.us-west2.run.app/health" -ForegroundColor Cyan
}

if ($fallidos -gt 0) { exit 1 }
