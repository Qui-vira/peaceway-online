"""Structured result schema for inventory photo analysis.

The AI response is never trusted directly: the raw payload must pass through
``parse_scan_result`` (pydantic, strict) before the pipeline uses it. The same
JSON Schema (``SCAN_RESULT_JSON_SCHEMA``) is sent to the provider as an output
constraint so a well-behaved provider can only produce valid shapes.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.services.products_admin import VALID_CATEGORIES


class DetectedProduct(BaseModel):
    """One distinct physical product detected across the photo batch."""

    temporary_id: str = ""
    product_name: str = Field(min_length=1, max_length=255)
    category: str
    stock: int = Field(ge=0)
    dosage: str | None = None
    prescription: Literal["OTC", "Rx", "uncertain"] = "uncertain"
    description: str | None = None
    identity_confidence: float = Field(ge=0.0, le=1.0)
    stock_count_confidence: float = Field(ge=0.0, le=1.0)
    source_images: list[int] = Field(default_factory=list)
    counting_notes: str = ""

    @field_validator("product_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("product_name must not be blank")
        return v[:255]

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        # Only the fixed Peaceway categories are allowed — never invent one.
        for cat in VALID_CATEGORIES:
            if v.strip().lower() == cat.lower():
                return cat
        raise ValueError(f"category must be one of {VALID_CATEGORIES}")

    @field_validator("dosage", "description")
    @classmethod
    def _empty_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class InventoryScanResult(BaseModel):
    """Validated top-level analysis result."""

    products: list[DetectedProduct] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unreadable_images: list[int] = Field(default_factory=list)


def parse_scan_result(raw: str | dict) -> InventoryScanResult:
    """Validate a raw provider payload. Raises VisionResultError on anything invalid."""
    from app.services.inventory_vision.base import VisionResultError

    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError) as exc:
        raise VisionResultError(f"Provider returned malformed JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise VisionResultError("Provider result must be a JSON object.")
    try:
        return InventoryScanResult.model_validate(data)
    except ValidationError as exc:
        raise VisionResultError(f"Provider result failed schema validation: {exc}") from exc


# JSON Schema sent to the provider as a structured-output constraint.
# Note: numeric range constraints are unsupported by structured outputs, so
# ranges are enforced by the pydantic layer above instead.
SCAN_RESULT_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "temporary_id": {
                        "type": "string",
                        "description": "Stable id for this detection, e.g. scan_item_001.",
                    },
                    "product_name": {
                        "type": "string",
                        "description": "Product name exactly as readable on packaging. Never guess unreadable names.",
                    },
                    "category": {"enum": list(VALID_CATEGORIES)},
                    "stock": {
                        "type": "integer",
                        "description": "Count of distinct physical units visible across ALL images, deduplicated across overlapping photos.",
                    },
                    "dosage": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "description": "Strength/dosage as printed, or null when not readable. Never guess.",
                    },
                    "prescription": {"enum": ["OTC", "Rx", "uncertain"]},
                    "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "identity_confidence": {
                        "type": "number",
                        "description": "0-1: how certain the product identification is (name/label readability).",
                    },
                    "stock_count_confidence": {
                        "type": "number",
                        "description": "0-1: how certain the unit count is, including duplicate-detection certainty.",
                    },
                    "source_images": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "0-based indexes of the images this product appears in.",
                    },
                    "counting_notes": {
                        "type": "string",
                        "description": "How the count was derived, incl. overlap handling.",
                    },
                },
                "required": [
                    "temporary_id",
                    "product_name",
                    "category",
                    "stock",
                    "dosage",
                    "prescription",
                    "description",
                    "identity_confidence",
                    "stock_count_confidence",
                    "source_images",
                    "counting_notes",
                ],
                "additionalProperties": False,
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
        "unreadable_images": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "0-based indexes of images too unclear to analyse.",
        },
    },
    "required": ["products", "warnings", "unreadable_images"],
    "additionalProperties": False,
}
