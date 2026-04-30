param(
    [string]$Environment = "dev",
    [string]$Region = "eu-west-2"
)

$ErrorActionPreference = "Stop"

$ScriptRoot = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ScriptRoot)) {
    $ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if ([string]::IsNullOrWhiteSpace($ScriptRoot)) {
    $ScriptRoot = Split-Path -Parent $PSCommandPath
}

function Get-TerraformExe {
    $cmd = Get-Command terraform -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Path }
    $homeRoot = if (-not [string]::IsNullOrWhiteSpace($env:HOME)) { $env:HOME } else { $env:USERPROFILE }
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $candidates += (Join-Path $env:LOCALAPPDATA "Programs\terraform\terraform.exe")
    }
    $candidates += @(
        "C:\Program Files\Terraform\terraform.exe",
        (Join-Path $homeRoot ".local/bin/terraform"),
        "/usr/local/bin/terraform"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    return $null
}

$ProjectRoot = Split-Path -Parent $ScriptRoot
$awsAccountId = (aws sts get-caller-identity '--query' 'Account' '--output' 'text').Trim()
if ([string]::IsNullOrWhiteSpace($awsAccountId)) {
    throw "Could not read AWS account id (aws sts get-caller-identity)."
}

$awsRegion = $Region.Trim()
if ([string]::IsNullOrWhiteSpace($awsRegion)) {
    $awsRegion = if (-not [string]::IsNullOrWhiteSpace($env:DEFAULT_AWS_REGION)) {
        $env:DEFAULT_AWS_REGION.Trim()
    } elseif (-not [string]::IsNullOrWhiteSpace($env:AWS_DEFAULT_REGION)) {
        $env:AWS_DEFAULT_REGION.Trim()
    } else {
        "eu-west-2"
    }
}

$tf = Get-TerraformExe
if (-not $tf) {
    throw "Terraform not found on PATH or common install locations."
}

& (Join-Path $ScriptRoot "ensure-terraform-backend.ps1") -AccountId $awsAccountId -Region $awsRegion

Set-Location (Join-Path $ProjectRoot "terraform")

$initArgs = @(
    'init', '-reconfigure', '-input=false', '-force-copy',
    "-backend-config=bucket=meridian-terraform-state-$awsAccountId",
    "-backend-config=key=$Environment/terraform.tfstate",
    "-backend-config=region=$awsRegion",
    '-backend-config=use_lockfile=true',
    '-backend-config=encrypt=true'
)
Write-Host "Running: terraform init -reconfigure -input=false -force-copy (backend S3, key $Environment/terraform.tfstate, region $awsRegion)" -ForegroundColor Cyan
& $tf @initArgs
