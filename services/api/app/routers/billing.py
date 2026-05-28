from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.security import AuthUser, get_current_user
from app.models.schemas import (
    BillingCheckoutRequest,
    BillingCheckoutResponse,
    BillingPortalResponse,
)
from app.services.history import HistoryStore

router = APIRouter(prefix="/billing", tags=["billing"])


def price_for_plan(plan: str, settings: Settings) -> str:
    return {
        "pro": settings.stripe_price_pro,
        "team": settings.stripe_price_team,
    }.get(plan, "")


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
    price_id = price_for_plan(body.plan, settings)
    if not price_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Stripe price is not configured for {body.plan}",
        )
    stripe.api_key = settings.stripe_secret_key
    store = HistoryStore(settings)
    profile = await store.get_or_create_profile(
        user_id=user.clerk_id,
        email=user.email,
        plan=user.plan,
    )
    checkout_args = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": body.success_url,
        "cancel_url": body.cancel_url,
        "metadata": {"clerk_id": user.clerk_id, "plan": body.plan},
        "subscription_data": {
            "metadata": {"clerk_id": user.clerk_id, "plan": body.plan}
        },
    }
    if profile.get("stripe_customer_id"):
        checkout_args["customer"] = str(profile["stripe_customer_id"])
    elif user.email:
        checkout_args["customer_email"] = user.email
    session = stripe.checkout.Session.create(**checkout_args)
    return BillingCheckoutResponse(url=session.url)


@router.post("/portal", response_model=BillingPortalResponse)
async def billing_portal(
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BillingPortalResponse:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Billing not configured",
        )
    profile = await HistoryStore(settings).get_profile(user.clerk_id)
    customer_id = profile.get("stripe_customer_id") if profile else None
    if customer_id:
        stripe.api_key = settings.stripe_secret_key
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=settings.stripe_customer_portal_return_url,
        )
        return BillingPortalResponse(url=session.url)
    if not settings.stripe_portal_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Billing portal not configured",
        )
    return BillingPortalResponse(url=settings.stripe_portal_url)


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
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    await apply_billing_event(dict(event), settings)
    return {"received": True}


async def apply_billing_event(event: dict, settings: Settings) -> None:
    data = event.get("data", {}).get("object", {})
    event_type = event.get("type")
    store = HistoryStore(settings)
    if event_type == "checkout.session.completed":
        clerk_id = data.get("metadata", {}).get("clerk_id")
        plan = data.get("metadata", {}).get("plan", "pro")
        if clerk_id:
            await store.update_profile(
                str(clerk_id),
                plan=plan,
                stripe_customer_id=data.get("customer"),
                stripe_subscription_id=data.get("subscription"),
                subscription_status="active",
            )
    elif event_type in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        clerk_id = data.get("metadata", {}).get("clerk_id")
        status_value = data.get("status", "inactive")
        plan = data.get("metadata", {}).get("plan", "free")
        if event_type == "customer.subscription.deleted" or status_value not in {
            "active",
            "trialing",
        }:
            plan = "free"
        if clerk_id:
            await store.update_profile(
                str(clerk_id),
                plan=plan,
                stripe_subscription_id=data.get("id"),
                subscription_status=status_value,
            )
