import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.core.rate_limit import daily_agent_limit_for_plan
from app.core.security import _decode_token
from app.main import create_app
from app.routers import billing


class AuthBillingTests(unittest.IsolatedAsyncioTestCase):
    def test_dev_tokens_can_be_disabled_for_production(self):
        settings = Settings(app_env="production", allow_dev_tokens=False)

        with self.assertRaises(HTTPException) as ctx:
            _decode_token("dev:local-user", settings, {})

        self.assertEqual(ctx.exception.status_code, 401)

    def test_daily_agent_limits_follow_plan(self):
        settings = Settings(
            daily_agent_tasks_free=10,
            daily_agent_tasks_pro=100,
            daily_agent_tasks_team=500,
        )

        self.assertEqual(daily_agent_limit_for_plan("free", settings), 10)
        self.assertEqual(daily_agent_limit_for_plan("pro", settings), 100)
        self.assertEqual(daily_agent_limit_for_plan("team", settings), 500)

    def test_user_export_requires_auth(self):
        client = TestClient(create_app())

        response = client.get("/user/export")

        self.assertEqual(response.status_code, 401)

    async def test_checkout_webhook_updates_profile_plan(self):
        settings = Settings()
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_123",
                    "subscription": "sub_123",
                    "metadata": {"clerk_id": "user_123", "plan": "pro"},
                }
            },
        }

        with patch.object(
            billing.HistoryStore,
            "update_profile",
            new=AsyncMock(),
        ) as update_profile:
            await billing.apply_billing_event(event, settings)

        update_profile.assert_awaited_once_with(
            "user_123",
            plan="pro",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_123",
            subscription_status="active",
        )

    async def test_subscription_delete_downgrades_to_free(self):
        settings = Settings()
        event = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_123",
                    "status": "canceled",
                    "metadata": {"clerk_id": "user_123", "plan": "pro"},
                }
            },
        }

        with patch.object(
            billing.HistoryStore,
            "update_profile",
            new=AsyncMock(),
        ) as update_profile:
            await billing.apply_billing_event(event, settings)

        update_profile.assert_awaited_once_with(
            "user_123",
            plan="free",
            stripe_subscription_id="sub_123",
            subscription_status="canceled",
        )


if __name__ == "__main__":
    unittest.main()
