#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Setup Stratum AI on Railway via CLI
.DESCRIPTION
    Creates Railway project, services, databases, sets env vars, and deploys.
    Run this from the project root directory.
.EXAMPLE
    .\scripts\setup-railway.ps1
#>

param(
    [string]$ProjectName = "stratum-ai2",
    [switch]$DryRun,
    [switch]$SkipDeploy
)

$ErrorActionPreference = "Stop"

# ─── Colors ───────────────────────────────────────────────────────────────────
$G = "`e[32m"; $Y = "`e[33m"; $R = "`e[31m"; $C = "`e[36m"; $B = "`e[1m"; $X = "`e[0m"

function info($m)  { Write-Host "${C}[INFO]${X}  $m" }
function ok($m)    { Write-Host "${G}[OK]${X}    $m" }
function warn($m)  { Write-Host "${Y}[WARN]${X}  $m" }
function err($m)   { Write-Host "${R}[ERR]${X}   $m" }
function step($m)  { Write-Host "`n${B}$m${X}`n$( '=' * ($m.Length) )" }

# ─── Helpers ──────────────────────────────────────────────────────────────────
function Invoke-Railway($cmd, [switch]$IgnoreError) {
    if ($DryRun) {
        Write-Host "${Y}[DRY]${X}  railway $cmd"
        return $null
    }
    $full = "railway $cmd"
    try {
        $out = Invoke-Expression $full 2>&1
        if ($LASTEXITCODE -ne 0 -and -not $IgnoreError) {
            err "Command failed: railway $cmd"
            err $out
            throw "Railway command failed"
        }
        return $out
    } catch {
        if (-not $IgnoreError) { throw }
        return $null
    }
}

function New-Secret($len = 32) {
    $bytes = [byte[]]::new($len)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return ($bytes | ForEach-Object { "{0:x2}" -f $_ }) -join ''
}

function Get-GitRemoteUrl {
    $remote = git remote get-url origin 2>$null
    if ($remote -match "github\.com[:/]([^/]+)/([^/]+?)(\.git)?$") {
        return "$($matches[1])/$($matches[2])"
    }
    return $null
}

# ─── 1. Prerequisites ─────────────────────────────────────────────────────────
step "1. Prerequisites"

info "Checking Railway CLI..."
try {
    $cliVer = railway --version 2>$null
    ok "Railway CLI found: $cliVer"
} catch {
    err "Railway CLI not found. Install: npm i -g @railway/cli"
    exit 1
}

info "Checking login..."
try {
    $userJson = railway whoami --json 2>$null | ConvertFrom-Json -ErrorAction Stop
    ok "Logged in as $($userJson.name) ($($userJson.email))"
} catch {
    err "Not logged in. Run: railway login"
    exit 1
}

info "Checking project root..."
if (-not (Test-Path "backend/Dockerfile") -or -not (Test-Path "frontend/Dockerfile")) {
    err "Not in project root. Run this from the Stratum AI repo root."
    exit 1
}
ok "Project root confirmed"

$repo = Get-GitRemoteUrl
if ($repo) { ok "GitHub repo: $repo" } else { warn "Could not detect GitHub repo URL" }

# ─── 2. Project ───────────────────────────────────────────────────────────────
step "2. Railway Project"

if (Test-Path ".railway") {
    warn ".railway/ already exists — project is linked"
    $projectJson = Invoke-Railway "status --json"
    ok "Using existing project"
} else {
    info "Creating new Railway project..."
    Invoke-Railway "init --name $ProjectName"
    ok "Project created"
}

# ─── 3. Services ──────────────────────────────────────────────────────────────
step "3. Services"

$services = Invoke-Railway "service status --json" -IgnoreError | ConvertFrom-Json -ErrorAction SilentlyContinue
$hasBackend = $services | Where-Object { $_.name -eq "backend" }
$hasFrontend = $services | Where-Object { $_.name -eq "frontend" }

if (-not $hasBackend) {
    info "Creating backend service..."
    Invoke-Railway "add --service backend"
    ok "Backend service created"
} else {
    ok "Backend service already exists"
}

if (-not $hasFrontend) {
    info "Creating frontend service..."
    Invoke-Railway "add --service frontend"
    ok "Frontend service created"
} else {
    ok "Frontend service already exists"
}

# ─── 4. Domains ───────────────────────────────────────────────────────────────
step "4. Domains"

