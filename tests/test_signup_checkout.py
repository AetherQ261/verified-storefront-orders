from dataclasses import dataclass

import pytest

from storefront_verification.infrai_email import SentEmail
from storefront_verification.models import CheckoutLine, CheckoutRequest, SignupRequest
from storefront_verification.signup_flow import StorefrontWorkflow


@dataclass
class RecordedEmail:
    to: str
    subject: str
    html: str
    idempotency_key: str


class RecordingEmailClient:
    def __init__(self) -> None:
        self.sent: list[RecordedEmail] = []

    def send(self, *, to: str, subject: str, html: str, idempotency_key: str) -> SentEmail:
        self.sent.append(RecordedEmail(to, subject, html, idempotency_key))
        return SentEmail(message_id="msg_test_123", metadata={"provider": "test"})


def test_checkout_opens_only_after_email_verification() -> None:
    mailer = RecordingEmailClient()
    workflow = StorefrontWorkflow(mailer, signing_secret="test-secret")  # type: ignore[arg-type]
    signup = workflow.signup(
        SignupRequest(email="buyer@example.com", display_name="Ada & Co"),
        public_base_url="https://shop.example.com",
    )
    checkout = CheckoutRequest(
        customer_id=signup.customer_id,
        lines=[CheckoutLine(sku="mug-blue", quantity=2, unit_price_cents=1800)],
    )

    with pytest.raises(PermissionError, match="Verify"):
        workflow.checkout(checkout)

    email = mailer.sent[0]
    assert email.to == "buyer@example.com"
    assert email.idempotency_key == f"signup-verification:{signup.customer_id}"
    assert "Ada &amp; Co" in email.html
    token = email.html.split("token=", 1)[1].split('"', 1)[0]
    workflow.verify_email(signup.customer_id, token)

    order = workflow.checkout(checkout)
    assert order.fulfillment == "pending"
    assert order.receipt.total_cents == 3600
    assert order.customer_id == signup.customer_id

