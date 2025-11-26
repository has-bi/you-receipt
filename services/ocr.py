"""OCR service using Mistral Document AI and OpenAI GPT-4 for structured extraction."""

import base64
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any, List, Tuple

import httpx
from openai import OpenAI

from models.schemas import OCRResult

logger = logging.getLogger(__name__)


def _normalize_response_content(content: Any) -> str:
    """Return plain text from SDK-specific message content structures."""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    extracted_parts: list[str] = []

    for part in content if isinstance(content, list) else [content]:
        if isinstance(part, str):
            extracted_parts.append(part)
            continue

        # Handle dict responses from SDKs
        if isinstance(part, dict):
            text_value = part.get("text") or part.get("content")
            if isinstance(text_value, str):
                extracted_parts.append(text_value)
            continue

        # Handle objects with a text attribute (e.g., SDK dataclasses)
        text_value = getattr(part, "text", None)
        if isinstance(text_value, str):
            extracted_parts.append(text_value)

    return " ".join(extracted_parts).strip()


def _extract_document_ai_text(payload: Any) -> str:
    """Extract concatenated text segments from a Document AI OCR response."""

    if isinstance(payload, dict):
        pages = payload.get("pages")
        if isinstance(pages, list):
            page_texts: list[str] = []
            for page in pages:
                if not isinstance(page, dict):
                    continue
                markdown = page.get("markdown")
                if isinstance(markdown, str) and markdown.strip():
                    page_texts.append(markdown.strip())
            if page_texts:
                return "\n\n".join(page_texts)

    texts: list[str] = []

    def _walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, str):
            stripped = node.strip()
            if stripped:
                texts.append(stripped)
            return
        if isinstance(node, dict):
            # Textual content is commonly stored in these keys; inspect them first.
            for key in ("text", "content", "raw_text", "value"):
                if key in node:
                    _walk(node[key])
            for value in node.values():
                if isinstance(value, (list, dict)):
                    _walk(value)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return "\n".join(texts)


MISTRAL_DOCUMENT_AI_URL = "https://api.mistral.ai/v1/ocr"
MISTRAL_FILES_URL = "https://api.mistral.ai/v1/files"
MISTRAL_DOCUMENT_AI_MODEL = "mistral-ocr-latest"
SUPPORTED_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "application/pdf"}


def _parse_json_payload(payload: str) -> Any:
    """Parse model response text into JSON, stripping markdown fences if needed."""

    payload = payload.strip()
    if payload.startswith("```"):
        payload = payload.strip("`")
        newline = payload.find("\n")
        if newline != -1:
            payload = payload[newline + 1 :]

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        if payload and payload[0] != "[":
            start = payload.find("[")
            end = payload.rfind("]")
            if start != -1 and end != -1 and end > start:
                payload = payload[start : end + 1]
        return json.loads(payload)


def _safe_parse_json_array(payload: str) -> list[Any]:
    """Parse a string into a JSON array, stripping markdown fences if needed."""

    data = _parse_json_payload(payload)
    if isinstance(data, dict) and "products" in data:
        data = data["products"]
    return data


