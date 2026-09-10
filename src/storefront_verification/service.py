import os

from fastapi import FastAPI, HTTPException, Request

from .infrai_email import InfraiEmailClient
from .models import CheckoutRequest, CustomerOrderUpdate, SignupRequest, SignupResult, VerificationResult
from .signup_flow import StorefrontWorkflow


def create_app(workflow: StorefrontWorkflow | None = None) -> FastAPI:
    app = FastAPI(title="Verified storefront orders")
    active_workflow = workflow or StorefrontWorkflow(
        email_client=InfraiEmailClient(),
        signing_secret=os.environ.get("VERIFICATION_SIGNING_SECRET", "local-development-secret"),
    )

    @app.post("/signup", response_model=SignupResult, status_code=201)
    def signup(body: SignupRequest, request: Request) -> SignupResult:
        return active_workflow.signup(body, str(request.base_url).rstrip("/"))

    @app.get("/verify-email", response_model=VerificationResult)
    def verify_email(customer_id: str, token: str) -> VerificationResult:
        try:
            return active_workflow.verify_email(customer_id, token)
        except (LookupError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/checkout", response_model=CustomerOrderUpdate, status_code=201)
    def checkout(body: CheckoutRequest) -> CustomerOrderUpdate:
        try:
            return active_workflow.checkout(body)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return app


app = create_app()

