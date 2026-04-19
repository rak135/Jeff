param(
    [string]$Dsn = $env:JEFF_TEST_POSTGRES_DSN
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Expected venv Python at $pythonExe"
}

if ([string]::IsNullOrWhiteSpace($Dsn)) {
    throw "Set JEFF_TEST_POSTGRES_DSN or pass -Dsn."
}

Write-Host "Repo root: $repoRoot"
Write-Host "Python: $pythonExe"
Write-Host "DSN host/db check: provided"

$commands = "psql", "pg_config", "postgres", "pg_ctl"
foreach ($name in $commands) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        Write-Warning "$name not found on PATH"
    }
    else {
        Write-Host ("{0}: {1}" -f $name, $cmd.Source)
    }
}

$pgServices = Get-Service | Where-Object {
    $_.Name -match "postgres" -or $_.DisplayName -match "PostgreSQL"
}

if ($pgServices) {
    $pgServices | ForEach-Object {
        Write-Host ("Service: {0} [{1}]" -f $_.Name, $_.Status)
    }
}
else {
    Write-Warning "No PostgreSQL Windows service found."
}

$env:JEFF_TEST_POSTGRES_DSN = $Dsn

$pythonCheck = @'
import os
import sys

try:
    import psycopg2
except Exception as exc:  # pragma: no cover - script path
    print(f"psycopg2 import failed: {exc}", file=sys.stderr)
    raise

dsn = os.environ["JEFF_TEST_POSTGRES_DSN"]
conn = psycopg2.connect(dsn)
try:
    cur = conn.cursor()
    cur.execute("select current_user, current_database()")
    user, db = cur.fetchone()
    print(f"connected_user={user}")
    print(f"connected_db={db}")

    cur.execute("show extension_control_path")
    print(f"extension_control_path={cur.fetchone()[0]}")

    cur.execute("show dynamic_library_path")
    print(f"dynamic_library_path={cur.fetchone()[0]}")

    cur.execute("select extversion from pg_extension where extname = 'vector'")
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("pgvector extension is not enabled in the target database")
    print(f"vector_extversion={row[0]}")

    cur.execute("select '[1,2,3]'::vector")
    print(f"vector_cast={cur.fetchone()[0]}")
finally:
    conn.close()
'@

$pythonCheck | & $pythonExe -

if ($LASTEXITCODE -ne 0) {
    throw "Preflight failed."
}

Write-Host "Preflight passed."