def _coerce_int(value: Any) -> int | None:
    """Convert strings/numbers into ints, handling commas/decimals."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        negative = cleaned.startswith("-")
        normalized = cleaned.replace("-", "").replace(",", "")
        try:
            as_int = int(float(normalized))
        except ValueError:
            return None
        return -as_int if negative else as_int
    return None


class MultiProductOCRService:
    """OCR pipeline that extracts multiple product lines from a single document."""

    def __init__(
        self,
        mistral_api_key: str,
        openai_api_key: str,
        review_threshold: float = 0.7,
    ):
        self.mistral_api_key = mistral_api_key
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.review_threshold = review_threshold

    async def process_document(self, image_path: str) -> List[OCRResult]:
        """Run full OCR pipeline and return a list of OCRResult objects."""
        try:
            raw_text = await self.mistral_ocr(image_path)
            logger.info(
                "Mistral OCR raw text for %s (first 500 chars): %s",
                Path(image_path).name,
                raw_text[:500].replace("\n", " ").strip(),
            )

            if not raw_text or raw_text.strip() == "":
                return [
                    OCRResult(
                        product_name=None,
                        stock_terjual=None,
                        confidence_score=0.0,
                        needs_review=True,
                        error="Mistral OCR failed to extract text from image",
                        raw_text="",
                    )
                ]

            products = await self.openai_extract_multi(raw_text)
            if not products:
                return [
                    OCRResult(
                        product_name=None,
                        stock_terjual=None,
                        confidence_score=0.0,
                        needs_review=True,
                        error="OpenAI extraction returned no products",
                        raw_text=raw_text,
                    )
                ]

            return products

        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Error processing document: {e}")
            return [
                OCRResult(
                    product_name=None,
                    stock_terjual=None,
                    confidence_score=0.0,
                    needs_review=True,
                    error=f"OCR processing failed: {str(e)}",
                    raw_text="",
                )
            ]

    async def process_image(self, image_path: str) -> List[OCRResult]:
        """Backward compatible alias for process_document."""
        return await self.process_document(image_path)

    async def mistral_ocr(self, image_path: str) -> str:
        """Extract text from image using Mistral Document AI Basic OCR."""

        try:
            image_file_path = Path(image_path)
            if not image_file_path.is_file():
                raise FileNotFoundError(f"Image not found at {image_file_path}")

            # Read file data once for upload
            with image_file_path.open("rb") as image_file:
                file_bytes = image_file.read()

            mime_type, _ = mimetypes.guess_type(image_file_path.name)
            if not mime_type:
                mime_type = "image/jpeg"

            if mime_type not in SUPPORTED_MIME_TYPES:
                raise ValueError(
                    "Unsupported file type for OCR. Please upload PDF, PNG, or JPG/JPEG"
                )

            headers = {"Authorization": f"Bearer {self.mistral_api_key}"}

            async with httpx.AsyncClient(timeout=60.0) as client:
                upload_response = await client.post(
                    MISTRAL_FILES_URL,
                    headers=headers,
                    data={"purpose": "ocr"},
                    files={
                        "file": (
                            image_file_path.name,
                            file_bytes,
                            mime_type,
                        )
                    },
                )
                upload_response.raise_for_status()
                file_id = upload_response.json().get("id")

                if not file_id:
                    raise ValueError("Mistral file upload response missing id")

                payload = {
                    "model": MISTRAL_DOCUMENT_AI_MODEL,
                    "document": {"type": "file", "file_id": file_id},
                }

                response = await client.post(
                    MISTRAL_DOCUMENT_AI_URL,
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()

            raw_text = _extract_document_ai_text(response.json())
            if not raw_text:
                logger.warning(
                    "Mistral Document AI returned no text for %s",
                    image_file_path.name,
                )
            else:
                logger.info(
                    "Mistral Document AI extracted %s characters from %s",
                    len(raw_text),
                    image_file_path.name,
                )
            return raw_text

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Mistral Document AI HTTP error %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            return ""
        except httpx.HTTPError as exc:
            logger.error(f"Mistral Document AI request failed: {exc}")
            return ""
        except Exception as e:
            logger.error(f"Mistral OCR error: {e}")
            return ""

    async def openai_extract_multi(self, raw_text: str) -> List[OCRResult]:
        """Extract all product lines from OCR text using OpenAI GPT-4o."""

        prompt = f"""Extract ALL products from this sales report:

{raw_text}

This is a multi-product sales report. Extract EVERY product line you can find.

For each product line, extract:
1. Product Name (copy the exact text from the line, including brand, variant, dosage, pack size, and any distinguishing text)
2. Quantity Sold (from QTY column or similar)

Important rules:
- Treat every physical line in the report as a separate entry EVEN if the product name repeats. Never merge or sum multiple lines.
- Preserve wording and numbers exactly as written so similar SKUs remain distinguishable (e.g., "7 DAYS" vs "30 DAYS").
- Youvit Anak was Youvit Multivitamin Kids, and Youvit Dewasa was Youvit Multivitamin Adults. The remaining product depends on the specifications.
- If a line appears twice, output two JSON objects (one per line) even if the details look identical.
- stock_terjual is mandatory (skip a line only if it truly has no quantity).
- confidence_score must describe your certainty for that specific line (0.0-1.0).

Return JSON with this structure:
{{
  "products": [
    {{
      "product_name": "YOUVIT OMEGA -3 ANAK 30 DAYS CANDY",
      "stock_terjual": 5,
      "confidence_score": 0.9
    }}
  ]
}}

