"""Aggregate OCR extraction results by SKU for preview and submission."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from models.schemas import OCRResult

from .converter import ProductSKUConverter


class SKUAggregator:
    """Group OCR results by SKU and provide summary statistics."""

    def __init__(self, review_threshold: float = 0.7):
        self.review_threshold = review_threshold

    def aggregate(
        self, ocr_results: List[OCRResult], converter: ProductSKUConverter
    ) -> Dict[str, List[dict]]:
        matched_groups: Dict[str, dict] = defaultdict(
            lambda: {"quantities": [], "confidences": [], "entries": []}
        )
        unmatched: List[dict] = []
        entries: List[dict] = []

        for result in ocr_results:
            entry = {
                "product_name": result.product_name,
                "stock_terjual": result.stock_terjual,
                "confidence_score": result.confidence_score,
                "error": result.error,
            }

            if result.product_name and result.stock_terjual is not None:
                sku, sku_confidence, suggestions = converter.convert_with_confidence(
                    result.product_name
                )

                entry.update(
                    {
                        "sku_code": sku,
                        "sku_confidence": sku_confidence,
                        "suggestions": suggestions,
                        "needs_review": result.needs_review
                        or sku is None
                        or sku_confidence < self.review_threshold,
                    }
                )

                if sku:
                    matched_groups[sku]["quantities"].append(result.stock_terjual)
                    matched_groups[sku]["confidences"].append(sku_confidence)
                    matched_groups[sku]["entries"].append(
                        {
                            "name": result.product_name,
                            "qty": result.stock_terjual,
                            "conf": sku_confidence,
                            "ocr_conf": result.confidence_score,
                        }
                    )
                else:
                    unmatched.append(
                        {
                            "product_name": result.product_name,
                            "qty": result.stock_terjual,
                            "confidence_score": result.confidence_score,
                            "suggestions": suggestions,
                        }
                    )
            else:
                entry.update(
                    {
                        "sku_code": None,
                        "sku_confidence": 0.0,
                        "suggestions": [],
                        "needs_review": True,
                    }
                )

            entries.append(entry)

        matched: List[dict] = []
        for sku, data in matched_groups.items():
            count = len(data["quantities"])
            total_qty = sum(data["quantities"])
            avg_confidence = (
                sum(data["confidences"]) / count if count else 0.0
            )
            matched.append(
                {
                    "sku": sku,
                    "master_name": converter.get_master_name(sku) or sku,
                    "total_qty": total_qty,
                    "count": count,
                    "avg_confidence": avg_confidence,
                    "needs_review": avg_confidence < self.review_threshold,
                    "entries": data["entries"],
                }
            )

        matched.sort(key=lambda x: x["master_name"] or "")
        unmatched.sort(key=lambda x: x.get("product_name") or "")

        return {"matched": matched, "unmatched": unmatched, "entries": entries}
