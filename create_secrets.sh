#!/usr/bin/env bash
set -euo pipefail

echo "=== Creating GCP Secrets from .env file ==="
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

# Function to create or update secret
create_or_update_secret() {
  local secret_name=$1
  local secret_value=$2

  if [ -z "$secret_value" ]; then
    echo "⚠ Skipping $secret_name (value not set in .env)"
    return
  fi

  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
    echo "Updating existing secret: $secret_name"
    printf "%s" "$secret_value" | gcloud secrets versions add "$secret_name" \
      --project="$PROJECT_ID" \
      --data-file=-
  else
    echo "Creating new secret: $secret_name"
    printf "%s" "$secret_value" | gcloud secrets create "$secret_name" \
      --project="$PROJECT_ID" \
      --replication-policy="automatic" \
      --data-file=-
  fi

  echo "✓ $secret_name"
  echo
}

# Create secrets
echo "Creating secrets..."
echo

create_or_update_secret "mistral-api-key" "${MISTRAL_API_KEY:-}"
create_or_update_secret "openai-api-key" "${OPENAI_API_KEY:-}"
create_or_update_secret "master-sheet-id" "${MASTER_SHEET_ID:-}"
create_or_update_secret "output-sheet-id" "${OUTPUT_SHEET_ID:-}"
create_or_update_secret "gcs-bucket-name" "${GCS_BUCKET_NAME:-}"
create_or_update_secret "gcs-project-id" "${GCS_PROJECT_ID:-}"

echo
echo "✓ All secrets created/updated successfully!"
echo
echo "Next steps:"
echo "1. Grant secret access to service account:"
echo "   gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "     --member=\"serviceAccount:po-unified-runner@${PROJECT_ID}.iam.gserviceaccount.com\" \\"
echo "     --role=\"roles/secretmanager.secretAccessor\""
echo
echo "2. Deploy: ./deploy.sh"