DO NOT include markdown or commentary—return raw JSON only."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data extraction assistant. Extract every product from OCR text and respond with valid JSON arrays only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format=OPENAI_PRODUCTS_SCHEMA,
            )

            response_text = _normalize_response_content(
                response.choices[0].message.content
            )

            if not response_text:
                raise ValueError("OpenAI returned empty response content")

            data = _safe_parse_json_array(response_text)
            if not isinstance(data, list):
                raise ValueError("OpenAI response is not a JSON array")

            results: List[OCRResult] = []
            for item in data:
                if not isinstance(item, dict):
                    continue

                product_name = item.get("product_name")
                stock_terjual = item.get("stock_terjual")
                confidence_score = float(item.get("confidence_score", 0.0))

                stock_value: int | None
                if isinstance(stock_terjual, (int, float)):
                    stock_value = int(stock_terjual)
                elif isinstance(stock_terjual, str):
                    stock_value = (
                        int(stock_terjual) if stock_terjual.isdigit() else None
                    )
                else:
                    stock_value = None

                results.append(
                    OCRResult(
                        product_name=product_name,
                        stock_terjual=stock_value,
                        confidence_score=confidence_score,
                        needs_review=confidence_score < self.review_threshold,
                        raw_text=raw_text,
                    )
                )

            return results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}")
            return []


OPENAI_PRODUCTS_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "ocr_product_list",
        "schema": {
            "type": "object",
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "stock_terjual": {"type": ["number", "string"]},
                            "confidence_score": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                        },
                        "required": [
                            "product_name",
                            "stock_terjual",
                            "confidence_score",
                        ],
                        "additionalProperties": False,
                    },
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_sell_out": {"type": ["number", "string"]},
                        "sell_out_entries": {"type": ["number", "string"]},
                        "sell_out_rows": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "transaction": {"type": ["string", "null"]},
                                    "transaction_no": {"type": ["string", "null"]},
                                    "timestamp": {"type": ["string", "null"]},
                                    "description": {"type": ["string", "null"]},
                                    "stok_delta": {"type": ["string", "number"]},
                                },
                                "additionalProperties": True,
                            },
                        },
                        "skipped_entries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "reason": {"type": "string"},
                                },
                                "required": ["description", "reason"],
                                "additionalProperties": False,
                            },
                        },
                        "notes": {"type": "string"},
                    },
                    "additionalProperties": True,
                },
            },
            "required": ["products"],
            "additionalProperties": True,
        },
    },
}


K24_OCR_VISION_PROMPT = (
    "You are auditing an Apotek K-24 transaction history for a single SKU."
    " Focus on the 'Stok +/- (PCS)' column."
    "\nInstructions:\n"
    "1. Read the SKU name that appears above the table and return it as product_name.\n"
    "2. Identify every table row whose 'Stok +/- (PCS)' value is negative (has a '-' sign)."
    "   Those rows represent sell-out events. Ignore rows without a minus sign.\n"
    "3. For each sell-out row, capture the transaction number, timestamp, description,"
    "   and the raw negative value (e.g. -1). Store them in summary.sell_out_rows.\n"
    "4. Convert the negative values to positive quantities and sum them to produce"
    "   summary.total_sell_out. Double-check the arithmetic.\n"
    "5. Populate products with exactly ONE object describing this SKU and the"
    "   total sell-out quantity (stock_terjual = total_sell_out).\n"
    "6. Add summary.sell_out_entries for the number of negative rows processed,"
    "   summary.skipped_entries for non-negative rows you ignored (with reasons),"
    "   and summary.notes for any important observations."
    "7. Respond with pure JSON only (no markdown)."
)


