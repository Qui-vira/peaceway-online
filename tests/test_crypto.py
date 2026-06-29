from decimal import Decimal

from app.core.config import Settings
from app.models import FeeSetting, Order
from app.services.payments import crypto


class _FakeSettings(Settings):
    pass


def test_crypto_disabled_when_flag_off(monkeypatch):
    fee = FeeSetting(id=1, enable_crypto=False)
    assert crypto.crypto_enabled(fee) is False


def test_crypto_disabled_without_wallets(monkeypatch):
    fee = FeeSetting(id=1, enable_crypto=True)
    monkeypatch.setattr(crypto, "get_settings", lambda: Settings(crypto_wallets="", _env_file=None))
    assert crypto.crypto_enabled(fee) is False


def test_crypto_enabled_with_flag_and_wallet(monkeypatch):
    fee = FeeSetting(id=1, enable_crypto=True)
    monkeypatch.setattr(
        crypto, "get_settings", lambda: Settings(crypto_wallets="TRON:USDT:Tabc123", _env_file=None)
    )
    assert crypto.crypto_enabled(fee) is True
    wallets = crypto.available_wallets()
    assert wallets == [{"network": "TRON", "token": "USDT", "address": "Tabc123"}]


def test_total_with_offramp_adds_fee_on_top():
    fee = FeeSetting(id=1, offramp_fee=Decimal("500"))
    order = Order(
        code="PW-TEST00",
        subtotal=Decimal("2000"),
        delivery_fee=Decimal("700"),
        payment_fee=Decimal("30"),
        handling_fee=Decimal("0"),
    )
    # 2000 + 700 + 30 + 0 + 500 offramp = 3230
    assert crypto.total_with_offramp(order, fee) == Decimal("3230")
