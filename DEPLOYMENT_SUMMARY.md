# Deployment Summary & Next Steps

## ✅ What We Fixed

### 1. **Removed sa-credentials Secret Dependency**
- **Problem**: The deployment was failing because it tried to mount a non-existent `sa-credentials` secret
- **Solution**: Updated `deploy.sh` to use Application Default Credentials (ADC) instead
- **Benefit**: Simpler, more secure, and follows Google Cloud best practices

### 2. **Dual Environment Support**
- **Local Development**: Uses `credentials.json` file with `GOOGLE_APPLICATION_CREDENTIALS` env var
- **Cloud Run**: Uses ADC automatically through the service account

### 3. **Documentation Updates**
- Added `LOCAL_SETUP.md` - Quick start guide for local development
- Updated `GCP_DEPLOYMENT.md` - Added authentication strategy section
- Updated `README.md` - Clarified local vs cloud setup
- Created `.env.example` - Template for environment variables

### 4. **Helper Scripts**
- `deploy.sh` - One-command deployment
- `create_secrets.sh` - Create secrets from .env
- `update_secrets.sh` - Update existing secrets
- `verify_deployment.sh` - Check deployment prerequisites

## 🔧 Current Status

**Docker Image**: ✅ Built and pushed to Artifact Registry
- Image: `asia-southeast1-docker.pkg.dev/youvit-ai-chatbot/youvit/pharmacy-stock-ocr:latest`

**Secrets**: ⚠️  Need to be created/verified (protobuf issue prevents automatic verification)

**Deployment**: ⚠️  Failed because secrets aren't accessible to the service

## 🚀 Next Steps (Choose One Option)

### Option A: Using Cloud Console (Recommended for WSL users)

1. **Create Secrets** (if not already done):
   - Go to: https://console.cloud.google.com/security/secret-manager?project=youvit-ai-chatbot
   - Click "CREATE SECRET" for each:
     - `mistral-api-key` → Your Mistral API key
     - `openai-api-key` → Your OpenAI API key
     - `master-sheet-id` → Google Sheets ID for master data
     - `output-sheet-id` → Google Sheets ID for output
     - `gcs-bucket-name` → `pharmacy-stock-photos`
     - `gcs-project-id` → `youvit-ai-chatbot`

2. **Grant Secret Access to Service Account**:
   - Go to: https://console.cloud.google.com/iam-admin/iam?project=youvit-ai-chatbot
   - Find: `youvit-runner@youvit-ai-chatbot.iam.gserviceaccount.com`
   - Click "Edit" → "Add Another Role"
   - Add: "Secret Manager Secret Accessor"
   - Save

3. **Deploy via Cloud Console**:
   - Go to: https://console.cloud.google.com/run?project=youvit-ai-chatbot
   - Click "CREATE SERVICE"
   - Container image URL: `asia-southeast1-docker.pkg.dev/youvit-ai-chatbot/youvit/pharmacy-stock-ocr:latest`
   - Service name: `pharmacy-stock-ocr`
   - Region: `asia-southeast1`
   - Service account: `youvit-runner@youvit-ai-chatbot.iam.gserviceaccount.com`
   - Under "Container, Variables & Secrets" → "Secrets" tab, add:
     - Reference each secret as an environment variable
   - Set CPU: 1, Memory: 512 MiB
   - Min instances: 0, Max instances: 2
   - Click "CREATE"

### Option B: Using Command Line (After fixing protobuf issue)

1. **Fix gcloud protobuf issue**:
   ```bash
   # Reinstall gcloud for Linux (not Windows)
   sudo apt-get remove google-cloud-cli
   sudo apt-get update && sudo apt-get install google-cloud-cli
   ```

2. **Create secrets from .env**:
   ```bash
   ./create_secrets.sh
   ```

3. **Grant permissions**:
   ```bash
   gcloud projects add-iam-policy-binding youvit-ai-chatbot \
     --member="serviceAccount:po-unified-runner@youvit-ai-chatbot.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

4. **Deploy**:
   ```bash
   ./deploy.sh
   ```

### Option C: Manual Secret Creation Commands

If you want to try creating secrets via command line:

```bash
# Use the create_secrets.sh script which reads from .env file
./create_secrets.sh
```

## 💰 Cost Optimization

Your current configuration is already optimized for minimal cost:

- **Min instances: 0** → Scale to zero when not in use (no idle cost)
- **CPU: 1, Memory: 512 MiB** → Minimum viable resources
- **Max instances: 2** → Prevents runaway costs
- **Region: asia-southeast1** → Consistent with your GCS bucket

**Expected costs** (assuming light usage):
- Cloud Run: ~$0-5/month (mostly free tier)
- Cloud Storage: ~$0.03/month (one 300MB image + photo uploads)
- Secret Manager: Free (6 versions per secret/month)
- Cloud Build: Free (120 build-minutes/day)

## 🔍 Troubleshooting

### If deployment still fails:

1. **Check logs** in Cloud Console:
   - https://console.cloud.google.com/run/detail/asia-southeast1/pharmacy-stock-ocr/logs?project=youvit-ai-chatbot

2. **Verify service account has all roles**:
   - `roles/secretmanager.secretAccessor`
   - `roles/storage.objectAdmin`
   - `roles/sheets.editor`

3. **Verify Google Sheets are shared** with:
   - `youvit-runner@youvit-ai-chatbot.iam.gserviceaccount.com`

4. **Check secrets exist**:
   - Go to Secret Manager in Cloud Console
   - Verify all 6 secrets have "latest" version

## 📝 Summary

✅ **Code is ready** - Supports both local and cloud environments seamlessly
✅ **Docker image is built** - Ready to deploy
✅ **Documentation is complete** - Clear setup instructions
⚠️  **Secrets need to be configured** - Use Cloud Console (recommended) or CLI
⚠️  **Service account permissions** - Grant secretAccessor role

Once secrets are configured with proper permissions, deployment should succeed!
