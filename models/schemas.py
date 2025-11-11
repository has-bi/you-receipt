"""Pydantic data models for the pharmacy stock management system."""

from datetime import datetime
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


class ASM(BaseModel):
    """ASM (Area Sales Manager) model."""
    name: str
    area_code: str
    area_name: str


class Area(BaseModel):
    """Area/Region model."""
    area_code: str
    area_name: str
    region: str


class Store(BaseModel):
    """Pharmacy store model."""
    store_id: str
    store_name: str
    area_code: str
    alamat: str
    kota: str


class Product(BaseModel):
    """Product/Medicine model."""
    product_name: str
    sku_code: str
    category: str


class StockEntry(BaseModel):
    """Stock entry output model (to be saved to Google Sheets)."""
    timestamp: datetime = Field(default_factory=datetime.now)
    area: str
    asm: str
    store: str
    sku: str
    stock_awal: Optional[int] = None
    stock_akhir: Optional[int] = None
    stock_terjual: int  # MANDATORY
    link_foto: Optional[str] = None
    method: str  # "manual" or "ocr"

    @field_validator("stock_terjual")
    @classmethod
    def validate_stock_terjual(cls, v):
        if v is None:
            raise ValueError("Stock Terjual is mandatory and cannot be null")
        if v < 0:
            raise ValueError("Stock Terjual must be >= 0")
        return v

    @field_validator("stock_awal", "stock_akhir")
    @classmethod
    def validate_optional_stock(cls, v):
        if v is not None and v < 0:
            raise ValueError("Stock values must be >= 0")
        return v


class OCRResult(BaseModel):
    """Result from OCR extraction (Mistral + Claude)."""
    product_name: Optional[str] = None
    stock_awal: Optional[int] = None
    stock_akhir: Optional[int] = None
    stock_terjual: Optional[int] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    needs_review: bool = False
    error: Optional[str] = None
    raw_text: str = ""


class SKUConversionResult(BaseModel):
    """Result from Product-SKU conversion."""
    sku_code: Optional[str] = None
    confidence: float = 0.0
    suggestions: List[Tuple[str, str, float]] = []  # (product_name, sku_code, confidence)


class OCRPreviewItem(BaseModel):
    """Preview item for OCR bulk processing."""
    id: str  # Unique identifier for this item
    image_url: str  # GCS public URL
    sku_code: Optional[str] = None
    product_name: Optional[str] = None
    stock_awal: Optional[int] = None
    stock_akhir: Optional[int] = None
    stock_terjual: Optional[int] = None
    confidence_score: float = 0.0
    needs_review: bool = False
    error: Optional[str] = None
    suggestions: List[Tuple[str, str, float]] = []  # For SKU suggestions


class ManualSKUEntry(BaseModel):
    """Single SKU entry details for manual submission."""

    sku_code: str
    stock_awal: Optional[int] = None
    stock_akhir: Optional[int] = None
    stock_terjual: int

    @field_validator("stock_terjual")
    @classmethod
    def validate_stock_terjual(cls, v):
        if v < 0:
            raise ValueError("Stock Terjual must be >= 0")
        return v

    @field_validator("stock_awal", "stock_akhir")
    @classmethod
    def validate_optional_stock(cls, v):
        if v is not None and v < 0:
            raise ValueError("Stock values must be >= 0")
        return v

    @model_validator(mode="after")
    def validate_stock_consistency(self):
        awal_present = self.stock_awal is not None
        akhir_present = self.stock_akhir is not None

        if awal_present or akhir_present:
            if not awal_present or not akhir_present:
                raise ValueError("Stock Awal and Stock Akhir must be provided together")

            diff = self.stock_awal - self.stock_akhir
            if diff < 0:
                raise ValueError("Stock Akhir must be less than or equal to Stock Awal")
            if self.stock_terjual != diff:
                raise ValueError(
                    "Stock Terjual must equal Stock Awal minus Stock Akhir when both are provided"
                )
        return self


class ManualInputRequest(BaseModel):
    """Request model for manual input submission with multiple SKUs."""

    asm_name: str
    store_id: str
    entries: List[ManualSKUEntry]

    @field_validator("entries")
    @classmethod
    def validate_entries(cls, v):
        if not v:
            raise ValueError("At least one SKU entry is required")
        return v

class OCRBulkRequest(BaseModel):
    """Request model for OCR bulk processing."""
    asm_name: str
    store_name: str  # Can be typed manually, not strict to master
    items: List[OCRPreviewItem]  # After user edits in preview
