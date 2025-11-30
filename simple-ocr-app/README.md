# Simple OCR App

A simple web app for batch PDF-to-Markdown conversion using olmOCR via Parasail API.

**No document limits. No authentication required. Just drag, drop, and convert.**

---

## Deploy in 2 Minutes (No CLI Required)

### Option 1: Render.com (Easiest)

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New** → **Web Service**
3. Connect your GitHub and select this repo
4. Set:
   - **Root Directory**: `simple-ocr-app`
   - **Environment**: Docker
5. Add environment variable:
   - `PARASAIL_API_KEY` = `your-parasail-api-key`
6. Click **Deploy**

You'll get a URL like `https://olmocr-simple.onrender.com`

---

### Option 2: Railway.app

1. Go to [railway.app](https://railway.app) and sign up
2. Click **New Project** → **Deploy from GitHub**
3. Select this repo
4. Add variable: `PARASAIL_API_KEY`
5. Deploy!

---

### Option 3: Google Cloud Run (via GitHub Actions)

If you prefer GCP, push to this repo and it auto-deploys:

1. In GitHub repo settings, add these secrets:
   - `GCP_PROJECT_ID`: Your GCP project ID
   - `GCP_SA_KEY`: Service account JSON key (with Cloud Run Admin role)
   - `PARASAIL_API_KEY`: Your Parasail API key

2. Push any change to `simple-ocr-app/` folder
3. GitHub Actions deploys automatically

---

## Local Development

```bash
cd simple-ocr-app
pip install -r requirements.txt
export PARASAIL_API_KEY="your-key"
python app.py
```

Open http://localhost:8080

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PARASAIL_API_KEY` | Yes | Your Parasail API key for olmOCR access |
| `PORT` | No | Server port (default: 8080) |

---

## Get a Parasail API Key

1. Go to [parasail.io](https://parasail.io)
2. Sign up and create an API key
3. Use model: `allenai/olmOCR-2-7B-1025`
