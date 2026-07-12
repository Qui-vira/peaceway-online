"""Anthropic (Claude) vision provider for inventory photo analysis.

Sends the full photo batch in ONE request so the model can reconcile products
that appear across overlapping photos, and constrains the response with a
structured-output JSON schema. The payload is still re-validated locally by
``parse_scan_result`` before anything downstream sees it.
"""
from __future__ import annotations

import base64
from collections.abc import Sequence

from app.core.logging import get_logger
from app.services.inventory_vision.base import (
    InventoryVisionProvider,
    ScanImage,
    VisionProviderError,
    VisionResultError,
)
from app.services.inventory_vision.schemas import (
    SCAN_RESULT_JSON_SCHEMA,
    InventoryScanResult,
    parse_scan_result,
)

log = get_logger("inventory-vision")

SYSTEM_PROMPT = """\
You are a pharmacy inventory intake assistant for Peaceway Pharmacy. Staff send you \
photos of pharmacy products and shelves. Your ONLY job is stock intake: identify each \
distinct product, read what is printed on the packaging, and count the physical units \
visible across the whole photo batch.

The photo batch is ONE scene. The same physical items may appear in several photos \
(different angles, overlapping shots, close-ups). Follow these rules exactly:

COUNTING
- Count distinct physical units visible across ALL images combined.
- The same physical unit appearing again in another photo is NOT an extra unit. Use \
product identity, shelf position, neighbouring products, and image overlap to decide.
- Multiple separate physical units of the same product (same SKU) DO all count.
- A quantity printed on a pack (e.g. "50 sachets") is NOT the unit count; count the \
sealed packs/boxes/bottles you can actually see.
- Do not infer stock hidden behind other products or outside the frame.
- Explain in counting_notes how you counted and how overlap was handled.

READING LABELS
- Report product_name, dosage/strength, and other details ONLY when readable in the \
photos. If text is unclear, use null (dosage/description) or omit the product entirely \
rather than guessing a name.
- prescription: "Rx" only when the packaging clearly indicates prescription-only \
(e.g. POM, "prescription only"); "OTC" only when clearly an over-the-counter product; \
otherwise "uncertain". Never guess Rx status to complete a field.
- Do NOT invent medical indications, dosing instructions, or any medical advice.

CATEGORIES
- category must be exactly one of: Medicines, Medical Devices, Vaccines, Supplements, \
Veterinary, Other. Use Other when unsure.

CONFIDENCE
- identity_confidence: how certain the product identification is (label readability, \
brand recognisability).
- stock_count_confidence: how certain the unit count is, including how confident you \
are that overlapping photos were deduplicated correctly.
- Be honest: blurry labels, partial occlusion, or ambiguous overlap must lower the \
relevant confidence.

IMAGES
- Images are numbered starting at 0 in the order provided. Use those indexes in \
source_images and unreadable_images.
- If an image is too blurry/dark to use, list it in unreadable_images and add a warning.
"""

USER_INSTRUCTIONS = (
    "Analyse ALL of the images above as one batch and return the structured inventory "
    "scan result. Remember: deduplicate the same physical units across overlapping "
    "photos, count only what is visible, and never guess unreadable text."
)


class AnthropicVisionProvider(InventoryVisionProvider):
    def __init__(self, api_key: str, model: str = "claude-opus-4-8") -> None:
        import anthropic  # local import: dependency only needed when provider is used

        self._anthropic = anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def analyse_images(self, images: Sequence[ScanImage]) -> InventoryScanResult:
        if not images:
            raise VisionProviderError("No images to analyse.")

        content: list[dict] = []
        for i, img in enumerate(images):
            content.append({"type": "text", "text": f"Image {i}:"})
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.media_type,
                        "data": base64.standard_b64encode(img.data).decode("utf-8"),
                    },
                }
            )
        content.append({"type": "text", "text": USER_INSTRUCTIONS})

        anthropic = self._anthropic
        last_result_error: VisionResultError | None = None
        # One retry for a malformed payload; provider/API errors mapped to typed errors.
        for attempt in range(2):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=16000,
                    thinking={"type": "adaptive"},
                    system=SYSTEM_PROMPT,
                    output_config={
                        "format": {"type": "json_schema", "schema": SCAN_RESULT_JSON_SCHEMA}
                    },
                    messages=[{"role": "user", "content": content}],
                )
            except anthropic.AuthenticationError as exc:
                raise VisionProviderError(f"Anthropic auth failed: {exc}") from exc
            except anthropic.RateLimitError as exc:
                raise VisionProviderError("Anthropic rate limited.", retryable=True) from exc
            except anthropic.APIStatusError as exc:
                raise VisionProviderError(
                    f"Anthropic API error ({exc.status_code}).",
                    retryable=exc.status_code >= 500,
                ) from exc
            except anthropic.APIConnectionError as exc:
                raise VisionProviderError("Network error calling Anthropic.", retryable=True) from exc

            if response.stop_reason == "refusal":
                raise VisionProviderError("The vision model declined to analyse these images.")
            if response.stop_reason == "max_tokens":
                raise VisionResultError("Vision response was truncated (max_tokens).")

            text = next((b.text for b in response.content if b.type == "text"), "")
            log.info(
                "vision_provider_response",
                model=self._model,
                images=len(images),
                attempt=attempt,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            try:
                return parse_scan_result(text)
            except VisionResultError as exc:
                last_result_error = exc
                log.warning("vision_result_invalid", attempt=attempt, error=str(exc))

        raise last_result_error  # type: ignore[misc]  # loop always sets it before falling through
