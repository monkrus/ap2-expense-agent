"""
GCP Marketplace API Client
Handles authentication and API calls to Google Cloud Marketplace
"""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Dict, Optional

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from ..config import settings


class GCPMarketplaceClient:
    """
    Client for interacting with Google Cloud Marketplace API

    Used for:
    - Reporting usage metrics to GCP for billing
    - Validating entitlements
    - Fetching account information
    """

    def __init__(self):
        """Initialize GCP Marketplace client with service account credentials"""
        self.project_id = settings.gcp_project_id
        self.service_account_path = settings.gcp_service_account_path
        self.api_base_url = "https://cloudcommerceprocurement.googleapis.com/v1"

        # Initialize credentials
        self.credentials = None
        if self.service_account_path:
            try:
                self.credentials = (
                    service_account.Credentials.from_service_account_file(
                        self.service_account_path,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                )
            except Exception as e:
                print(f"Warning: Failed to load GCP service account: {e}")
                print("GCP Marketplace integration will be disabled")

    def _get_access_token(self) -> str:
        """Get OAuth2 access token for GCP API"""
        if not self.credentials:
            raise ValueError("GCP service account credentials not configured")

        # Refresh token if needed
        if not self.credentials.valid:
            self.credentials.refresh(Request())

        return self.credentials.token

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication"""
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    async def report_usage(
        self,
        entitlement_id: str,
        metrics: Dict[str, float],
        timestamp: Optional[str] = None,
    ) -> Dict:
        """
        Report usage metrics to GCP Marketplace for billing

        This is called hourly to report aggregated usage for each organization.

        Args:
            entitlement_id: GCP entitlement ID (unique per customer)
            metrics: Dict of metric_name -> value
                {
                    "ai_categorization": 1234,
                    "ap2_transaction": 56,
                    "active_users": 45
                }
            timestamp: ISO timestamp (default: now)

        Returns:
            API response dict

        Example:
            await client.report_usage(
                "ent_abc123",
                {"ai_categorization": 1234, "ap2_transaction": 56}
            )
        """
        if not self.credentials:
            # GCP not configured - log but don't fail
            print(f"Warning: GCP usage reporting disabled (no credentials)")
            return {"status": "skipped", "reason": "no_credentials"}

        if not timestamp:
            timestamp = datetime.utcnow().isoformat() + "Z"

        # Build Consumer Procurement usage payload (entitlement-scoped)
        usage_items = []
        for metric_name, value in metrics.items():
            usage_items.append(
                {
                    "metric": metric_name,
                    "value": int(value),
                    "effectiveTime": timestamp,
                }
            )

        usage_report = {
            "requestId": f"usage-{entitlement_id}-{int(datetime.utcnow().timestamp())}",
            "usage": usage_items,
        }

        try:
            # Send usage report to GCP Consumer Procurement API
            url = (
                f"{self.api_base_url}/providers/{self.project_id}/"
                f"entitlements/{entitlement_id}:reportUsage"
            )
            response = requests.post(
                url, headers=self._get_headers(), json=usage_report, timeout=30
            )

            if response.status_code == 200:
                return {
                    "status": "success",
                    "entitlement_id": entitlement_id,
                    "metrics_reported": len(metrics),
                    "response": response.json(),
                }
            else:
                return {
                    "status": "error",
                    "entitlement_id": entitlement_id,
                    "error": response.text,
                    "status_code": response.status_code,
                }

        except Exception as e:
            return {
                "status": "error",
                "entitlement_id": entitlement_id,
                "error": str(e),
            }

    async def get_entitlement(self, entitlement_id: str) -> Dict:
        """
        Get entitlement details from GCP Marketplace

        Args:
            entitlement_id: GCP entitlement ID

        Returns:
            Entitlement details dict
        """
        if not self.credentials:
            raise ValueError("GCP credentials not configured")

        try:
            url = f"{self.api_base_url}/providers/{self.project_id}/entitlements/{entitlement_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get entitlement: {response.text}")

        except Exception as e:
            raise Exception(f"Error fetching entitlement: {str(e)}")

    async def validate_entitlement(self, entitlement_id: str) -> bool:
        """
        Validate that an entitlement is active

        Args:
            entitlement_id: GCP entitlement ID

        Returns:
            True if entitlement is active, False otherwise
        """
        try:
            entitlement = await self.get_entitlement(entitlement_id)
            return entitlement.get("state") == "ACTIVE"
        except:
            return False

    @staticmethod
    def verify_webhook_signature(
        request_body: bytes, signature_header: str, webhook_secret: str
    ) -> bool:
        """
        Verify webhook signature from Google Cloud Marketplace

        Args:
            request_body: Raw request body bytes
            signature_header: X-Goog-Signature header value
            webhook_secret: Webhook secret from GCP console

        Returns:
            True if signature is valid, False otherwise
        """
        if not webhook_secret:
            # If no secret configured, skip verification (dev mode)
            print("Warning: Webhook signature verification disabled")
            return True

        try:
            # Google uses HMAC-SHA256
            expected_signature = hmac.new(
                webhook_secret.encode(), request_body, hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature_header)
        except Exception as e:
            print(f"Webhook signature verification failed: {e}")
            return False

    async def get_account_info(self, account_id: str) -> Dict:
        """
        Get GCP Marketplace account information

        Args:
            account_id: GCP account ID

        Returns:
            Account details dict
        """
        if not self.credentials:
            raise ValueError("GCP credentials not configured")

        try:
            url = (
                f"{self.api_base_url}/providers/{self.project_id}/accounts/{account_id}"
            )
            response = requests.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get account info: {response.text}")

        except Exception as e:
            raise Exception(f"Error fetching account: {str(e)}")


# Singleton instance
_gcp_client = None


def get_gcp_marketplace_client() -> GCPMarketplaceClient:
    """Get singleton GCP Marketplace client"""
    global _gcp_client
    if _gcp_client is None:
        _gcp_client = GCPMarketplaceClient()
    return _gcp_client
