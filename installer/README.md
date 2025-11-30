# olmOCR One-Click Installer

Fully automated installation of olmOCR on Google Cloud Platform.

## Quick Start

### Windows

**Option 1: Double-click**
1. Double-click `setup.bat`
2. Follow the prompts

**Option 2: PowerShell (recommended)**
1. Right-click `setup.ps1` → "Run with PowerShell"
2. Or open PowerShell and run: `.\setup.ps1`

### Mac / Linux

```bash
./setup.sh
```

Or:
```bash
bash setup.sh
```

## What Gets Installed

The installer automatically:

1. ✅ Checks and installs prerequisites (gcloud, Firebase CLI)
2. ✅ Authenticates with Google Cloud
3. ✅ Enables required GCP APIs
4. ✅ Creates Cloud Storage bucket
5. ✅ Creates Firestore database
6. ✅ Creates Pub/Sub topic
7. ✅ Stores Parasail API key securely
8. ✅ Sets up Firebase Authentication
9. ✅ Builds container images
10. ✅ Deploys to Cloud Run
11. ✅ Configures everything automatically

## Prerequisites

The installer will check for and help install:

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Google Cloud SDK** - [Download](https://cloud.google.com/sdk/docs/install)
- **Firebase CLI** (optional) - Installed automatically if npm is available

## Configuration

Default settings (can be changed during installation):

| Setting | Default Value |
|---------|--------------|
| GCP Project ID | `juniper-core` |
| Region | `us-central1` |
| Parasail API Key | Pre-configured |

To use custom settings, set environment variables before running:

```bash
export GCP_PROJECT_ID="your-project-id"
export PARASAIL_API_KEY="psk-your-key"
export GCP_REGION="us-west1"
./setup.sh
```

## Installation Time

- First-time setup: ~20-30 minutes
- Most time is spent building Docker images

## After Installation

Your olmOCR application will be live at:
- **Frontend**: `https://olmocr-frontend-xxxxx-uc.a.run.app`

A `DEPLOYMENT_INFO.txt` file is created with all URLs and configuration.

## Troubleshooting

### "gcloud not found"
Install Google Cloud SDK:
- Windows: Download from https://cloud.google.com/sdk/docs/install
- Mac: `brew install --cask google-cloud-sdk`
- Linux: `curl https://sdk.cloud.google.com | bash`

### "Permission denied"
Make sure you have Owner or Editor role on the GCP project.

### "Build failed"
Check Cloud Build logs:
```bash
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

### "Firebase setup failed"
The installer falls back to gcloud if Firebase CLI isn't available.
You may need to manually enable authentication providers in the Firebase Console.

## Manual Installation

If the automated installer doesn't work, see:
- `QUICKSTART.md` in the project root
- `docs/gcp-architecture/USER_GUIDE.md`

## Support

- Issues: https://github.com/aiminnovations/_aim_olmocr/issues
