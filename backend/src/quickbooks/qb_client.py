"""
QuickBooks Online OAuth2 client.

Handles authorization, token exchange, refresh, and API calls
to the Intuit QuickBooks Online Accounting API.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Intuit OAuth2 endpoints
INTUIT_AUTH_BASE = {
    "sandbox": "https://appcenter.intuit.com/connect/oauth2",
    "production": "https://appcenter.intuit.com/connect/oauth2",
}
INTUIT_TOKEN_URL = {
    "sandbox": "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
    "production": "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
}
QB_API_BASE = {
    "sandbox": "https://sandbox-quickbooks.api.intuit.com/v3",
    "production": "https://quickbooks.api.intuit.com/v3",
}

SCOPES = "com.intuit.quickbooks.accounting"


class QuickBooksClient:
    """OAuth2 client for QuickBooks Online."""

    def __init__(self):
        self.client_id = settings.quickbooks_client_id
        self.client_secret = settings.quickbooks_client_secret
        self.redirect_uri = settings.quickbooks_redirect_uri
        self.env = settings.quickbooks_environment

    @property
    def api_base(self) -> str:
        return QB_API_BASE[self.env]

    def get_authorization_url(self, state: str) -> str:
        """Generate the OAuth2 authorization URL for QuickBooks."""
        base = INTUIT_AUTH_BASE[self.env]
        params = (
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&scope={SCOPES}"
            f"&state={state}"
        )
        return base + params

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access + refresh tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                INTUIT_TOKEN_URL[self.env],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                auth=(self.client_id, self.client_secret),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
                "token_expires_at": datetime.utcnow()
                + timedelta(seconds=data["expires_in"]),
            }

    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                INTUIT_TOKEN_URL[self.env],
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                auth=(self.client_id, self.client_secret),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
                "token_expires_at": datetime.utcnow()
                + timedelta(seconds=data["expires_in"]),
            }

    async def api_request(
        self,
        method: str,
        realm_id: str,
        endpoint: str,
        access_token: str,
        json_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated API request to QuickBooks."""
        url = f"{self.api_base}/company/{realm_id}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method, url, headers=headers, json=json_data
            )
            resp.raise_for_status()
            return resp.json()

    async def get_company_info(
        self, realm_id: str, access_token: str
    ) -> Dict[str, Any]:
        """Get QuickBooks company info."""
        return await self.api_request(
            "GET", realm_id, "companyinfo/" + realm_id, access_token
        )

    async def get_accounts(
        self, realm_id: str, access_token: str
    ) -> List[Dict[str, Any]]:
        """Get chart of accounts from QuickBooks."""
        data = await self.api_request(
            "GET",
            realm_id,
            "query?query=SELECT * FROM Account WHERE AccountType = 'Expense' MAXRESULTS 1000",
            access_token,
        )
        return data.get("QueryResponse", {}).get("Account", [])

    async def get_vendors(
        self, realm_id: str, access_token: str
    ) -> List[Dict[str, Any]]:
        """Get vendors from QuickBooks."""
        data = await self.api_request(
            "GET",
            realm_id,
            "query?query=SELECT * FROM Vendor MAXRESULTS 1000",
            access_token,
        )
        return data.get("QueryResponse", {}).get("Vendor", [])

    async def create_purchase(
        self,
        realm_id: str,
        access_token: str,
        expense_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a purchase (expense) in QuickBooks."""
        return await self.api_request(
            "POST", realm_id, "purchase", access_token, json_data=expense_data
        )

    async def create_vendor(
        self,
        realm_id: str,
        access_token: str,
        vendor_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a vendor in QuickBooks."""
        return await self.api_request(
            "POST", realm_id, "vendor", access_token, json_data=vendor_data
        )