info "Generating backend domain..."
$backendDomainOut = Invoke-Railway "domain --service backend" -IgnoreError
if ($backendDomainOut -match "([a-z0-9\-]+\.up\.railway\.app)") {
    $backendDomain = $matches[1]
    $backendUrl = "https://$backendDomain/api/v1"
    ok "Backend domain: $backendDomain"
} else {
    warn "Could not auto-detect backend domain. Will use placeholder."
    $backendDomain = "YOUR_BACKEND_DOMAIN.up.railway.app"
    $backendUrl = "https://$backendDomain/api/v1"
}

info "Generating frontend domain..."
$frontendDomainOut = Invoke-Railway "domain --service frontend" -IgnoreError
if ($frontendDomainOut -match "([a-z0-9\-]+\.up\.railway\.app)") {
    $frontendDomain = $matches[1]
    $frontendUrl = "https://$frontendDomain"
    ok "Frontend domain: $frontendDomain"
} else {
    warn "Could not auto-detect frontend domain. Will use placeholder."
    $frontendDomain = "YOUR_FRONTEND_DOMAIN.up.railway.app"
    $frontendUrl = "https://$frontendDomain"
}

# ─── 5. Databases ─────────────────────────────────────────────────────────────
step "5. Databases"

info "Adding PostgreSQL..."
Invoke-Railway "add --database postgres --service backend" -IgnoreError
ok "PostgreSQL added (linked to backend)"

info "Adding Redis..."
Invoke-Railway "add --database redis --service backend" -IgnoreError
ok "Redis added (linked to backend)"

# ─── 6. Secrets ───────────────────────────────────────────────────────────────
step "6. Secrets"

$secretKey     = New-Secret 32
$jwtSecret     = New-Secret 32
$piiKey        = New-Secret 32
ok "Secrets generated"

# ─── 7. Backend Variables ─────────────────────────────────────────────────────
step "7. Backend Environment Variables"

$backendVars = @{
    "APP_ENV"              = "production"
    "DEBUG"                = "false"
    "SECRET_KEY"           = $secretKey
    "JWT_SECRET_KEY"       = $jwtSecret
    "PII_ENCRYPTION_KEY"   = $piiKey
    "LOG_LEVEL"            = "INFO"
    "LOG_FORMAT"           = "json"
    "CORS_ORIGINS"         = $frontendUrl
    "FRONTEND_URL"         = $frontendUrl
    "ENABLE_WHATSAPP"      = "false"
    "USE_MOCK_AD_DATA"     = "true"
    "MARKET_INTEL_PROVIDER"= "mock"
}

foreach ($kv in $backendVars.GetEnumerator()) {
    info "Setting $($kv.Key)..."
    Invoke-Railway "variable set --service backend --skip-deploys `"$($kv.Key)=$($kv.Value)`""
}
ok "Backend variables set"

# ─── 8. Frontend Variables ────────────────────────────────────────────────────
step "8. Frontend Environment Variables"

$frontendVars = @{
    "VITE_API_URL"        = $backendUrl
    "VITE_WS_URL"         = "wss://$backendDomain"
    "VITE_DEFAULT_LOCALE" = "en"
}

foreach ($kv in $frontendVars.GetEnumerator()) {
    info "Setting $($kv.Key)..."
    Invoke-Railway "variable set --service frontend --skip-deploys `"$($kv.Key)=$($kv.Value)`""
}
ok "Frontend variables set"

# ─── 9. Deploy ────────────────────────────────────────────────────────────────
step "9. Deploy"

if ($SkipDeploy) {
    warn "Skipping deployment (--SkipDeploy)"
} else {
    info "Deploying backend..."
    Invoke-Railway "up backend/ --service backend --path-as-root"
    ok "Backend deployed"

    info "Deploying frontend..."
    Invoke-Railway "up frontend/ --service frontend --path-as-root"
    ok "Frontend deployed"
}

# ─── Summary ──────────────────────────────────────────────────────────────────
step "Summary"

Write-Host @"
${G}Setup complete!${X}

Project:     $ProjectName
Backend:     https://$backendDomain
Frontend:    https://$frontendDomain

Healthchecks:
  Backend:   https://$backendDomain/health
  Frontend:  https://$frontendDomain

Useful commands:
  railway logs --service backend
  railway logs --service frontend
  railway open

If domains were placeholders, update VITE_API_URL after backend deploys:
  railway variable set --service frontend VITE_API_URL=https://<REAL_DOMAIN>/api/v1
"@
