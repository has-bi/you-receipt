# Quick Reference Guide

## Local Development

```bash
# Setup (first time)
cp .env.example .env
# Edit .env with your credentials
# Download credentials.json from GCP

# Run with Docker
docker compose up --build

# Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Access app
open http://localhost:8000
```

## Cloud Deployment

```bash
# Build image
gcloud builds submit --tag asia-southeast1-docker.pkg.dev/youvit-ai-chatbot/youvit/pharmacy-stock-ocr:latest

# Deploy
./deploy.sh

# View logs (via console)
# https://console.cloud.google.com/run/detail/asia-southeast1/pharmacy-stock-ocr/logs?project=youvit-ai-chatbot
```

## File Structure

```
youvit-receipt/
├── .env                        # Local environment variables (not in git)
├── .env.example                # Template for .env
├── credentials.json            # GCP service account (not in git)
├── deploy.sh                   # Deploy to Cloud Run
├── create_secrets.sh           # Create GCP secrets from .env
├── update_secrets.sh           # Update existing secrets
├── verify_deployment.sh        # Check deployment prerequisites
│
├── DEPLOYMENT_SUMMARY.md       # Full deployment guide & troubleshooting
├── GCP_DEPLOYMENT.md           # Detailed GCP deployment docs
├── LOCAL_SETUP.md              # Local development setup
├── QUICK_REFERENCE.md          # This file
│
├── main.py                     # FastAPI application
├── Dockerfile                  # Production container
├── docker-compose.yml          # Local development
├── pyproject.toml             # Python dependencies
│
├── models/                     # Pydantic schemas
├── services/                   # Business logic
├── templates/                  # HTML templates
└── static/                     # Static files & uploads
```

## Key Environment Variables

### Local (.env file)
```bash
MISTRAL_API_KEY=your_key
OPENAI_API_KEY=your_key
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
GCS_BUCKET_NAME=pharmacy-stock-photos
GCS_PROJECT_ID=youvit-ai-chatbot
MASTER_SHEET_ID=your_sheet_id
OUTPUT_SHEET_ID=your_sheet_id
```

### Cloud Run (via secrets)
- No credentials file needed!
- All values loaded from Secret Manager
- Uses Application Default Credentials (ADC)

## Common Commands

```bash
# View git status
git status

# Check docker images
docker images | grep pharmacy

# Test local endpoint
curl http://localhost:8000/health

# Check GCS bucket
gsutil ls gs://pharmacy-stock-photos/

# View Cloud Run services
gcloud run services list --region=asia-southeast1
```

## Troubleshooting Quick Fixes

### gcloud protobuf errors (WSL)
Use Cloud Console instead of CLI, or reinstall Linux gcloud

### Container won't start
Check secrets exist and service account has secretAccessor role

### Google Sheets permission denied
Share sheets with service account email

### GCS upload fails
Verify bucket exists and service account has storage.objectAdmin role

### Port already in use (local)
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn main:app --port 8001
```

## Important URLs

- **Cloud Console**: https://console.cloud.google.com
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager?project=youvit-ai-chatbot
- **Cloud Run**: https://console.cloud.google.com/run?project=youvit-ai-chatbot
- **IAM**: https://console.cloud.google.com/iam-admin/iam?project=youvit-ai-chatbot
- **Logs**: https://console.cloud.google.com/logs?project=youvit-ai-chatbot

## Cost Monitoring

```bash
# Set budget alert (via console)
# Billing → Budgets & alerts → Create budget

# View current costs
# https://console.cloud.google.com/billing
```

## Authentication Summary

| Environment | Method | Credential |
|-------------|--------|------------|
| Local | credentials.json | Service account key file |
| Cloud Run | ADC | Service account (no file needed) |

The app automatically detects which environment it's running in!
