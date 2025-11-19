# Sistem Manajemen Stok Apotek

Sistem manajemen stok apotek dengan dua metode input: manual entry dan OCR bulk processing berbasis AI.

## Fitur Utama

- **Input Manual**: Form entry cepat dengan dropdown yang dapat dicari
- **Scan Struk (OCR)**: Ekstraksi data otomatis dari foto struk menggunakan Mistral Pixtral-12B dan OpenAI GPT-4
- **Integrasi Google Sheets**: Penyimpanan master data dan output
- **Google Cloud Storage**: Backup gambar otomatis dengan URL publik
- **Product-SKU Converter**: Pencocokan fuzzy untuk konversi nama produk ke SKU

## Teknologi

- **Backend**: FastAPI + Python 3.11+ dengan package manager `uv`
- **Frontend**: HTML + Tailwind CSS + HTMX + Tom-Select
- **OCR**: Mistral Pixtral-12B untuk ekstraksi teks
- **LLM**: OpenAI GPT-4 untuk ekstraksi data terstruktur
- **Storage**: Google Cloud Storage untuk gambar
- **Database**: Google Sheets (master data + output)
- **Deployment**: Docker + Docker Compose

## Prerequisites

1. Python 3.11 or higher
2. Docker and Docker Compose (for containerized deployment)
3. Google Cloud Platform account with:
   - Service account with Sheets API and Cloud Storage permissions
   - GCS bucket created
   - Service account credentials JSON file
4. API Keys:
   - Mistral API key
   - OpenAI API key
5. Google Sheets:
   - Master data spreadsheet (with ASM_Area, Stores, Products, Areas sheets)
   - Output data spreadsheet (with Stock_Output sheet)

## Project Structure

```
pharmacy-stock-ocr/
├── main.py                      # FastAPI application
├── pyproject.toml              # uv dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker compose setup
├── .env                        # Environment variables (create from .env.example)
├── .env.example                # Environment variables template
├── credentials.json            # Google service account (add manually)
│
├── models/
│   ├── __init__.py
│   └── schemas.py              # Pydantic data models
│
├── services/
│   ├── __init__.py
│   ├── sheets.py               # Google Sheets integration
│   ├── gcs.py                  # Google Cloud Storage uploads
│   ├── ocr.py                  # Mistral + Claude OCR pipeline
│   ├── converter.py            # Product name → SKU converter
│   └── database.py             # In-memory cache for master data
│
├── templates/
│   ├── base.html               # Base template with Tailwind + HTMX
│   ├── home.html               # Landing page
│   ├── manual_input.html       # Manual form
│   └── ocr_input.html          # OCR bulk upload & preview
│
└── static/
    └── uploads/                # Temporary uploads (before GCS)
```

## Setup Instructions

### 1. Clone and Setup Environment

```bash
# Clone repository
git clone <repository-url>
cd pharmacy-stock-ocr

# Create .env file from example
cp .env.example .env

# Edit .env with your actual credentials
nano .env
```

### 2. Configure Environment Variables

Edit `.env` file:

```bash
# API Keys
MISTRAL_API_KEY=your_mistral_api_key
OPENAI_API_KEY=your_openai_api_key

# Google Cloud (Local Development Only)
# For local: use credentials.json file
# For Cloud Run: leave unset, uses Application Default Credentials
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-gcp-project-id

# Google Sheets
MASTER_SHEET_ID=your_master_sheet_id
OUTPUT_SHEET_ID=your_output_sheet_id

# Optional Configuration
FUZZY_MATCH_THRESHOLD=0.75
MAX_UPLOAD_SIZE_MB=10
CACHE_TTL_SECONDS=300
```

### 3. Add Google Service Account Credentials

1. Download your service account JSON key from Google Cloud Console
2. Save it as `credentials.json` in the project root
3. Ensure the service account has:
   - Google Sheets API enabled with read/write permissions
   - Cloud Storage permissions (storage.objects.create, storage.objects.get)

### 4. Prepare Google Sheets

Create two Google Sheets with the following structure:

**Master Data Sheet** (MASTER_SHEET_ID):

- Sheet: **ASM_Area**
  - Columns: ASM Name | Area Code | Area Name

- Sheet: **Stores**
  - Columns: Store ID | Store Name | Area Code | Alamat | Kota

- Sheet: **Products**
  - Columns: Product Name | SKU Code | Category

- Sheet: **Areas**
  - Columns: Area Code | Area Name | Region

**Output Sheet** (OUTPUT_SHEET_ID):

- Sheet: **Stock_Output**
  - Columns: Timestamp | Area | ASM | Store | SKU | Stock Awal | Stock Akhir | Stock Terjual | Link Foto | Method

Share both sheets with your service account email (found in credentials.json).

