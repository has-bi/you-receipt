"""Product name to SKU converter with aggressive normalization and fuzzy matching."""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from models.schemas import SKUConversionResult

logger = logging.getLogger(__name__)


class ProductSKUConverter:
    """Intelligent SKU matcher that handles Indonesian/English variations."""

    KEYWORD_RULES = {
        "omega": {"candidate_requires_input": 0.4, "input_requires_candidate": 0.6},
        "collagen": {"candidate_requires_input": 0.5, "input_requires_candidate": 0.6},
        "beauti": {"candidate_requires_input": 0.5, "input_requires_candidate": 0.6},
    }

    LANGUAGE_MAP = {
        "anak": "kids",
        "dewasa": "adult",
        "multivitamin": "mltvmn",
        "vitamin": "vit",
        "gummy": "gummy",
        "collagen": "collagen",
        "omega": "omega",
        "beauty": "beauti",
    }

    NOISE_WORDS = {
        "candy",
        "gummy",
        "tablet",
        "kapsul",
        "caplet",
        "the",
        "and",
        "for",
        "with",
    }

    DAY_PATTERNS = [
        (r"(\d+)\s*day'?s?", r"\1days"),
        (r"(\d+)'?s", r"\1days"),
    ]

    def __init__(self, mapping: Dict[str, str], threshold: float = 0.75):
        self.mapping = mapping
        self.threshold = threshold
        self._build_indexes()

    def _build_indexes(self) -> None:
        self.lower_mapping = {
            name.lower(): (name, sku) for name, sku in self.mapping.items()
        }
        self.normalized_master = {
            name: self._normalize(name) for name in self.mapping.keys()
        }
        self.normalized_lookup = {}
        self.master_tokens: Dict[str, set[str]] = {}
        for name, normalized in self.normalized_master.items():
            self.normalized_lookup[normalized] = (name, self.mapping[name])
            self.master_tokens[name] = set(filter(None, normalized.split()))
        self.sku_to_master: Dict[str, str] = {}
        for name, sku in self.mapping.items():
            self.sku_to_master.setdefault(sku, name)

    def _normalize(self, text: str) -> str:
        if not text:
            return ""

        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)

        words = text.split()
        translated = [self.LANGUAGE_MAP.get(word, word) for word in words]
        text = " ".join(translated)

        for pattern, replacement in self.DAY_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        words = [w for w in text.split() if w not in self.NOISE_WORDS]
        text = " ".join(words)

        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _similarity(self, str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1, str2).ratio()

    def convert(self, product_name: str) -> SKUConversionResult:
        sku, confidence, suggestions = self.convert_with_confidence(product_name)

        remaining_suggestions = suggestions[1:] if len(suggestions) > 1 else []
        return SKUConversionResult(
            sku_code=sku,
            confidence=confidence,
            suggestions=remaining_suggestions,
        )

    def convert_with_confidence(
        self, product_name: str
    ) -> tuple[Optional[str], float, List[Tuple[str, str, float]]]:
        if not product_name or not product_name.strip():
            return None, 0.0, []

        product_name = product_name.strip()

        # Exact match
        if product_name in self.mapping:
            sku = self.mapping[product_name]
            return sku, 1.0, [(product_name, sku, 1.0)]

        # Case-insensitive match
        lower = product_name.lower()
        if lower in self.lower_mapping:
            original, sku = self.lower_mapping[lower]
            return sku, 0.95, [(original, sku, 0.95)]

        normalized_input = self._normalize(product_name)
        if not normalized_input:
            return None, 0.0, []

        # Exact normalized match
        if normalized_input in self.normalized_lookup:
            original, sku = self.normalized_lookup[normalized_input]
            return sku, 0.9, [(original, sku, 0.9)]

        suggestions = self.get_suggestions(product_name, n=5, _normalized_input=normalized_input)
        if not suggestions:
            return None, 0.0, []

        top_name, top_sku, top_score = suggestions[0]
        final_sku = top_sku if top_score >= self.threshold else None
        return final_sku, top_score, suggestions

    def get_suggestions(
        self,
        product_name: str,
        n: int = 5,
        _normalized_input: Optional[str] = None,
    ) -> List[Tuple[str, str, float]]:
        if _normalized_input is not None:
            normalized_input = _normalized_input
        else:
            if not product_name or not product_name.strip():
                return []
            normalized_input = self._normalize(product_name.strip())
            if not normalized_input:
                return []

        input_tokens = set(filter(None, normalized_input.split()))
        scores: List[Tuple[str, str, float]] = []
        for original_name, normalized_master in self.normalized_master.items():
            candidate_tokens = self.master_tokens.get(original_name, set())
            score = self._score_candidate(
                normalized_input, normalized_master, input_tokens, candidate_tokens
            )
            scores.append((original_name, self.mapping[original_name], score))

        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:n]

    def get_sku(self, product_name: str) -> Optional[str]:
        sku, _, _ = self.convert_with_confidence(product_name)
        return sku

    def get_master_name(self, sku_code: str) -> Optional[str]:
        return self.sku_to_master.get(sku_code)

    def update_mapping(self, new_mapping: Dict[str, str]):
        self.mapping = new_mapping
        self._build_indexes()
        logger.info(f"Updated mapping with {len(new_mapping)} products")

    def _score_candidate(
        self,
        normalized_input: str,
        normalized_master: str,
        input_tokens: set[str],
        candidate_tokens: set[str],
    ) -> float:
        base = self._similarity(normalized_input, normalized_master)
        keyword_penalty = self._keyword_penalty(input_tokens, candidate_tokens)
        return base * keyword_penalty

    def _keyword_penalty(
        self, input_tokens: set[str], candidate_tokens: set[str]
    ) -> float:
        penalty = 1.0
        for keyword, rules in self.KEYWORD_RULES.items():
            if keyword in candidate_tokens and keyword not in input_tokens:
                penalty *= rules.get("candidate_requires_input", 1.0)
            if keyword in input_tokens and keyword not in candidate_tokens:
                penalty *= rules.get("input_requires_candidate", 1.0)
        return penalty
