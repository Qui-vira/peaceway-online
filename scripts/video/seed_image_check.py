"""Seed the scratch verification DB with two products: one photographed, one not.

Verification fixture only — the image is a generated placeholder that says so, not a
real medicine photo. Real photos come from staff via the Telegram flow.

Run with DATABASE_URL pointing at the scratch database.
"""
from __future__ import annotations

import asyncio
import io
from decimal import Decimal

from PIL import Image, ImageDraw

from app.core.db import get_session
from app.models import Product, ProductPricing
from app.services import file_storage


def _fixture_image() -> bytes:
    """A labelled placeholder, so nobody mistakes this screenshot for a real photo."""
    img = Image.new("RGB", (1400, 1400), (238, 240, 236))
    d = ImageDraw.Draw(img)
    d.rectangle([140, 300, 1260, 1100], fill=(255, 255, 255), outline=(20, 90, 55), width=14)
    d.rectangle([140, 300, 1260, 470], fill=(20, 120, 70))
    d.text((190, 370), "TEST FIXTURE", fill=(255, 255, 255))
    d.text((190, 560), "NOT A REAL PRODUCT PHOTO", fill=(30, 30, 30))
    d.text((190, 640), "verifies image pipeline only", fill=(90, 90, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


async def main() -> None:
    async with get_session() as s:
        asset = await file_storage.store_image(s, _fixture_image(), uploaded_by=1)

        with_photo = Product(
            name="Afrab Loratadine Syrup",
            generic_name="Loratadine",
            dosage_form="Syrup",
            strength="5 mg/5 mL",
            category="Medicines",
            is_listed=True,
            requires_prescription=False,
            requires_review=False,
            image_id=asset.id,
        )
        with_photo.pricing = ProductPricing(
            selling_price=Decimal("600"), cost_price=Decimal("400"),
            stock_qty=12, is_in_stock=True,
        )

        without_photo = Product(
            name="Cal D3 Tablet",
            generic_name="Calcium + Vitamin D3",
            dosage_form="Tablet",
            strength="1250 mg; 250 IU",
            category="Supplements",
            is_listed=True,
            requires_prescription=False,
            requires_review=False,
        )
        without_photo.pricing = ProductPricing(
            selling_price=Decimal("1300"), cost_price=Decimal("900"),
            stock_qty=8, is_in_stock=True,
        )

        s.add_all([with_photo, without_photo])
        await s.commit()

        print(f"asset       : {asset.id} ({asset.byte_size} bytes, {asset.width}x{asset.height})")
        print(f"with photo  : {with_photo.id}  {with_photo.name}")
        print(f"without     : {without_photo.id}  {without_photo.name}")


if __name__ == "__main__":
    asyncio.run(main())
