#!/usr/bin/env bash
set -euo pipefail

echo "=== Cloud Run Deployment Verification ==="
echo

PROJECT_ID=${PROJECT_ID:-youvit-ai-chatbot}
REGION=${REGION:-asia-southeast1}
SERVICE=${SERVICE:-pharmacy-stock-ocr}
SA_EMAIL=${SA_EMAIL:-po-unified-runner@youvit-ai-chatbot.iam.gserviceaccount.com}

echo "Checking required secrets..."
REQUIRED_SECRETS=(
  "mistral-api-key"
  "openai-api-key"
  "master-sheet-id"
  "output-sheet-id"
  "gcs-bucket-name"
  "gcs-project-id"
)

ALL_OK=true

for secret in "${REQUIRED_SECRETS[@]}"; do
  if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
    echo "✓ Secret '$secret' exists"
  else
    echo "✗ Secret '$secret' NOT FOUND"
    ALL_OK=false
  fi
done

echo
echo "Checking service account permissions..."

# Check if service account has secret accessor role
if gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SA_EMAIL} AND bindings.role:roles/secretmanager.secretAccessor" \
  --format="value(bindings.role)" | grep -q "secretAccessor"; then
  echo "✓ Service account has secretAccessor role"
else
  echo "✗ Service account missing secretAccessor role"
  echo "  Run: gcloud projects add-iam-policy-binding $PROJECT_ID \\"
  echo "    --member=\"serviceAccount:${SA_EMAIL}\" \\"
  echo "    --role=\"roles/secretmanager.secretAccessor\""
  ALL_OK=false
fi

echo
if [ "$ALL_OK" = true ]; then
  echo "✓ All checks passed! Deployment should work."
  echo
  echo "View logs at:"
  echo "https://console.cloud.google.com/run/detail/${REGION}/${SERVICE}/logs?project=${PROJECT_ID}"
else
  echo "✗ Some checks failed. Please fix the issues above before deploying."
fi
