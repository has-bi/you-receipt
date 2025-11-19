# Local Development Setup

This guide will help you set up the pharmacy stock OCR application for local development.

## Prerequisites

1. Python 3.11 or higher
2. Docker and Docker Compose (optional, for containerized development)
3. Google Cloud Platform service account with:
   - Google Sheets API access
   - Cloud Storage permissions
4. API Keys:
   - Mistral API key
   - OpenAI API key

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd pharmacy-stock-ocr

# Create .env from example
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Download Service Account Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **IAM & Admin → Service Accounts**
3. Select your service account (or create one with Sheets + Storage permissions)
4. Click **Keys → Add Key → Create new key**
5. Choose **JSON** format
6. Save the downloaded file as `credentials.json` in the project root

### 3. Configure Google Sheets

Create two Google Sheets:

**Master Data Sheet:**
- Sheet: `ASM_Area` - Columns: ASM Name | Area Code | Area Name
- Sheet: `Stores` - Columns: Store ID | Store Name | Area Code | Kota
- Sheet: `Products` - Columns: Product Name | SKU Code | Category
- Sheet: `Areas` - Columns: Area Code | Area Name | Region

**Output Sheet:**
- Sheet: `Stock_Output` - Columns: Timestamp | Area | ASM | Store | SKU | Stock Awal | Stock Akhir | Stock Terjual | Link Foto | Method

Share both sheets with your service account email (found in `credentials.json`).

### 4. Run the Application

**Option A: Docker (Recommended)**

```bash
docker compose up --build
```

Access the app at: http://localhost:8000

**Option B: Local Python**

```bash
# Install uv package manager
pip install uv

# Install dependencies
uv pip install -r pyproject.toml

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

Your `.env` file should contain:

```bash
# API Keys
MISTRAL_API_KEY=your_mistral_api_key
OPENAI_API_KEY=your_openai_api_key

# Google Cloud (Local Development)
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-gcp-project-id

# Google Sheets
MASTER_SHEET_ID=your_master_sheet_id
OUTPUT_SHEET_ID=your_output_sheet_id

# Optional
FUZZY_MATCH_THRESHOLD=0.75
MAX_UPLOAD_SIZE_MB=10
CACHE_TTL_SECONDS=300
CONFIDENCE_WARNING=0.7
OCR_CONCURRENCY=2
```

## Authentication: Local vs Cloud

### Local Development
- Uses `GOOGLE_APPLICATION_CREDENTIALS=credentials.json`
- Requires service account JSON file

### Cloud Run Deployment
- Uses **Application Default Credentials (ADC)** automatically
- No credentials file needed!
- See [GCP_DEPLOYMENT.md](./GCP_DEPLOYMENT.md) for details

## Troubleshooting

### Google Sheets connection fails
- Verify `credentials.json` is valid
- Ensure service account has access to both sheets
- Check sheet IDs are correct

### GCS upload fails
- Verify bucket name and project ID
- Ensure service account has Storage permissions
- Check that bucket exists

### OCR processing fails
- Verify Mistral and OpenAI API keys
- Check file size limits (default: 10MB)
- Ensure image format is supported (PNG, JPG, JPEG)

## Next Steps

- For production deployment to Google Cloud Run, see [GCP_DEPLOYMENT.md](./GCP_DEPLOYMENT.md)
- For cost optimization tips, see section 0 in GCP_DEPLOYMENT.md
