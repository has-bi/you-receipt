"""In-memory cache for master data from Google Sheets."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from models.schemas import ASM, Area, Store, Product

logger = logging.getLogger(__name__)


class MasterDataCache:
    """In-memory cache for master data with TTL refresh."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.last_refresh: Optional[datetime] = None

        # Data stores
        self.asms: List[ASM] = []
        self.areas: List[Area] = []
        self.stores: List[Store] = []
        self.products: List[Product] = []

        # Lookup maps
        self.asm_map: Dict[str, ASM] = {}
        self.area_map: Dict[str, Area] = {}
        self.store_map: Dict[str, Store] = {}
        self.product_map: Dict[str, Product] = {}
        self.sku_to_product: Dict[str, Product] = {}
        self.product_name_to_sku: Dict[str, str] = {}

        self._lock = asyncio.Lock()

    async def load_data(self, sheets_service):
        """Load all master data from Google Sheets."""
        async with self._lock:
            logger.info("Loading master data from Google Sheets...")

            # Load ASMs
            self.asms = await sheets_service.get_asms()
            self.asm_map = {asm.name: asm for asm in self.asms}

            # Load Areas
            self.areas = await sheets_service.get_areas()
            self.area_map = {area.area_code: area for area in self.areas}

            # Load Stores
            self.stores = await sheets_service.get_stores()
            self.store_map = {store.store_id: store for store in self.stores}

            # Load Products
            self.products = await sheets_service.get_products()
            self.product_map = {product.product_name: product for product in self.products}
            self.sku_to_product = {product.sku_code: product for product in self.products}
            self.product_name_to_sku = {product.product_name: product.sku_code for product in self.products}

            self.last_refresh = datetime.now()
            logger.info(f"Loaded {len(self.asms)} ASMs, {len(self.areas)} areas, "
                       f"{len(self.stores)} stores, {len(self.products)} products")

    async def refresh_if_needed(self, sheets_service):
        """Refresh cache if TTL has expired."""
        if self.last_refresh is None:
            await self.load_data(sheets_service)
            return

        if datetime.now() - self.last_refresh > timedelta(seconds=self.ttl_seconds):
            await self.load_data(sheets_service)

    def get_asm(self, name: str) -> Optional[ASM]:
        """Get ASM by name."""
        return self.asm_map.get(name)

    def get_area(self, area_code: str) -> Optional[Area]:
        """Get area by code."""
        return self.area_map.get(area_code)

    def get_store(self, store_id: str) -> Optional[Store]:
        """Get store by ID."""
        return self.store_map.get(store_id)

    def get_stores_by_area(self, area_code: str) -> List[Store]:
        """Get all stores in a specific area."""
        return [store for store in self.stores if store.area_code == area_code]

    def get_product_by_name(self, name: str) -> Optional[Product]:
        """Get product by exact name match."""
        return self.product_map.get(name)

    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU code."""
        return self.sku_to_product.get(sku)

    def get_all_product_names(self) -> List[str]:
        """Get all product names for fuzzy matching."""
        return list(self.product_name_to_sku.keys())

    def get_product_name_to_sku_mapping(self) -> Dict[str, str]:
        """Get product name to SKU mapping for converter."""
        return self.product_name_to_sku.copy()
