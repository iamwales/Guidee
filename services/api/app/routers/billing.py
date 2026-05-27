from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.security import AuthUser, get_current_user
from app.models.schemas import BillingCheckoutRequest, BillingCheckoutResponse

router = APIRouter(prefix="/billing", tags=["billing"])

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
    price_id = {
        "pro": settings.stripe_price_pro,
        "team": settings.stripe_price_team,
    }.get(body.plan)
    if not price_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Stripe price is not configured for {body.plan}",
        )
    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
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
    if not settings.stripe_portal_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Billing portal not configured",
        )
    return {"url": settings.stripe_portal_url}


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
