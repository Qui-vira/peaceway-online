from decimal import Decimal

from app.models.orders import PaymentMethod
from app.services.pricing import FeeConfig, QuoteItem, quote_order


def _items():
    return [QuoteItem(name="Drug A", quantity=2, selling_price=Decimal("1000"), cost_price=Decimal("600"))]


def test_basic_quote_adds_fees_on_top():
    q = quote_order(
        _items(),
        delivery_fee=Decimal("1500"),
        fees=FeeConfig(payment_fee_pct=Decimal("1.5")),
        payment_method=PaymentMethod.BANK_TRANSFER,
    )
    assert q.subtotal == Decimal("2000.00")
    assert q.delivery_fee == Decimal("1500.00")
    assert q.payment_fee == Decimal("30.00")  # 1.5% of 2000
    assert q.total == Decimal("3530.00")  # 2000 + 1500 + 30


def test_profit_is_independent_of_fees():
    q = quote_order(
        _items(),
        delivery_fee=Decimal("5000"),
        fees=FeeConfig(payment_fee_pct=Decimal("3"), payment_fee_flat=Decimal("100"), handling_fee=Decimal("200")),
        payment_method=PaymentMethod.FLUTTERWAVE,
    )
    # Profit = (1000-600)*2 = 800, regardless of how large the fees are.
    assert q.product_profit == Decimal("800.00")


def test_flat_plus_percentage_payment_fee():
    q = quote_order(
        _items(),
        delivery_fee=Decimal("0"),
        fees=FeeConfig(payment_fee_pct=Decimal("2"), payment_fee_flat=Decimal("50")),
        payment_method=PaymentMethod.FLUTTERWAVE,
    )
    # 50 flat + 2% of 2000 (=40) = 90
    assert q.payment_fee == Decimal("90.00")
    assert q.total == Decimal("2090.00")


def test_offramp_fee_only_for_crypto():
    fees = FeeConfig(offramp_fee=Decimal("500"))
    bank = quote_order(_items(), Decimal("0"), fees, PaymentMethod.BANK_TRANSFER)
    crypto = quote_order(_items(), Decimal("0"), fees, PaymentMethod.CRYPTO)
    assert bank.offramp_fee == Decimal("0.00")
    assert crypto.offramp_fee == Decimal("500.00")
    assert crypto.total == Decimal("2500.00")


def test_handling_fee_added():
    q = quote_order(
        _items(),
        delivery_fee=Decimal("1000"),
        fees=FeeConfig(handling_fee=Decimal("250")),
        payment_method=PaymentMethod.BANK_TRANSFER,
    )
    assert q.handling_fee == Decimal("250.00")
    assert q.total == Decimal("3250.00")  # 2000 + 1000 + 250
