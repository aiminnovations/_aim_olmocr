# olmOCR - Dead Simple Deployment

## Get Your App Running in 5 Minutes

### Step 1: Get Your API Key

1. Go to https://parasail.io
2. Sign up (it's free)
3. Copy your API key

### Step 2: Run ONE Command

```bash
./DEPLOY_NOW.sh
```

That's it. The script will ask you 2 questions:

1. **Your Parasail API key** (paste it)
2. **A project name** (anything you want, like "my-ocr-app")

Then it deploys everything automatically.

### Step 3: Use Your App

You'll get a URL like:

```
https://olmocr-abc123.run.app
```

Open it, drag a PDF, get Markdown. Done.

---

## What This Actually Does

The script automatically:

- ✅ Creates a Google Cloud project
- ✅ Enables required services
- ✅ Sets up storage
- ✅ Deploys the app
- ✅ Gives you a working URL

**Zero manual configuration required.**

---

## Cost

You only pay when you use it:

- Small PDFs (1-5 pages): ~$0.05
- Medium PDFs (10-20 pages): ~$0.20
- Large PDFs (50+ pages): ~$0.50

If you don't use it, it costs $0.

---

## Troubleshooting

**Script fails with "gcloud not found":**

```bash
# Install gcloud CLI
# Windows: https://cloud.google.com/sdk/docs/install#windows
# Mac: brew install google-cloud-sdk
# Linux: https://cloud.google.com/sdk/docs/install#linux
```

**Need to change your API key later:**

```bash
cd simple-ocr-app
nano .env  # Edit PARASAIL_API_KEY
cd ..
./DEPLOY_NOW.sh  # Re-deploy
```

**Want to delete everything:**

```bash
gcloud run services delete olmocr --region us-central1
gcloud projects delete YOUR-PROJECT-NAME
```

---

## That's All

No complex setup. No configuration files. No multiple scripts.

**Just run `./DEPLOY_NOW.sh` and you're done.**


Service URL: https://olmocr-500216852878.us-central1.run.app
