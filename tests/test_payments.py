import pytest
from src.payments import PaymentService, PaymentError


@pytest.fixture
def service():
    return PaymentService(api_key="sk_test_dummy", livemode=False)


@pytest.fixture
def customer(service):
    return service.create_customer(email="test@example.com")


def test_successful_charge(service, customer):
    charge = service.charge(
        customer_id=customer["id"],
        amount=2500,  # $25.00
        currency="usd",
        description="Test charge",
    )
    assert charge["status"] == "succeeded"
    assert charge["amount"] == 2500
    assert charge["currency"] == "usd"
    assert "id" in charge
    assert len(charge["id"]) > 0


def test_declined_payment(service, customer):
    with pytest.raises(PaymentError) as exc_info:
        service.charge(
            customer_id=customer["id"],
            amount=99999,
            currency="usd",
            description="Always-declined test charge",
            idempotency_key="decline_test_001",
        )
    assert exc_info.value.code == "card_declined"
    assert exc_info.value.decline_code == "insufficient_funds"


def test_refund(service, customer):
    charge = service.charge(
        customer_id=customer["id"],
        amount=1000,
        currency="usd",
        description="Refund test charge",
    )
    refund = service.refund(charge_id=charge["id"], amount=500)
    assert refund["status"] == "succeeded"
    assert refund["amount"] == 500
    assert refund["charge_id"] == charge["id"]


def test_refund_full_amount(service, customer):
    charge = service.charge(
        customer_id=customer["id"],
        amount=1500,
        currency="eur",
        description="Full refund test",
    )
    refund = service.refund(charge_id=charge["id"])
    assert refund["status"] == "succeeded"
    assert refund["amount"] == 1500
