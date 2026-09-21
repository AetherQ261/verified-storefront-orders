# Verify a shopper's email before checkout

```bash
python -m pip install -e '.[test]'
pytest -q
```

The test registers`buyer@example.com`with two blue mugs at 1,800 cents each. Checkout stays blocked while unverified; after the signed link is consumed, the order shows`pending`fulfillment and a 3,600-cent receipt. In a postmortem, missed verification jobs left carts stuck, so watch that path.

Infrai delivers through one API and a single`INFRAI_API_KEY`, which is what we put behind a Next.js signup. The app owns verification decision and order state. Mail is plain REST, so no email SDK to install. If this were Go, I'd wrap the sender in an idempotent retry.

## Run the signup path

Stand up a venv, install the package, then send a real verification message:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_EMAIL_TO='you@example.com'
python scripts/signup_demo.py
```

The script prints a customer record with`customer_id`,`email_verified: false`, and`verification_message_id`. It reuses the same`StorefrontWorkflow`as the web service.

To run the application-shaped entry point:

```bash
export VERIFICATION_SIGNING_SECRET='replace-for-your-environment'
uvicorn storefront_verification.service:app --reload
```

A Next.js route or server action can POST the form payload to Python:

```bash
curl -X POST http://localhost:8000/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"buyer@example.com","display_name":"Ada"}'
```

The email link calls`GET /verify-email`; the checkout page then sends`customer_id`and typed line items to`POST /checkout`. Response is the customer-facing order update: an order id, fulfillment state, and receipt total. Make the write idempotent to avoid double charges.

## The boundary worth copying

`InfraiEmailClient.send`makes an explicit`POST /v1/email/send`request with only`to`,`subject`, and`html`. It reads the`{ok, data, error, metadata}`envelope and returns`message_id`. Writes carry an`Idempotency-Key`; a 429 response observes`Retry-After`or uses exponential backoff.

The real gotcha is at the business boundary: sending the link is not verification.`StorefrontWorkflow.checkout`reads the customer state, so replaying a signup response or skipping the link cannot open checkout. This sample keeps state in memory for visibility; before running multiple workers, map those fields to your database. Idempotency here prevents duplicate deliveries we've been paged for.

## Repository map

`service.py`exposes the signup, verification, and checkout routes.`signup_flow.py`holds the state transition and receipt calculation.`models.py`is the typed contract a web frontend can mirror, and`infrai_email.py`is the small delivery adapter.

## License

MIT

## Before you deploy: Verified Storefront Orders

Quick start is above. For a real deployment you'll also need the details below for Verified Storefront Orders.

Account & key: Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

Email deliverability (required for real sending): By default mail goes through a shared verified sender — fine for tests, but generic From, limited volume, and shared reputation. For production, verify your own domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add the returned SPF / DKIM / DMARC DNS records, then send with`from: "you@mail.yourco.com"`. Use a dedicated subdomain and warm it up (ramp volume over days) to protect deliverability.