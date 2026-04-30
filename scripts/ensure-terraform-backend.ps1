param(
    [Parameter(Mandatory = $true)]
    [string]$AccountId,

    [Parameter(Mandatory = $true)]
    [string]$Region
)

$ErrorActionPreference = "Stop"

function Invoke-Aws {
    param(
        [string[]]$CliArgs
    )

    Write-Host "Running: aws $($CliArgs -join ' ')" -ForegroundColor DarkGray

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    $output = & aws @CliArgs 2>&1
    $exitCode = $LASTEXITCODE

    $ErrorActionPreference = $prev

    if ($exitCode -ne 0) {
        Write-Host "----- AWS ERROR OUTPUT -----" -ForegroundColor Red
        $output | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        Write-Host "----------------------------" -ForegroundColor Red

        throw "AWS command failed (exit $exitCode)"
    }

    return $output
}
# ---- Validate Inputs ----
$AccountId = $AccountId.Trim()
if ([string]::IsNullOrWhiteSpace($AccountId)) {
    throw "AccountId is empty. Check AWS credentials."
}

$Region = $Region.Trim()
if ([string]::IsNullOrWhiteSpace($Region)) {
    throw "Region is empty."
}

$bucketName = "meridian-terraform-state-$AccountId"

Write-Host "Ensuring Terraform backend bucket: $bucketName ($Region)" -ForegroundColor Cyan

# ---- Check if bucket exists ----
aws s3api head-bucket --bucket $bucketName 2>$null
$bucketExists = ($LASTEXITCODE -eq 0)

if (-not $bucketExists) {

    Write-Host "Creating bucket..." -ForegroundColor Yellow

    if ($Region -eq "us-east-1") {
        Invoke-Aws @(
            's3api', 'create-bucket',
            '--bucket', $bucketName,
            '--region', $Region
        )
    }
    else {
        Invoke-Aws @(
            's3api', 'create-bucket',
            '--bucket', $bucketName,
            '--region', $Region,
            '--create-bucket-configuration', "LocationConstraint=$Region"
        )
    }

    Write-Host "Bucket created." -ForegroundColor Green
}
else {
    Write-Host "Bucket already exists." -ForegroundColor DarkGray
}

# ---- Enable Versioning ----
Write-Host "Enabling versioning..." -ForegroundColor Yellow

Invoke-Aws @(
    's3api', 'put-bucket-versioning',
    '--bucket', $bucketName,
    '--versioning-configuration', 'Status=Enabled'
)

# ---- Configure Encryption (FILE-BASED — SAFE) ----
Write-Host "Applying server-side encryption..." -ForegroundColor Yellow

$encFile = Join-Path $env:TEMP "s3-encryption.json"

$encJson = @{
    Rules = @(
        @{
            ApplyServerSideEncryptionByDefault = @{
                SSEAlgorithm = "AES256"
            }
        }
    )
} | ConvertTo-Json -Depth 5

[System.IO.File]::WriteAllText($encFile, $encJson)

# Debug (optional)
Write-Host "Encryption JSON:" -ForegroundColor Gray
Get-Content $encFile

Invoke-Aws @(
    's3api', 'put-bucket-encryption',
    '--bucket', $bucketName,
    '--server-side-encryption-configuration', "file://$encFile"
)

# ---- Block Public Access ----
Write-Host "Blocking public access..." -ForegroundColor Yellow

Invoke-Aws @(
    's3api', 'put-public-access-block',
    '--bucket', $bucketName,
    '--public-access-block-configuration',
    'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
)

Write-Host "Terraform backend bucket is ready." -ForegroundColor Green

# NOTE:
# Terraform S3 backend with use_lockfile stores locks in the bucket
# DynamoDB is NOT required.