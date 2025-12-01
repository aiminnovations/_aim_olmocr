# olmOCR Windows PowerShell Installer
# Run: .\setup.ps1
# Or right-click and "Run with PowerShell"

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "olmOCR Automated Installer for Windows" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$env:GCP_PROJECT_ID = "juniper-core"
$env:PARASAIL_API_KEY = "psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP"
$env:GCP_REGION = "us-central1"

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check gcloud
try {
    $gcloudVersion = gcloud --version 2>&1 | Select-Object -First 1
    Write-Host "[OK] Google Cloud SDK: $gcloudVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Google Cloud SDK not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing Google Cloud SDK..." -ForegroundColor Yellow

    # Download and install gcloud
    $installerUrl = "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe"
    $installerPath = "$env:TEMP\GoogleCloudSDKInstaller.exe"

    Write-Host "Downloading Google Cloud SDK installer..."
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

    Write-Host "Running installer (please complete the installation)..."
    Start-Process -FilePath $installerPath -Wait

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    # Check again
    try {
        gcloud --version | Out-Null
        Write-Host "[OK] Google Cloud SDK installed" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Google Cloud SDK installation failed" -ForegroundColor Red
        Write-Host "Please install manually from https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Check Firebase CLI (optional)
try {
    $firebaseVersion = firebase --version 2>&1
    Write-Host "[OK] Firebase CLI: $firebaseVersion" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Firebase CLI not found (will use gcloud fallback)" -ForegroundColor Yellow

    # Try to install via npm if available
    try {
        npm --version | Out-Null
        Write-Host "Installing Firebase CLI via npm..."
        npm install -g firebase-tools
    } catch {
        Write-Host "Firebase CLI will be configured via gcloud" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Starting installation..." -ForegroundColor Cyan
Write-Host ""

# Run the Python installer
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "install.py"

try {
    python $pythonScript

    if ($LASTEXITCODE -ne 0) {
        throw "Installation failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "Installation Complete!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "[ERROR] Installation failed: $_" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"
