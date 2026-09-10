import os

from storefront_verification.infrai_email import InfraiEmailClient
from storefront_verification.models import SignupRequest
from storefront_verification.signup_flow import StorefrontWorkflow


recipient = os.environ.get("DEMO_EMAIL_TO")
if not recipient:
    raise SystemExit("DEMO_EMAIL_TO is required")

workflow = StorefrontWorkflow(
    email_client=InfraiEmailClient(),
    signing_secret=os.environ.get("VERIFICATION_SIGNING_SECRET", "local-demo-secret"),
)
result = workflow.signup(
    SignupRequest(email=recipient, display_name="Ada"),
    public_base_url="http://localhost:8000",
)
print(result.model_dump_json(indent=2))

