"""Main FastAPI application for pharmacy stock management system."""

import asyncio
import logging
import os
import uuid
import mimetypes
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models.schemas import ManualInputRequest, StockEntry
from services import (
    GCSUploader,
    GoogleSheetsService,
    MasterDataCache,
    MultiProductOCRService,
    ProductSKUConverter,
    SKUAggregator,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
cache: Optional[MasterDataCache] = None
sheets_service: Optional[GoogleSheetsService] = None
gcs_uploader: Optional[GCSUploader] = None
ocr_service: Optional[MultiProductOCRService] = None
sku_converter: Optional[ProductSKUConverter] = None
sku_aggregator: Optional[SKUAggregator] = None


async def ensure_master_data_synced():
    """Refresh cache if needed and sync SKU converter mapping."""
    if cache is None or sheets_service is None:
        return
    await cache.refresh_if_needed(sheets_service)
    if sku_converter:
        sku_converter.update_mapping(cache.get_product_name_to_sku_mapping())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup and cleanup on shutdown."""
    global cache, sheets_service, gcs_uploader, ocr_service, sku_converter, sku_aggregator

    logger.info("Starting pharmacy stock management system...")

    # Initialize services
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    master_sheet_id = os.getenv("MASTER_SHEET_ID")
    output_sheet_id = os.getenv("OUTPUT_SHEET_ID")

    if not master_sheet_id or not output_sheet_id:
        raise ValueError(
            "MASTER_SHEET_ID and OUTPUT_SHEET_ID must be set in environment"
        )

    # Google Sheets service
    sheets_service = GoogleSheetsService(
        credentials_path=credentials_path,
        master_sheet_id=master_sheet_id,
        output_sheet_id=output_sheet_id,
    )

    # Master data cache
    cache_ttl = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    cache = MasterDataCache(ttl_seconds=cache_ttl)
    await cache.load_data(sheets_service)

    # GCS uploader
    gcs_bucket = os.getenv("GCS_BUCKET_NAME")
    gcs_project = os.getenv("GCS_PROJECT_ID")
    if gcs_bucket and gcs_project:
        gcs_uploader = GCSUploader(
            bucket_name=gcs_bucket,
            project_id=gcs_project,
            credentials_path=credentials_path,
        )
    else:
        logger.warning("GCS credentials not configured, OCR uploads will fail")

    # OCR service
    mistral_key = os.getenv("MISTRAL_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    confidence_warning = float(os.getenv("CONFIDENCE_WARNING", "0.7"))

    if mistral_key and openai_key:
        ocr_service = MultiProductOCRService(
            mistral_api_key=mistral_key,
            openai_api_key=openai_key,
            review_threshold=confidence_warning,
        )
    else:
        logger.warning("OCR API keys not configured, OCR will fail")

    # SKU converter
    fuzzy_threshold = float(os.getenv("FUZZY_MATCH_THRESHOLD", "0.75"))
    sku_converter = ProductSKUConverter(
        mapping=cache.get_product_name_to_sku_mapping(), threshold=fuzzy_threshold
    )
    sku_aggregator = SKUAggregator(review_threshold=confidence_warning)

    logger.info("All services initialized successfully")

    yield

    logger.info("Shutting down pharmacy stock management system...")


# Initialize FastAPI app
app = FastAPI(
    title="Pharmacy Stock Management",
    description="Dual-input pharmacy stock management with manual entry and OCR bulk processing",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker."""
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with two input options."""
    await ensure_master_data_synced()
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/manual", response_class=HTMLResponse)
async def manual_input_page(request: Request):
    """Manual input form page."""
    await ensure_master_data_synced()

    return templates.TemplateResponse(
        "manual_input.html",
        {"request": request, "asms": cache.asms, "products": cache.products},
    )


@app.get("/ocr", response_class=HTMLResponse)
async def ocr_input_page(request: Request):
    """OCR bulk upload page."""
    await ensure_master_data_synced()

    return templates.TemplateResponse(
        "ocr_input.html", {"request": request, "asms": cache.asms}
    )


@app.get("/api/stores")
async def get_stores(area: Optional[str] = None):
    """Get stores, optionally filtered by area code."""
    await ensure_master_data_synced()

    if area:
        stores = cache.get_stores_by_area(area)
    else:
        stores = cache.stores

    return [
        {
            "id": store.store_id,
            "name": store.store_name,
            "area_code": store.area_code,
            "kota": store.kota,
            "alamat": store.alamat,
        }
        for store in stores
    ]


@app.post("/api/manual-submit")
async def submit_manual_entry(request: ManualInputRequest):
    """Submit manual stock entries (one ASM/store, multiple SKUs)."""
    await ensure_master_data_synced()

    # Validate ASM
    asm = cache.get_asm(request.asm_name)
    if not asm:
        raise HTTPException(status_code=400, detail="Invalid ASM name")

    # Validate Store
    store = cache.get_store(request.store_id)
    if not store:
        raise HTTPException(status_code=400, detail="Invalid store ID")

    # Validate store belongs to ASM's area
    if store.area_code != asm.area_code:
        raise HTTPException(
            status_code=400, detail="Store does not belong to ASM's area"
        )

    stock_entries: List[StockEntry] = []

    for idx, sku_entry in enumerate(request.entries, start=1):
        product = cache.get_product_by_sku(sku_entry.sku_code)
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid SKU code for entry #{idx}",
            )

        stock_entries.append(
            StockEntry(
                area=asm.area_code,
                asm=request.asm_name,
                store=store.store_name,
                sku=sku_entry.sku_code,
                stock_awal=sku_entry.stock_awal,
                stock_akhir=sku_entry.stock_akhir,
                stock_terjual=sku_entry.stock_terjual,
                link_foto=None,
                method="manual",
            )
        )

    # Save to Google Sheets in batch
    success = await sheets_service.append_stock_entries_batch(stock_entries)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save to Google Sheets")

    return {
        "success": True,
        "message": f"{len(stock_entries)} SKU berhasil disimpan",
        "entries": [
            {
                "sku": entry.sku,
                "stock_terjual": entry.stock_terjual,
            }
            for entry in stock_entries
        ],
    }


@app.post("/api/ocr-process")
async def process_ocr_images(
    asm_name: str = Form(...),
    store_name: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """Process multiple images through OCR pipeline."""
    await ensure_master_data_synced()

    # Validate ASM
    asm = cache.get_asm(asm_name)
    if not asm:
        raise HTTPException(status_code=400, detail="Invalid ASM name")

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    preview_items: list[dict] = []
    documents: list[dict] = []
    max_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    max_size_bytes = max_size_mb * 1024 * 1024
    concurrency_limit = max(1, int(os.getenv("OCR_CONCURRENCY", "2")))
    semaphore = asyncio.Semaphore(concurrency_limit)

    async def process_single_file(index: int, file: UploadFile):
        document_id = str(uuid.uuid4())
        original_filename = file.filename or f"Document {index}"
        content_type = file.content_type or mimetypes.guess_type(original_filename)[0]

        async with semaphore:
            temp_path = None
            try:
                file_bytes = await file.read()
                if len(file_bytes) > max_size_bytes:
                    error_message = f"File exceeds {max_size_mb}MB size limit"
                    return (
                        [
                            {
                                "id": str(uuid.uuid4()),
                                "document_id": document_id,
                                "image_url": None,
                                "sku_code": None,
                                "product_name": None,
                                "stock_awal": None,
                                "stock_akhir": None,
                                "stock_terjual": None,
                                "confidence_score": 0.0,
                                "needs_review": True,
                                "error": error_message,
                                "suggestions": [],
                            }
                        ],
                        {
                            "id": document_id,
                            "filename": original_filename,
                            "image_url": None,
                            "document_url": None,
                            "mime_type": content_type,
                            "matched_products": [],
                            "unmatched_products": [],
                            "errors": [error_message],
                        },
                    )

                temp_path = f"static/uploads/{uuid.uuid4().hex}_{file.filename or 'upload'}"
                with open(temp_path, "wb") as f:
                    f.write(file_bytes)

                image_url = await gcs_uploader.upload_file(temp_path, original_filename)
                ocr_results = await ocr_service.process_document(temp_path)
                aggregation = sku_aggregator.aggregate(ocr_results, sku_converter)
                document_errors = [err for err in (res.error for res in ocr_results) if err]

                document_payload = {
                    "id": document_id,
                    "filename": original_filename,
                    "image_url": image_url,
                    "document_url": image_url,
                    "mime_type": content_type,
                    "matched_products": aggregation["matched"],
                    "unmatched_products": aggregation["unmatched"],
                    "errors": document_errors,
                }

                preview_payloads = []
                for entry in aggregation["entries"]:
                    preview_payloads.append(
                        {
                            "id": str(uuid.uuid4()),
                            "document_id": document_id,
                            "image_url": image_url,
                            "sku_code": entry.get("sku_code"),
                            "product_name": entry.get("product_name"),
                            "stock_awal": None,
                            "stock_akhir": None,
                            "stock_terjual": entry.get("stock_terjual"),
                            "confidence_score": entry.get("confidence_score", 0.0),
                            "needs_review": entry.get("needs_review", True),
                            "error": entry.get("error"),
                            "suggestions": entry.get("suggestions", []),
                        }
                    )

                return preview_payloads, document_payload
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Error processing file {original_filename}: {exc}")
                return (
                    [
                        {
                            "id": str(uuid.uuid4()),
                            "document_id": document_id,
                            "image_url": None,
                            "error": f"Processing failed: {str(exc)}",
                            "needs_review": True,
                            "sku_code": None,
                            "product_name": None,
                            "stock_awal": None,
                            "stock_akhir": None,
                            "stock_terjual": None,
                            "confidence_score": 0.0,
                            "suggestions": [],
                        }
                    ],
                    {
                        "id": document_id,
                        "filename": original_filename,
                        "image_url": None,
                        "document_url": None,
                        "mime_type": content_type,
                        "matched_products": [],
                        "unmatched_products": [],
                        "errors": [f"Processing failed: {str(exc)}"],
                    },
                )
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

    tasks = [process_single_file(idx, file) for idx, file in enumerate(files, start=1)]
    results = await asyncio.gather(*tasks)

    for previews, document in results:
        preview_items.extend(previews)
        documents.append(document)

    return {
        "success": True,
        "asm_name": asm_name,
        "store_name": store_name,
        "area": asm.area_code,
        "results": preview_items,
        "documents": documents,
    }


@app.post("/api/ocr-submit")
async def submit_ocr_bulk(request: Request):
    """Submit OCR bulk entries after user review/editing."""
    await cache.refresh_if_needed(sheets_service)

    data = await request.json()
    asm_name = data.get("asm_name")
    store_name = data.get("store_name")
    documents_payload = data.get("documents")
    items = data.get("items", [])

    # Validate ASM
    asm = cache.get_asm(asm_name)
    if not asm:
        raise HTTPException(status_code=400, detail="Invalid ASM name")

    # Create stock entries
    entries = []

    if documents_payload is not None:
        for document in documents_payload:
            image_url = document.get("image_url")
            for product in document.get("matched_products", []):
                sku = product.get("sku")
                qty = product.get("total_qty")
                if not sku or qty is None:
                    continue

                entries.append(
                    StockEntry(
                        area=asm.area_code,
                        asm=asm_name,
                        store=store_name,
                        sku=sku,
                        stock_awal=None,
                        stock_akhir=None,
                        stock_terjual=qty,
                        link_foto=image_url,
                        method="ocr",
                    )
                )
    else:
        grouped: dict[tuple[str, str], dict] = {}
        for item in items:
            sku = item.get("sku_code")
            qty = item.get("stock_terjual")
            if not sku or qty is None:
                continue

            doc_id = item.get("document_id", "")
            key = (doc_id, sku)
            group = grouped.setdefault(
                key,
                {
                    "total": 0,
                    "count": 0,
                    "image_url": item.get("image_url"),
                },
            )
            group["total"] += qty
            group["count"] += 1
            if not group["image_url"] and item.get("image_url"):
                group["image_url"] = item.get("image_url")

        for (_, sku), payload in grouped.items():
            entries.append(
                StockEntry(
                    area=asm.area_code,
                    asm=asm_name,
                    store=store_name,
                    sku=sku,
                    stock_awal=None,
                    stock_akhir=None,
                    stock_terjual=payload["total"],
                    link_foto=payload.get("image_url"),
                    method="ocr",
                )
            )

    if not entries:
        raise HTTPException(status_code=400, detail="No valid entries to submit")

    # Batch save to Google Sheets
    success = await sheets_service.append_stock_entries_batch(entries)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save to Google Sheets")

    return {
        "success": True,
        "message": f"Successfully saved {len(entries)} stock entries",
        "count": len(entries),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