### 5. Setup GCS Bucket

```bash
# Create bucket (or use existing one)
gsutil mb gs://your-bucket-name

# Make bucket publicly readable (or use signed URLs)
gsutil iam ch allUsers:objectViewer gs://your-bucket-name
```

## Running the Application

### Option 1: Docker (Recommended)

```bash
# Build and run with Docker Compose
docker compose up --build

# Run in detached mode
docker compose up -d

# View logs
docker compose logs -f app

# Stop
docker compose down
```

The application will be available at `http://localhost:8000`

### Option 2: Local Development

```bash
# Install uv package manager
pip install uv

# Install dependencies
uv pip install -r pyproject.toml

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Usage Guide

### Alur Input Manual

1. Buka halaman `/manual`
2. Pilih ASM dari dropdown (area terisi otomatis)
3. Pilih Toko (terfilter berdasarkan area)
4. Pilih Produk/SKU
5. Masukkan jumlah stok:
   - Stok Awal (opsional)
   - Stok Akhir (opsional)
   - Stok Terjual (wajib)
6. Simpan
7. Data tersimpan ke Google Sheets

### Alur Scan Struk (OCR)

1. Buka halaman `/ocr`
2. Pilih ASM (area terisi otomatis)
3. Ketik Nama Toko (bisa diketik manual)
4. Upload beberapa foto struk
5. Klik "Proses dengan AI"
6. Tunggu proses AI (Mistral OCR + OpenAI ekstraksi)
7. Review data yang diekstrak:
   - Setiap item menampilkan gambar dan data
   - Item dengan akurasi rendah ditandai kuning
   - Edit field yang perlu diperbaiki
   - Saran SKU ditampilkan untuk produk yang tidak cocok
8. Klik "Simpan Semua Data"
9. Data tersimpan ke Google Sheets dengan URL gambar GCS

## API Endpoints

- `GET /` - Landing page
- `GET /manual` - Manual input form
- `GET /ocr` - OCR bulk upload page
- `GET /api/stores?area={code}` - Get stores filtered by area
- `POST /api/manual-submit` - Submit manual entry
- `POST /api/ocr-process` - Process images through OCR
- `POST /api/ocr-submit` - Submit OCR bulk entries
- `GET /health` - Health check endpoint

## Data Validation

- **ASM**: Must exist in master data
- **Store**: Must exist in master AND belong to ASM's area
- **SKU**: Must exist in master (exact match for manual, fuzzy for OCR)
- **Stock Terjual**: MANDATORY, must be integer >= 0
- **Stock Awal/Akhir**: Optional, must be integer >= 0 if provided

## Fuzzy Matching

The Product-SKU converter uses three strategies:

1. **Exact match** (confidence: 1.0)
2. **Case-insensitive match** (confidence: 0.95)
3. **Fuzzy match** using difflib (confidence: 0.0-1.0)

Items with confidence < 0.7 are flagged for review.

## Troubleshooting

### Common Issues

**Koneksi Google Sheets gagal:**
- Verifikasi credentials.json valid
- Pastikan service account memiliki akses ke sheets
- Cek MASTER_SHEET_ID dan OUTPUT_SHEET_ID sudah benar

**Upload GCS gagal:**
- Verifikasi GCS_BUCKET_NAME dan GCS_PROJECT_ID
- Pastikan service account memiliki permission storage
- Cek bucket sudah ada dan dapat diakses

**Proses OCR gagal:**
- Verifikasi MISTRAL_API_KEY dan OPENAI_API_KEY
- Cek ukuran file gambar (harus < MAX_UPLOAD_SIZE_MB)
- Pastikan format gambar didukung (PNG, JPG, JPEG)

**Dependencies installation fails:**
- Ensure Python 3.11+ is installed
- Try: `uv pip install --upgrade pip`
- Check internet connection

### Logs

View application logs:

```bash
# Docker
docker compose logs -f app

# Local
# Logs printed to console
```

## Development

### Hot Reload

When running with Docker Compose, changes to the following are automatically reloaded:

- `main.py`
- `services/*.py`
- `templates/*.html`
- `models/*.py`

### Running Tests

```bash
# TODO: Add pytest tests
pytest
```

## Production Deployment

### Deploy to Google Cloud Run

For detailed deployment instructions including cost optimization and best practices, see [GCP_DEPLOYMENT.md](./GCP_DEPLOYMENT.md).

**Quick deployment** (after setup):

```bash
# Build and deploy
./deploy.sh
```

The app automatically uses **Application Default Credentials** in Cloud Run - no credentials file needed! See GCP_DEPLOYMENT.md for authentication details.

## License

[Your License Here]

## Support

For issues and questions, please open an issue in the repository.
