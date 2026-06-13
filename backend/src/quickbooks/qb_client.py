"""
QuickBooks Online OAuth2 client.

Handles authorization, token exchange, refresh, and API calls
to the Intuit QuickBooks Online Accounting API.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Intuit rate limit: 500 requests per minute per realm
_QB_MAX_RETRIES = 3
_QB_RETRY_BASE_DELAY = 1.0  # seconds


class QuickBooksAPIError(Exception):
    """Base exception for QuickBooks API errors."""

    def __init__(self, message: str, status_code: int = 0, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class QuickBooksAuthError(QuickBooksAPIError):
    """Token revoked or invalid — re-authentication required."""

    def __init__(self, message: str = "QuickBooks authentication failed"):
        super().__init__(message, status_code=401, retryable=False)


class QuickBooksRateLimitError(QuickBooksAPIError):
    """Rate limit exceeded — should retry with backoff."""

    def __init__(self, retry_after: float = 60.0):
        super().__init__(
            "QuickBooks rate limit exceeded", status_code=429, retryable=True
        )
        self.retry_after = retry_after


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
        """Make an authenticated API request to QuickBooks with retry and backoff."""
        url = f"{self.api_base}/company/{realm_id}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        last_exc: Optional[Exception] = None
        for attempt in range(_QB_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.request(
                        method, url, headers=headers, json=json_data
                    )

                if resp.status_code == 401:
                    raise QuickBooksAuthError(
                        "Access token invalid or revoked — reconnect QuickBooks"
                    )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", "60"))
                    if attempt < _QB_MAX_RETRIES - 1:
                        delay = min(retry_after, _QB_RETRY_BASE_DELAY * (2**attempt))
                        logger.warning(
                            f"QB rate limited, retrying in {delay:.1f}s (attempt {attempt + 1})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise QuickBooksRateLimitError(retry_after)
                if resp.status_code == 404:
                    raise QuickBooksAPIError(
                        f"QuickBooks resource not found: {endpoint}",
                        status_code=404,
                        retryable=False,
                    )
                if resp.status_code >= 500:
                    if attempt < _QB_MAX_RETRIES - 1:
                        delay = _QB_RETRY_BASE_DELAY * (2**attempt)
                        logger.warning(
                            f"QB server error {resp.status_code}, retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise QuickBooksAPIError(
                        f"QuickBooks server error: {resp.status_code}",
                        status_code=resp.status_code,
                        retryable=True,
                    )

                resp.raise_for_status()
                return resp.json()

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < _QB_MAX_RETRIES - 1:
                    delay = _QB_RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        f"QB connection error, retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise QuickBooksAPIError(
                    f"QuickBooks connection failed after {_QB_MAX_RETRIES} attempts: {e}",
                    retryable=True,
                ) from e

        raise QuickBooksAPIError(
            f"QuickBooks request failed after {_QB_MAX_RETRIES} retries"
        ) from last_exc

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