class K24OpenAIOCRService:
    """OCR pipeline that uses OpenAI vision models directly on receipt images."""

    def __init__(
        self,
        openai_api_key: str,
        review_threshold: float = 0.7,
        vision_model: str = "gpt-4o",
        prompt: str | None = None,
    ):
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.review_threshold = review_threshold
        self.vision_model = vision_model
        self.prompt = prompt or K24_OCR_VISION_PROMPT

    async def process_document(self, image_path: str) -> dict:
        """Read a receipt image with OpenAI's vision model and return OCR results + summary."""

        try:
            data_url = self._encode_image(image_path)
            response = self.openai_client.chat.completions.create(
                model=self.vision_model,
                temperature=0.1,
                max_tokens=2048,
                response_format=OPENAI_PRODUCTS_SCHEMA,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a vision OCR assistant focused on structured JSON output.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"{self.prompt}\n"
                                    "Return raw JSON only with product_name, stock_terjual, confidence_score."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    },
                ],
            )

            response_text = _normalize_response_content(
                response.choices[0].message.content
            )
            if not response_text:
                raise ValueError("OpenAI vision response was empty")

            results, summary = self._parse_products(response_text)
            return {"results": results, "summary": summary}

        except Exception as exc:  # pragma: no cover - defensive path
            logger.error(f"K24 OpenAI OCR error: {exc}")
            return {
                "results": [
                    OCRResult(
                        product_name=None,
                        stock_terjual=None,
                        confidence_score=0.0,
                        needs_review=True,
                        error=f"K24 OCR processing failed: {exc}",
                        raw_text="",
                    )
                ],
                "summary": {
                    "llm_total_sell_out": None,
                    "calculated_total_sell_out": 0,
                    "notes": f"K24 OCR processing failed: {exc}",
                    "matches_llm_total": False,
                },
            }

    def _encode_image(self, image_path: str) -> str:
        image_file_path = Path(image_path)
        if not image_file_path.is_file():
            raise FileNotFoundError(f"Image not found at {image_file_path}")

        mime_type, _ = mimetypes.guess_type(image_file_path.name)
        if not mime_type:
            mime_type = "image/jpeg"

        if mime_type not in SUPPORTED_MIME_TYPES:
            raise ValueError("Unsupported file type for OCR. Upload PDF, PNG, or JPG/JPEG")

        encoded = base64.b64encode(image_file_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _parse_products(self, payload: str) -> Tuple[List[OCRResult], dict]:
        data = _parse_json_payload(payload)
        if isinstance(data, dict):
            raw_products = data.get("products", [])
            summary = data.get("summary", {})
        else:
            raw_products = data if isinstance(data, list) else []
            summary = {}

        summary_product_name = summary.get("product_name")
        if not summary_product_name and raw_products:
            first_name = (
                raw_products[0].get("product_name")
                if isinstance(raw_products[0], dict)
                else None
            )
            if first_name:
                summary_product_name = first_name

        results: List[OCRResult] = []
        for item in raw_products:
            if not isinstance(item, dict):
                continue

            item_name = item.get("product_name") or summary_product_name
            stock_terjual = item.get("stock_terjual")
            confidence_score = float(item.get("confidence_score", 0.0))

            stock_value = _coerce_int(stock_terjual)
            if isinstance(stock_value, int) and stock_value < 0:
                stock_value = abs(stock_value)

            results.append(
                OCRResult(
                    product_name=item_name,
                    stock_terjual=stock_value,
                    confidence_score=confidence_score,
                    needs_review=confidence_score < self.review_threshold,
                    raw_text="",
                )
            )

        sell_out_rows = summary.get("sell_out_rows")
        calculated_total = 0
        if isinstance(sell_out_rows, list) and sell_out_rows:
            for row in sell_out_rows:
                if not isinstance(row, dict):
                    continue
                delta = _coerce_int(row.get("stok_delta"))
                if delta is None:
                    continue
                calculated_total += abs(delta)
        else:
            calculated_total = sum(
                int(result.stock_terjual or 0)
                for result in results
                if result.stock_terjual is not None
            )

        llm_total = _coerce_int(summary.get("total_sell_out"))
        sell_out_entries = _coerce_int(summary.get("sell_out_entries"))

        info = {
            "product_name": summary_product_name or (results[0].product_name if results else None),
            "llm_total_sell_out": llm_total,
            "calculated_total_sell_out": calculated_total,
            "matches_llm_total": llm_total is None or llm_total == calculated_total,
            "sell_out_entry_count": (
                len(sell_out_rows)
                if isinstance(sell_out_rows, list)
                else len(results)
            ),
            "llm_sell_out_entry_count": sell_out_entries,
        }
        skipped = summary.get("skipped_entries")
        if isinstance(skipped, list) and skipped:
            info["skipped_entries"] = skipped
        if isinstance(sell_out_rows, list) and sell_out_rows:
            info["sell_out_rows"] = sell_out_rows
        if summary.get("notes"):
            info["notes"] = summary["notes"]

        if not info["matches_llm_total"]:
            logger.warning(
                "K24 OCR summary mismatch: LLM total %s vs calculated %s",
                llm_total,
                calculated_total,
            )

        return results, info
