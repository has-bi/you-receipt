#!/usr/bin/env bash
# Script to verify sheets access after sharing

echo "Checking Cloud Run logs for data loading..."
echo "=============================================="
echo ""

gcloud run services logs read pharmacy-stock-ocr \
  --region=asia-southeast1 \
  --project=youvit-ai-chatbot \
  --limit=50 \
  --format="table(timestamp,textPayload)" \
  | grep -E "(Loaded|Error reading)"

echo ""
echo "If you see 'Loaded X ASMs, X areas, X stores, X products' with numbers > 0, it's working!"
echo "If you see 'Error reading' with 403 permission errors, permissions haven't propagated yet."
