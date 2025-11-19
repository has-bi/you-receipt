#!/usr/bin/env bash
set -euo pipefail

echo "Deploying pharmacy-stock-ocr to Cloud Run..."

SERVICE=${SERVICE:-pharmacy-stock-ocr}
REGION=${REGION:-asia-southeast1}
PROJECT_ID=${PROJECT_ID:-youvit-ai-chatbot}
SA_EMAIL=${SA_EMAIL:-youvit-runner@youvit-ai-chatbot.iam.gserviceaccount.com}
IMAGE=${IMAGE:-asia-southeast1-docker.pkg.dev/${PROJECT_ID}/youvit/${SERVICE}:latest}

cat <<CONFIG
Using configuration:
  SERVICE      = ${SERVICE}
  REGION       = ${REGION}
  PROJECT_ID   = ${PROJECT_ID}
  SERVICE ACCT = ${SA_EMAIL}
  IMAGE        = ${IMAGE}
CONFIG

gcloud config set project "${PROJECT_ID}" >/dev/null

gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --service-account "${SA_EMAIL}" \
  --cpu 1 \
  --memory 512Mi \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 600 \
  --allow-unauthenticated \
  --set-secrets MISTRAL_API_KEY=mistral-api-key:latest \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-secrets MASTER_SHEET_ID=master-sheet-id:latest \
  --set-secrets OUTPUT_SHEET_ID=output-sheet-id:latest \
  --set-secrets GCS_BUCKET_NAME=gcs-bucket-name:latest \
  --set-secrets GCS_PROJECT_ID=gcs-project-id:latest
