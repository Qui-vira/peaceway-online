"""Product image storage, serving, and catalog exposure.

Covers app/services/file_storage.py, app/api/v1/media.py, and the image_url field
that the storefront reads.
"""
from __future__ import annotations

import io
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.main import app
from app.models import Base, MediaAsset, Product, ProductPricing
from app.services import file_storage


def _png_bytes(width: int = 100, height: int = 100, colour=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buf, format="PNG")
    return buf.getvalue()


# ── Normalization ─────────────────────────────────────────────────────────────
def test_normalize_converts_to_webp():
    data, w, h = file_storage.normalize_image(_png_bytes())
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    assert (w, h) == (100, 100)


def test_normalize_downscales_long_edge_to_800():
    _, w, h = file_storage.normalize_image(_png_bytes(2400, 1200))
    assert w == 800
    assert h == 400  # aspect ratio preserved


def test_normalize_leaves_small_images_alone():
    _, w, h = file_storage.normalize_image(_png_bytes(300, 200))
    assert (w, h) == (300, 200)


def test_normalize_strips_exif():
    """Phone photos carry GPS. These images are public — the metadata must not survive."""
    buf = io.BytesIO()
    img = Image.new("RGB", (50, 50), (10, 10, 10))
    exif = img.getexif()
    exif[271] = "SecretCameraMake"  # Make
    img.save(buf, format="JPEG", exif=exif)
    assert b"SecretCameraMake" in buf.getvalue()

    data, _, _ = file_storage.normalize_image(buf.getvalue())
    assert b"SecretCameraMake" not in data
    assert not Image.open(io.BytesIO(data)).getexif()


def test_normalize_rejects_non_image():
    with pytest.raises(file_storage.ImageRejected):
        file_storage.normalize_image(b"this is definitely not a png")


# ── Storage + dedup ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_store_image_persists_asset(db_session: AsyncSession):
    asset = await file_storage.store_image(db_session, _png_bytes(), uploaded_by=555)
    assert asset.content_type == "image/webp"
    assert asset.byte_size == len(asset.data)
    assert len(asset.sha256) == 64
    assert asset.uploaded_by_telegram_id == 555


@pytest.mark.asyncio
async def test_store_image_dedups_identical_bytes(db_session: AsyncSession):
    raw = _png_bytes()
    first = await file_storage.store_image(db_session, raw)
    second = await file_storage.store_image(db_session, raw)
    assert first.id == second.id


@pytest.mark.asyncio
async def test_store_image_dedups_across_source_formats(db_session: AsyncSession):
    """Same picture as PNG and as JPEG normalizes to the same WebP, so one row."""
    png = _png_bytes(64, 64, (7, 7, 7))
    jpg_buf = io.BytesIO()
    Image.open(io.BytesIO(png)).save(jpg_buf, format="JPEG", quality=100)

    a = await file_storage.store_image(db_session, png)
    b = await file_storage.store_image(db_session, jpg_buf.getvalue())
    assert a.sha256 == b.sha256
    assert a.id == b.id


@pytest.mark.asyncio
async def test_get_asset_returns_none_for_unknown(db_session: AsyncSession):
    assert await file_storage.get_asset(db_session, uuid4()) is None


# ── HTTP serving + catalog exposure ───────────────────────────────────────────
@pytest_asyncio.fixture
async def client_and_maker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, maker

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_product(maker, *, with_image: bool) -> tuple[str, str | None]:
    async with maker() as s:
        asset = None
        if with_image:
            asset = await file_storage.store_image(s, _png_bytes(), uploaded_by=1)
        product = Product(
            name="Afrab Loratadine Syrup",
            generic_name="Loratadine",
            dosage_form="Syrup",
            is_listed=True,
            requires_prescription=False,
            requires_review=False,
            image_id=asset.id if asset else None,
        )
        product.pricing = ProductPricing(
            selling_price=Decimal("600"), stock_qty=5, is_in_stock=True
        )
        s.add(product)
        await s.commit()
        return str(product.id), (str(asset.id) if asset else None)


@pytest.mark.asyncio
async def test_media_endpoint_serves_bytes(client_and_maker):
    client, maker = client_and_maker
    _, asset_id = await _seed_product(maker, with_image=True)

    resp = await client.get(f"/api/v1/media/{asset_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"
    assert resp.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert resp.content[:4] == b"RIFF"


@pytest.mark.asyncio
async def test_media_endpoint_304_on_matching_etag(client_and_maker):
    client, maker = client_and_maker
    _, asset_id = await _seed_product(maker, with_image=True)

    first = await client.get(f"/api/v1/media/{asset_id}")
    etag = first.headers["etag"]

    second = await client.get(
        f"/api/v1/media/{asset_id}", headers={"If-None-Match": etag}
    )
    assert second.status_code == 304
    assert second.content == b""


@pytest.mark.asyncio
async def test_media_endpoint_404_for_unknown_asset(client_and_maker):
    client, _ = client_and_maker
    resp = await client.get(f"/api/v1/media/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_catalog_exposes_image_url_when_set(client_and_maker):
    client, maker = client_and_maker
    product_id, asset_id = await _seed_product(maker, with_image=True)

    resp = await client.get(f"/api/v1/catalog/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["image_url"] == f"/api/v1/media/{asset_id}"


@pytest.mark.asyncio
async def test_catalog_image_url_is_null_without_photo(client_and_maker):
    client, maker = client_and_maker
    product_id, _ = await _seed_product(maker, with_image=False)

    resp = await client.get(f"/api/v1/catalog/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["image_url"] is None


@pytest.mark.asyncio
async def test_catalog_list_includes_image_url(client_and_maker):
    client, maker = client_and_maker
    _, asset_id = await _seed_product(maker, with_image=True)

    resp = await client.get("/api/v1/catalog")
    assert resp.status_code == 200
    assert resp.json()[0]["image_url"] == f"/api/v1/media/{asset_id}"


@pytest.mark.asyncio
async def test_serving_an_asset_does_not_require_a_product(client_and_maker):
    """Assets are standalone; clearing a product's image must not orphan the bytes."""
    client, maker = client_and_maker
    async with maker() as s:
        asset = await file_storage.store_image(s, _png_bytes())
        await s.commit()
        asset_id = asset.id

    assert (await client.get(f"/api/v1/media/{asset_id}")).status_code == 200
    async with maker() as s:
        assert await s.get(MediaAsset, asset_id) is not None
