"""Google Sheets integration for reading master data and writing output."""

import logging
from typing import List, Optional

from google.auth import default as google_auth_default
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.schemas import ASM, Area, Product, StockEntry, Store

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for interacting with Google Sheets API."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(
        self,
        credentials_path: Optional[str],
        master_sheet_id: str,
        output_sheet_id: str,
    ):
        self.master_sheet_id = master_sheet_id
        self.output_sheet_id = output_sheet_id

        # Initialize Google Sheets API client
        credentials = self._load_credentials(credentials_path)
        self.service = build("sheets", "v4", credentials=credentials)
        self.sheets = self.service.spreadsheets()

    def _load_credentials(self, credentials_path: Optional[str]):
        if credentials_path:
            return service_account.Credentials.from_service_account_file(
                credentials_path, scopes=self.SCOPES
            )

        credentials, _ = google_auth_default(scopes=self.SCOPES)
        if not credentials:
            raise RuntimeError("Unable to determine Google credentials")
        return credentials

    async def get_asms(self) -> List[ASM]:
        """Read ASM data from 'ASM_Area' sheet."""
        try:
            result = (
                self.sheets.values()
                .get(
                    spreadsheetId=self.master_sheet_id,
                    range="ASM_Area!A2:C",  # Skip header row
                )
                .execute()
            )

            values = result.get("values", [])
            asms = []

            for row in values:
                if len(row) >= 3:
                    asms.append(ASM(name=row[0], area_code=row[1], area_name=row[2]))

            logger.info(f"Loaded {len(asms)} ASMs from Google Sheets")
            return asms
        except HttpError as e:
            logger.error(f"Error reading ASM data: {e}")
            return []

    async def get_areas(self) -> List[Area]:
        """Read Area data from 'Areas' sheet."""
        try:
            result = (
                self.sheets.values()
                .get(
                    spreadsheetId=self.master_sheet_id,
                    range="Areas!A2:C",  # Skip header row
                )
                .execute()
            )

            values = result.get("values", [])
            areas = []

            for row in values:
                if len(row) >= 3:
                    areas.append(
                        Area(area_code=row[0], area_name=row[1], region=row[2])
                    )

            logger.info(f"Loaded {len(areas)} areas from Google Sheets")
            return areas
        except HttpError as e:
            logger.error(f"Error reading Area data: {e}")
            return []

    async def get_stores(self) -> List[Store]:
        """Read Store data from 'Stores' sheet."""
        try:
            result = (
                self.sheets.values()
                .get(
                    spreadsheetId=self.master_sheet_id,
                    range="Stores!A2:D",  # Skip header row
                )
                .execute()
            )

            values = result.get("values", [])
            stores = []

            for row in values:
                # Sheet columns: Store ID, Store Name, Area Code, Kota
                if len(row) >= 4:
                    stores.append(
                        Store(
                            store_id=row[0],
                            store_name=row[1],
                            area_code=row[2],
                            alamat="",  # Address column not provided in sheet
                            kota=row[3],
                        )
                    )

            logger.info(f"Loaded {len(stores)} stores from Google Sheets")
            return stores
        except HttpError as e:
            logger.error(f"Error reading Store data: {e}")
            return []

    async def get_products(self) -> List[Product]:
        """Read Product data from 'Products' sheet."""
        try:
            result = (
                self.sheets.values()
                .get(
                    spreadsheetId=self.master_sheet_id,
                    range="Products!A2:C",  # Skip header row
                )
                .execute()
            )

            values = result.get("values", [])
            products = []

            for row in values:
                if len(row) >= 3:
                    products.append(
                        Product(product_name=row[0], sku_code=row[1], category=row[2])
                    )

            logger.info(f"Loaded {len(products)} products from Google Sheets")
            return products
        except HttpError as e:
            logger.error(f"Error reading Product data: {e}")
            return []

    async def append_stock_entry(self, entry: StockEntry) -> bool:
        """Append a stock entry to the 'Stock_Output' sheet."""
        try:
            # Format row data
            row_data = [
                entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                entry.area,
                entry.asm,
                entry.store,
                entry.sku,
                entry.stock_awal if entry.stock_awal is not None else "",
                entry.stock_akhir if entry.stock_akhir is not None else "",
                entry.stock_terjual,
                self._format_link(entry.link_foto),
                entry.method,
            ]

            self.sheets.values().batchUpdate(
                spreadsheetId=self.output_sheet_id,
                body={
                    "value_input_option": "USER_ENTERED",
                    "data": [
                        {
                            "range": "Stock_Output!A:J",
                            "values": [row_data],
                        }
                    ],
                },
            ).execute()

            logger.info(f"Appended stock entry: {entry.sku} - {entry.store}")
            return True
        except HttpError as e:
            logger.error(f"Error appending stock entry: {e}")
            return False

    def _format_link(self, url: Optional[str]) -> str:
        if not url:
            return ""
        escaped = url.replace('"', '""')
        return f'=HYPERLINK("{escaped}", "Lihat Foto")'

    async def append_stock_entries_batch(self, entries: List[StockEntry]) -> bool:
        """Append multiple stock entries in a single batch request."""
        try:
            rows_data = []
            for entry in entries:
                row_data = [
                    entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    entry.area,
                    entry.asm,
                    entry.store,
                    entry.sku,
                    entry.stock_awal if entry.stock_awal is not None else "",
                    entry.stock_akhir if entry.stock_akhir is not None else "",
                    entry.stock_terjual,
                    self._format_link(entry.link_foto),
                    entry.method,
                ]
                rows_data.append(row_data)

            self.sheets.values().batchUpdate(
                spreadsheetId=self.output_sheet_id,
                body={
                    "value_input_option": "USER_ENTERED",
                    "data": [
                        {
                            "range": "Stock_Output!A:J",
                            "values": rows_data,
                        }
                    ],
                },
            ).execute()

            logger.info(f"Batch appended {len(entries)} stock entries")
            return True
        except HttpError as e:
            logger.error(f"Error batch appending stock entries: {e}")
            return False
