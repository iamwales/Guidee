from typing import Annotated

import stripe
from app.core.config import Settings, get_settings
from app.core.security import AuthUser, get_current_user
from app.models.schemas import BillingCheckoutRequest, BillingCheckoutResponse
from fastapi import APIRouter, Depends, HTTPException, Request, status

router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_PRICES = {
    "pro": None,  # Set via STRIPE_PRICE_PRO env in production
    "team": None,
}


@router.post("/checkout", response_model=BillingCheckoutResponse)
async def create_checkout(
    body: BillingCheckoutRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if not settings.stripe_secret_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Billing not configured",
        )
    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": body.plan, "quantity": 1}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"clerk_id": user.clerk_id, "plan": body.plan},
    )
    return BillingCheckoutResponse(url=session.url)


@router.post("/portal")
async def billing_portal(
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _ = user
    if not settings.stripe_secret_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Billing not configured",
        )
    return {"url": "https://billing.stripe.com/p/login/test"}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    if not settings.stripe_webhook_secret:
        return {"received": True}
    try:
        stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return {"received": True}
