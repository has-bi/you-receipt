#!/usr/bin/env bash
set -euo pipefail

echo "=== Updating GCP Secrets from .env file ==="
echo

# Load .env file
if [ ! -f .env ]; then
  echo "Error: .env file not found!"
  exit 1
fi

# Source .env file
set -a
source .env
set +a

PROJECT_ID=${PROJECT_ID:-youvit-ai-chatbot}

echo "Project: $PROJECT_ID"
echo

# Function to update secret (add new version)
update_secret() {
  local secret_name=$1
  local secret_value=$2

  if [ -z "$secret_value" ]; then
    echo "⚠ Skipping $secret_name (value not set in .env)"
    return
  fi

  echo "Updating secret: $secret_name"
  if printf "%s" "$secret_value" | gcloud secrets versions add "$secret_name" \
    --project="$PROJECT_ID" \
    --data-file=- 2>/dev/null; then
    echo "✓ $secret_name updated"
  else
    echo "✗ Failed to update $secret_name (may not exist yet)"
  fi
  echo
}

# Update all secrets
echo "Updating secrets..."
echo

update_secret "mistral-api-key" "${MISTRAL_API_KEY:-}"
update_secret "openai-api-key" "${OPENAI_API_KEY:-}"
update_secret "master-sheet-id" "${MASTER_SHEET_ID:-}"
update_secret "output-sheet-id" "${OUTPUT_SHEET_ID:-}"
update_secret "gcs-bucket-name" "${GCS_BUCKET_NAME:-}"
update_secret "gcs-project-id" "${GCS_PROJECT_ID:-}"

echo
echo "✓ Secrets update attempted!"
echo
echo "Now try deploying: ./deploy.sh"
