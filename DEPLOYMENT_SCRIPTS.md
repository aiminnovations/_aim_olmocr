# Deployment Scripts Guide

## Overview

This guide explains which deployment scripts to use for different scenarios.

## 🔧 Active Deployment Scripts

### 1. Simple OCR App Deployment (Recommended for Most Users)

**File:** [`simple-ocr-app/deploy.sh`](simple-ocr-app/deploy.sh)

**Purpose:** Deploy standalone OCR app to Google Cloud Run

**What it deploys:**
- Single Cloud Run service with FastAPI backend
- Optional Firestore integration for job persistence
- Uses Parasail API for OCR processing

**Usage:**
```bash
cd simple-ocr-app
./deploy.sh
```

**Prerequisites:**
- Google Cloud account with billing enabled
- Parasail API key ([get one here](https://parasail.io))
- gcloud CLI installed and authenticated

**Configuration:**
Set these environment variables before deploying:
```bash
export PARASAIL_API_KEY="your-key-here"
export GCP_PROJECT_ID="your-project-id"
```

Or edit the `.env` file directly (don't commit it!)

**When to use:**
- Personal projects
- Proof of concept
- Small team usage (<100 PDFs/day)
- No multi-user authentication needed

---

### 2. Full Stack Cloud Run Deployment (Production)

**File:** [`gcp-deployment/cloudrun/deploy.sh`](gcp-deployment/cloudrun/deploy.sh)

**Purpose:** Deploy complete microservices stack to Google Cloud

**What it deploys:**
- **Frontend:** React app (Cloud Run)
- **Backend:** FastAPI with authentication (Cloud Run)
- **Worker:** Background OCR processor (Cloud Run with GPU support)
- **Infrastructure:** Pub/Sub topics, Secret Manager, Firestore

**Usage:**
```bash
cd gcp-deployment/cloudrun
./deploy.sh
```

**Prerequisites:**
- All services enabled in GCP:
  - Cloud Run
  - Cloud Storage
  - Firestore
  - Pub/Sub
  - Secret Manager
  - Container Registry
- Firebase project configured
- gcloud CLI authenticated

**Configuration Files:**
- `gcp-frontend/.env` - Frontend Firebase config
- `gcp-backend/.env` - Backend service account
- `gcp-worker/.env` - Worker configuration

**When to use:**
- Production deployments
- Multi-user applications
- Need authentication/authorization
- High volume processing (>1000 PDFs/day)
- Team collaboration features

---

### 3. GCP Infrastructure Setup

**File:** [`gcp-deployment/scripts/setup-gcp.sh`](gcp-deployment/scripts/setup-gcp.sh)

**Purpose:** One-time setup of GCP project infrastructure

**What it does:**
- Enables required Google Cloud APIs
- Creates GCS buckets
- Creates Firestore database
- Sets up Pub/Sub topics and subscriptions
- Configures IAM permissions
- Creates service accounts

**Usage:**
```bash
cd gcp-deployment/scripts
./setup-gcp.sh YOUR_PROJECT_ID
```

**When to use:**
- First time deploying to a new GCP project
- Setting up development/staging environments
- Recreating infrastructure after major changes

---

### 4. GitHub Actions Automated Deployment

**File:** [`.github/workflows/deploy-simple-ocr.yml`](.github/workflows/deploy-simple-ocr.yml)

**Purpose:** Automated deployment on code changes

**What it does:**
- Runs on push to `simple-ocr-app/` directory
- Builds Docker image
- Deploys to Cloud Run
- Runs smoke tests

**Setup:**
1. Add GitHub secrets:
   - `GCP_PROJECT_ID`
   - `GCP_SA_KEY` (service account key)
   - `PARASAIL_API_KEY`

2. Push changes:
```bash
git push origin main
```

**When to use:**
- CI/CD pipeline
- Automatic deployments from main branch
- Rolling updates without manual intervention

---

## 📋 Deployment Decision Matrix

| Scenario | Recommended Script | Complexity | Cost |
|----------|-------------------|------------|------|
| Personal project, testing | `simple-ocr-app/deploy.sh` | ⭐ Low | $ Low |
| Small team, no auth | `simple-ocr-app/deploy.sh` | ⭐ Low | $ Low |
| Production, multi-user | `gcp-deployment/cloudrun/deploy.sh` | ⭐⭐⭐ High | $$$ Higher |
| CI/CD pipeline | GitHub Actions | ⭐⭐ Medium | $$ Medium |
| New GCP project setup | `setup-gcp.sh` | ⭐⭐ Medium | N/A |

---

## 🗑️ Deprecated/Removed Scripts

### ~~Root deploy.sh~~ (DELETED)

**Status:** ❌ Removed during cleanup

**Reason:** Duplicate functionality with `gcp-deployment/cloudrun/deploy.sh`

**Migration:** Use `gcp-deployment/cloudrun/deploy.sh` instead

**What changed:**
- Moved from root to `gcp-deployment/cloudrun/`
- Better organized with related deployment files
- Improved error handling
- Supports both GPU and Parasail API modes

---

## 🔐 Security Best Practices

### Never Commit Secrets

Add to `.gitignore`:
```gitignore
.env
*.key
credentials.json
service-account.json
```

### Use Secret Manager

For production deployments:
```bash
# Store secrets in Google Secret Manager
gcloud secrets create PARASAIL_API_KEY --data-file=-
# (then paste your key and press Ctrl+D)

# Reference in Cloud Run deployment
gcloud run services update olmocr-backend \
  --update-secrets=PARASAIL_API_KEY=PARASAIL_API_KEY:latest
```

### Rotate API Keys

Set reminders to rotate:
- Parasail API keys (every 90 days)
- GCP service account keys (every 90 days)
- Firebase credentials (when team members leave)

---

## 🚀 Deployment Workflow (Recommended)

### For Simple Projects

```bash
# 1. Set up environment
cd simple-ocr-app
cp .env.example .env
# Edit .env with your Parasail API key

# 2. Test locally
python app.py
# Visit http://localhost:8080

# 3. Deploy to Cloud Run
./deploy.sh

# 4. Test deployment
# Visit the URL provided by Cloud Run
```

### For Production Projects

```bash
# 1. One-time GCP setup
cd gcp-deployment/scripts
./setup-gcp.sh YOUR_PROJECT_ID

# 2. Configure services
cd ../..
# Edit gcp-frontend/.env
# Edit gcp-backend/.env
# Edit gcp-worker/.env

# 3. Build and test locally
docker-compose up

# 4. Deploy to Cloud Run
cd gcp-deployment/cloudrun
./deploy.sh

# 5. Verify deployment
gcloud run services list
```

---

## 📞 Troubleshooting

### Deployment Fails: "Permission Denied"

**Solution:**
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
```

### Deployment Fails: "API Not Enabled"

**Solution:**
```bash
cd gcp-deployment/scripts
./setup-gcp.sh YOUR_PROJECT_ID
```

### Cloud Run Service Won't Start

**Check logs:**
```bash
gcloud run services logs read olmocr-backend --limit=50
```

**Common issues:**
- Missing environment variables
- Invalid Firebase credentials
- Port mismatch (should be 8080)

### Frontend Can't Connect to Backend

**Check CORS configuration** in `gcp-backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-url.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Firebase Setup Guide](https://firebase.google.com/docs/web/setup)
- [gcloud CLI Reference](https://cloud.google.com/sdk/gcloud/reference)
- [Parasail API Documentation](https://parasail.io/docs)

---

## ✅ Pre-Deployment Checklist

Before deploying:

- [ ] `.env` files configured (not committed!)
- [ ] API keys obtained and stored securely
- [ ] GCP project billing enabled
- [ ] Required APIs enabled (run `setup-gcp.sh`)
- [ ] Service account keys created
- [ ] Firebase project configured (for full stack)
- [ ] Tests passing (`./run_all_tests.sh`)
- [ ] Docker images build successfully
- [ ] Local deployment tested (`docker-compose up`)

---

For questions or issues, open an issue on GitHub or consult the main [README.md](README.md).
