# Quick Start Guide

Get up and running with the Pharmacy Stock Management System in 5 steps.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional, but recommended)
- Google Cloud Platform account
- Mistral API key
- Anthropic API key

## Step 1: Clone and Setup

```bash
cd youvit-receipt
./setup.sh
```

## Step 2: Configure Environment

Edit `.env` file with your credentials:

```bash
nano .env
```

Required variables:
- `MISTRAL_API_KEY` - Get from https://console.mistral.ai/
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com/
- `GCS_BUCKET_NAME` - Your GCS bucket name
- `GCS_PROJECT_ID` - Your GCP project ID
- `MASTER_SHEET_ID` - Google Sheet ID for master data
- `OUTPUT_SHEET_ID` - Google Sheet ID for output data

## Step 3: Add Google Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to IAM & Admin > Service Accounts
3. Create service account (if needed) with:
   - Google Sheets API access
   - Cloud Storage access
4. Download JSON key
5. Save as `credentials.json` in project root

## Step 4: Setup Google Sheets

Follow the detailed guide in `SHEETS_SETUP.md` to create:

1. **Master Data Sheet** with 4 tabs:
   - ASM_Area
   - Stores
   - Products
   - Areas

2. **Output Sheet** with 1 tab:
   - Stock_Output

**Important**: Share both sheets with your service account email (found in `credentials.json`)

## Step 5: Verify Setup

```bash
python verify_setup.py
```

Fix any issues reported by the verification script.

## Step 6: Run the Application

### Option A: Docker (Recommended)

```bash
docker compose up --build
```

### Option B: Local Development

```bash
# Install dependencies
uv pip install -r pyproject.toml

# Run application
uvicorn main:app --reload
```

## Access the Application

Open your browser and navigate to:
- **Home**: http://localhost:8000
- **Manual Input**: http://localhost:8000/manual
- **OCR Bulk**: http://localhost:8000/ocr
- **Health Check**: http://localhost:8000/health

## Test the System

### Test Manual Input

1. Go to http://localhost:8000/manual
2. Select an ASM from dropdown
3. Area will auto-populate
4. Select a store (filtered by area)
5. Select a product/SKU
6. Enter stock quantities
7. Submit
8. Check your Output Google Sheet - new row should appear!

### Test OCR Bulk Processing

1. Go to http://localhost:8000/ocr
2. Select an ASM
3. Enter store name
4. Upload 1-2 test receipt images
5. Click "Process Images with OCR"
6. Wait for processing (may take 1-2 minutes)
7. Review extracted data
8. Edit if needed
9. Submit all
10. Check your Output Google Sheet - new rows should appear!

## Troubleshooting

### Common Issues

**Port 8000 already in use:**
```bash
# Change port in docker-compose.yml or run with:
uvicorn main:app --reload --port 8080
```

**Google Sheets access denied:**
- Verify sheets are shared with service account email
- Check service account has "Editor" permissions

**OCR processing fails:**
- Verify API keys are correct in .env
- Check image file size (< 10MB)
- Ensure image is in supported format (PNG, JPG, JPEG)

**Dependencies not found:**
```bash
# Reinstall dependencies
uv pip install --upgrade -r pyproject.toml
```

### View Logs

**Docker:**
```bash
docker compose logs -f app
```

**Local:**
Logs appear in terminal where you ran uvicorn

## What's Next?

1. **Add your real data** to the Master Data Sheet
2. **Customize** the UI in `templates/` if needed
3. **Adjust** fuzzy matching threshold in `.env` (`FUZZY_MATCH_THRESHOLD`)
4. **Set up** regular backups of your Google Sheets
5. **Deploy** to production (see README.md for Cloud Run deployment)

## Getting Help

- See `README.md` for detailed documentation
- See `SHEETS_SETUP.md` for Google Sheets structure
- Check application logs for error messages
- Verify setup with `python verify_setup.py`

## Key Features to Try

✅ **Smart Dropdowns**: ASM selection auto-filters stores by area  
✅ **Searchable Fields**: Type to search in dropdowns (Tom-Select)  
✅ **OCR Magic**: Upload receipt images, AI extracts data  
✅ **Fuzzy Matching**: Product names with typos still get matched  
✅ **Editable Preview**: Review and edit OCR results before saving  
✅ **Cloud Storage**: Images automatically uploaded to GCS  
✅ **Real-time Sync**: Data instantly appears in Google Sheets  

Happy stock tracking! 🎉
