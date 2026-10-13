# Despliegue COMPLETO del backend a Cloud Run tomando TODAS las variables del .env.
#
# Que hace (en orden):
#   1. Lee TODAS las claves del .env (las que agregues en el futuro tambien).
#   2. Las sensibles -> Secret Manager (crea el secreto si no existe; solo agrega
#      version nueva si el valor CAMBIO, para no acumular versiones con costo).
#      Las de entorno (ENVIRONMENT, CORS_*, GOOGLE_DRIVE_REDIRECT_URI) -> env vars.
#   3. Construye la imagen con Cloud Build (Dockerfile) y la sube a Artifact Registry.
#   4. Despliega en Cloud Run REEMPLAZANDO todas las variables por las del .env
#      (lo que no esta en el .env se quita del servicio).
#
# Convivencia con otros proyectos en el MISMO proyecto de GCP:
#   Los nombres de las variables (DATABASE_URL...) NO chocan: cada servicio de Cloud Run
#   tiene las suyas. Lo que SI es compartido en el proyecto es el nombre del servicio y
#   los nombres de los secretos. Por eso todo lleva el prefijo de -Service:
#   servicio "minimarket-backend" -> secretos "minimarket-*", imagen ".../minimarket-backend".
#   Ademas el script NO sobrescribe un servicio que no haya creado el (otro equipo).
#
# Excepciones a "tal cual el .env" (si no, se rompe):
#   - GOOGLE_DRIVE_REDIRECT_URI se calcula con la URL REAL del servicio
#     (https://SERVICIO-NUMERO.REGION.run.app/drive/callback).
#   - CORS_ORIGINS / CORS_ORIGIN_REGEX: si no estan en el .env, se usan localhost +
#     el regex de los deploys de Vercel (minimarket-*.vercel.app).
#   - ENVIRONMENT se fuerza a "production".
#   - SECRET_KEY: si en el .env es la de ejemplo ("change-me" o < 32 chars) se genera una
#     aleatoria la 1ra vez y despues se conserva (la del .env local no sirve en produccion).
#
# Uso (desde backend/):
#   .\scripts\desplegar.ps1 -DryRun     # muestra el plan, NO sube nada
#   .\scripts\desplegar.ps1             # despliega
#   .\scripts\desplegar.ps1 -Setup      # 1ra vez en un proyecto GCP nuevo (APIs, repo, permisos)
#   .\scripts\desplegar.ps1 -Service otro-backend -Project otro-proyecto -Yes
param(
    [string]$EnvFile = ".env",
    [string]$Project = "",                 # vacio = el proyecto activo de gcloud
    [string]$Service = "minimarket-backend",
    [string]$Region  = "us-west2",
    [string]$Repo    = "kiosko",
    [string]$RegionRepo = "",              # region del repo Artifact Registry (vacio = -Region)
    [string]$PrefijoSecretos = "",         # vacio = nombre del servicio sin "-backend"
    [switch]$ModoSesion,                   # DATABASE_URL al pooler en session mode (6543 -> 5432)
    [int]$MinInstancias = -1,              # -1 = no tocar el valor del servicio
    [int]$MaxInstancias = -1,
    [switch]$Setup,
    [switch]$DryRun,
    [switch]$Yes,
    [switch]$Sobrescribir                  # permite pisar un servicio que este script no creo
)

# Continue (NO Stop): gcloud escribe a stderr en casos normales; con "Stop" PowerShell 5.1
# lo convierte en error terminante. El exito se controla por $LASTEXITCODE.
$ErrorActionPreference = "Continue"

function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GArgs)
    $salida = & gcloud @GArgs 2>&1
    return [pscustomobject]@{ Code = $LASTEXITCODE; Out = ($salida | Out-String).Trim() }
}

function Fail($msg) { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }

# Prefijo de los secretos: el nombre del servicio sin "-backend" (o -PrefijoSecretos, para
# que dos servicios con nombres parecidos no compartan secretos).
$Prefijo = if ($PrefijoSecretos) { $PrefijoSecretos } else { $Service -replace '-backend$', '' }
if (-not $RegionRepo) { $RegionRepo = $Region }
$LABEL = "desplegado-por"
$LABEL_VALOR = "desplegar-ps1"

# Claves que van como env var normal (no son secretas y dependen del entorno).
# Todo lo demas del .env va a Secret Manager.
$PUBLICAS = @("ENVIRONMENT", "CORS_ORIGINS", "CORS_ORIGIN_REGEX", "GOOGLE_DRIVE_REDIRECT_URI")

# Sufijos historicos (compatibles con cloudbuild.yaml / subir-secretos.ps1 cuando el
# prefijo es "kiosko"). Una clave que no este aqui -> PREFIJO-clave-en-minusculas.
$SUFIJOS = @{
    "GOOGLE_DRIVE_CLIENT_ID"     = "drive-client-id"
    "GOOGLE_DRIVE_CLIENT_SECRET" = "drive-client-secret"
    "GOOGLE_DRIVE_FOLDER_ID"     = "drive-folder-id"
}
function Get-SecretName($key) {
    $suf = if ($SUFIJOS.ContainsKey($key)) { $SUFIJOS[$key] } else { $key.ToLower().Replace("_", "-") }
    return "$Prefijo-$suf"
}

function New-ClaveAleatoria {
    $b = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    return ([Convert]::ToBase64String($b)).Replace("+", "-").Replace("/", "_").TrimEnd("=")
}

# Todo se ejecuta desde backend/ (ahi estan Dockerfile, .gcloudignore y el .env).
Push-Location (Split-Path -Parent $PSScriptRoot)
$tmpDir = Join-Path $env:TEMP ("kiosko_deploy_" + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $tmpDir | Out-Null
try {
    if (-not (Test-Path $EnvFile)) { Fail "No encuentro '$EnvFile' dentro de backend/." }

    # ---------------------------------------------------------------- 1. Leer .env
    # Mismas reglas que python-dotenv (lo que usa la app en local): ignora comentarios,
    # quita comillas envolventes y, si no hay comillas, recorta espacios y " #comentario".
    $vals = [ordered]@{}
    foreach ($line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
        $t = $line.Trim()
        if ($t -eq "" -or $t.StartsWith("#")) { continue }
        if ($t.StartsWith("export ")) { $t = $t.Substring(7).TrimStart() }
        $i = $t.IndexOf("=")
        if ($i -lt 1) { continue }
        $k = $t.Substring(0, $i).Trim()
        $v = $t.Substring($i + 1).Trim()
        if ($v.Length -ge 2 -and (($v[0] -eq '"' -and $v[-1] -eq '"') -or ($v[0] -eq "'" -and $v[-1] -eq "'"))) {
            $v = $v.Substring(1, $v.Length - 2)
        } else {
            $v = ($v -replace '\s+#.*$', '').Trim()
        }
        $vals[$k] = $v
    }
    if ($vals.Count -eq 0) { Fail "El $EnvFile no tiene variables." }

    # Session mode: mismo host del pooler, puerto 5432. Con eso session.py activa el cache
    # de prepared statements (1 viaje por consulta en vez de 2). El .env local no cambia.
    if ($ModoSesion) {
        if ($vals["DATABASE_URL"] -notmatch '\.pooler\.supabase\.com:6543/') {
            Fail "-ModoSesion espera un DATABASE_URL del pooler de Supabase en el puerto 6543."
        }
        $vals["DATABASE_URL"] = $vals["DATABASE_URL"] -replace '(\.pooler\.supabase\.com):6543/', '$1:5432/'
    }

    # ---------------------------------------------------------------- 2. Proyecto destino
    if (-not $Project) { $Project = (& gcloud config get-value project 2>$null | Out-String).Trim() }
    if (-not $Project) { Fail "No hay proyecto. Usa -Project o 'gcloud config set project ID'." }
    $cuenta = (& gcloud config get-value account 2>$null | Out-String).Trim()
    $num = (& gcloud projects describe $Project --format="value(projectNumber)" 2>$null | Out-String).Trim()
    if (-not $num) { Fail "No pude leer el proyecto '$Project' con la cuenta '$cuenta' (no existe o no tienes permiso)." }

    $urlBack = "https://$Service-$num.$Region.run.app"
    $sa      = "$num-compute@developer.gserviceaccount.com"
    $image   = "$RegionRepo-docker.pkg.dev/$Project/$Repo/${Service}:" + (Get-Date -Format "yyyyMMdd-HHmmss")

    # ¿El servicio ya existe? Si existe y NO lo creo este script, es de otro equipo/proyecto.
    $estado = "nuevo"
    # stderr descartado: avisos de gcloud ("updates available") romperian el JSON.
    $svcJson = & gcloud run services describe $Service --region $Region --project $Project --format=json 2>$null
    if ($LASTEXITCODE -eq 0) {
        $labels = (($svcJson | Out-String) | ConvertFrom-Json).metadata.labels
        $estado = if ($labels -and $labels.$LABEL -eq $LABEL_VALOR) { "existe (creado por este script)" } else { "AJENO" }
    }

    # Env vars especificas del entorno (ver cabecera).
    $envVars = [ordered]@{}
    $envVars["ENVIRONMENT"] = "production"
    $envVars["CORS_ORIGINS"] = if ($vals["CORS_ORIGINS"]) { $vals["CORS_ORIGINS"] } else { "http://localhost:5173,http://localhost:5174" }
    $envVars["CORS_ORIGIN_REGEX"] = if ($vals["CORS_ORIGIN_REGEX"]) { $vals["CORS_ORIGIN_REGEX"] } else { 'https://minimarket-[a-z0-9-]+\.vercel\.app' }
    $envVars["GOOGLE_DRIVE_REDIRECT_URI"] = "$urlBack/drive/callback"
    foreach ($k in $vals.Keys) {   # cualquier otra clave publica que agregues a $PUBLICAS
        if ($PUBLICAS -contains $k -and -not $envVars.Contains($k)) { $envVars[$k] = $vals[$k] }
    }

    $secretos = [ordered]@{}
    $vacias = @()
    foreach ($k in $vals.Keys) {
        if ($PUBLICAS -contains $k) { continue }
        if ($vals[$k] -eq "") { $vacias += $k; continue }
        $secretos[$k] = Get-SecretName $k
    }
    # SECRET_KEY de ejemplo -> se genera una propia de produccion (ver cabecera).
    $skEjemplo = (-not $vals["SECRET_KEY"]) -or $vals["SECRET_KEY"] -eq "change-me" -or $vals["SECRET_KEY"].Length -lt 32
    if ($skEjemplo) { $secretos["SECRET_KEY"] = Get-SecretName "SECRET_KEY" }

    # ---------------------------------------------------------------- Plan
    Write-Host "`n=== Despliegue $Service ===" -ForegroundColor Cyan
    Write-Host ("Cuenta   : {0}" -f $cuenta)
    Write-Host ("Proyecto : {0} (numero {1})" -f $Project, $num)
    Write-Host ("Region   : {0}" -f $Region)
    Write-Host ("Servicio : {0} [{1}]" -f $Service, $estado)
    Write-Host ("URL      : {0}" -f $urlBack)
    Write-Host ("Imagen   : {0}" -f $image)
    Write-Host ("Secretos : prefijo '{0}-'" -f $Prefijo)
    if ($ModoSesion) { Write-Host "BD       : pooler en session mode (5432), cache de consultas activo" }
    if ($MinInstancias -ge 0) { Write-Host ("Min inst.: {0}" -f $MinInstancias) }
    if ($MaxInstancias -ge 0) { Write-Host ("Max inst.: {0}" -f $MaxInstancias) }
    Write-Host "`nSecretos (Secret Manager, valores NO se muestran):" -ForegroundColor Cyan
    foreach ($k in $secretos.Keys) {
        $nota = if ($k -eq "SECRET_KEY" -and $skEjemplo) { "  (la del .env es de ejemplo: se genera una aleatoria)" } else { "" }
        Write-Host ("  {0,-28} -> {1}{2}" -f $k, $secretos[$k], $nota)
    }
    Write-Host "`nVariables de entorno:" -ForegroundColor Cyan
    foreach ($k in $envVars.Keys) { Write-Host ("  {0,-28} = {1}" -f $k, $envVars[$k]) }
    if ($vals["GOOGLE_DRIVE_REDIRECT_URI"] -and $vals["GOOGLE_DRIVE_REDIRECT_URI"] -ne $envVars["GOOGLE_DRIVE_REDIRECT_URI"]) {
        Write-Host ("  (el .env tenia GOOGLE_DRIVE_REDIRECT_URI={0}; se usa la URL de este servicio)" -f $vals["GOOGLE_DRIVE_REDIRECT_URI"]) -ForegroundColor DarkYellow
    }
    foreach ($k in $vacias) { Write-Host ("  OMITIDA {0} (vacia en el .env -> la app usa su valor por defecto)" -f $k) -ForegroundColor DarkYellow }

    $bloqueo = ""
    if ($estado -eq "AJENO" -and -not $Sobrescribir) {
        $bloqueo = "El servicio '$Service' ya existe en este proyecto y NO lo creo este script (es de otro proyecto/equipo). Usa otro -Service, o -Sobrescribir si de verdad es tuyo."
        Write-Host "`nBLOQUEADO: $bloqueo" -ForegroundColor Red
    }

    if ($DryRun) { Write-Host "`n-DryRun: no se subio ni desplego nada." -ForegroundColor Yellow; return }
    if ($bloqueo) { Fail $bloqueo }
    if (-not $Yes) {
        $r = Read-Host "`nDesplegar con esta configuracion? (s/N)"
        if ($r -notmatch '^(s|si|y|yes)$') { Write-Host "Cancelado."; return }
    }

    # ---------------------------------------------------------------- Setup (1ra vez)
    if ($Setup) {
        Write-Host "`n[setup] Habilitando APIs..." -ForegroundColor Cyan
        & gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com --project $Project
        if ($LASTEXITCODE -ne 0) { Fail "No se pudieron habilitar las APIs (falta facturacion o permisos)." }

        if ((Invoke-Gcloud artifacts repositories describe $Repo --location $RegionRepo --project $Project).Code -ne 0) {
            Write-Host "[setup] Creando repo Artifact Registry '$Repo'..." -ForegroundColor Cyan
            & gcloud artifacts repositories create $Repo --repository-format=docker --location $RegionRepo --project $Project --description="Docker KIOSKO Backend"
            if ($LASTEXITCODE -ne 0) { Fail "No se pudo crear el repo '$Repo'." }
        }

        # El build y el runtime corren como la compute SA (NO la @cloudbuild legacy).
        foreach ($role in @("roles/cloudbuild.builds.builder", "roles/artifactregistry.writer", "roles/logging.logWriter", "roles/secretmanager.secretAccessor")) {
            $b = Invoke-Gcloud projects add-iam-policy-binding $Project --member="serviceAccount:$sa" --role=$role --condition=None --quiet
            if ($b.Code -ne 0) { Fail "No se pudo dar $role a $sa`n$($b.Out)" }
            Write-Host ("[setup] {0} -> {1}" -f $role, $sa) -ForegroundColor Green
        }
    }

    # ---------------------------------------------------------------- 3. Secretos
    Write-Host "`n[1/3] Subiendo secretos..." -ForegroundColor Cyan
    $existentes = @((& gcloud secrets list --project $Project --format="value(name)" 2>$null) | ForEach-Object { ($_ -split '/')[-1].Trim() })
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $nuevo  = Join-Path $tmpDir "nuevo.txt"
    $actual = Join-Path $tmpDir "actual.txt"
    foreach ($k in $secretos.Keys) {
        $name = $secretos[$k]
        $valor = $vals[$k]
        if ($k -eq "SECRET_KEY" -and $skEjemplo) {
            if ($existentes -contains $name) {
                Write-Host ("  =       {0,-28} se conserva la clave de produccion existente" -f $k) -ForegroundColor DarkGray
                continue
            }
            $valor = New-ClaveAleatoria
        }
        # UTF-8 sin BOM y SIN salto de linea final (un \n rompe DATABASE_URL, ver DEPLOY.md)
        [System.IO.File]::WriteAllText($nuevo, $valor, $utf8)

        if ($existentes -notcontains $name) {
            $c = Invoke-Gcloud secrets create $name --replication-policy=automatic --project $Project
            if ($c.Code -ne 0) { Fail "No se pudo crear el secreto $name`n$($c.Out)" }
        } else {
            # Si el valor no cambio, no se agrega version (cada version activa cuesta).
            if (Test-Path $actual) { Remove-Item $actual -Force }
            $a = Invoke-Gcloud secrets versions access latest --secret $name --project $Project --out-file $actual
            if ($a.Code -eq 0 -and (Test-Path $actual) -and
                ([Convert]::ToBase64String([System.IO.File]::ReadAllBytes($actual)) -eq [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($nuevo)))) {
                Write-Host ("  =       {0,-28} sin cambios" -f $k) -ForegroundColor DarkGray
                continue
            }
        }
        $add = Invoke-Gcloud secrets versions add $name --data-file=$nuevo --project $Project
        if ($add.Code -ne 0) { Fail "No se pudo subir $k -> $name`n$($add.Out)" }
        Write-Host ("  OK      {0,-28} -> {1} (nueva version)" -f $k, $name) -ForegroundColor Green
    }
    Remove-Item $nuevo, $actual -Force -ErrorAction SilentlyContinue

    # ---------------------------------------------------------------- 4. Build
    Write-Host "`n[2/3] Construyendo imagen $image ..." -ForegroundColor Cyan
    & gcloud builds submit --tag $image --project $Project .
    if ($LASTEXITCODE -ne 0) { Fail "Fallo el build. Si es un proyecto GCP nuevo, corre con -Setup." }

    # ---------------------------------------------------------------- 5. Deploy
    # YAML con comillas simples: las comas de CORS y la "\" del regex pasan literal.
    $yaml = Join-Path $tmpDir "env.yaml"
    $lineas = foreach ($k in $envVars.Keys) { "{0}: '{1}'" -f $k, ($envVars[$k] -replace "'", "''") }
    [System.IO.File]::WriteAllText($yaml, ($lineas -join "`n") + "`n", $utf8)
    $pares = ($secretos.GetEnumerator() | ForEach-Object { "{0}={1}:latest" -f $_.Key, $_.Value }) -join ","

    Write-Host "`n[3/3] Desplegando en Cloud Run..." -ForegroundColor Cyan
    # --env-vars-file y --set-secrets REEMPLAZAN todo: el servicio queda igual al .env.
    # La etiqueta marca el servicio como "de este script" (ver chequeo AJENO arriba).
    $escala = @()
    if ($MinInstancias -ge 0) { $escala += "--min-instances=$MinInstancias" }
    if ($MaxInstancias -ge 0) { $escala += "--max-instances=$MaxInstancias" }
    & gcloud run deploy $Service --image $image --region $Region --project $Project `
        --allow-unauthenticated --env-vars-file $yaml "--set-secrets=$pares" `
        "--update-labels=$LABEL=$LABEL_VALOR" @escala --quiet
    if ($LASTEXITCODE -ne 0) { Fail "Fallo el deploy. Revisa los logs: gcloud run services logs read $Service --region $Region --project $Project" }

    # ---------------------------------------------------------------- Verificacion
    Write-Host "`nVerificando $urlBack/health ..." -ForegroundColor Cyan
    try {
        $h = Invoke-RestMethod -Uri "$urlBack/health" -TimeoutSec 30
        Write-Host ("  /health -> {0}" -f ($h | ConvertTo-Json -Compress)) -ForegroundColor Green
    } catch {
        Write-Host "  /health no respondio: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    Write-Host "`nListo. Backend: $urlBack" -ForegroundColor Green
    Write-Host "Pendiente (una sola vez):" -ForegroundColor Yellow
    Write-Host "  - En Vercel: VITE_API_URL=$urlBack y redeploy del front." -ForegroundColor Yellow
    Write-Host "  - En tu cliente OAuth de Google, redirect URI autorizada: $urlBack/drive/callback" -ForegroundColor Yellow
}
finally {
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
    Pop-Location
}
