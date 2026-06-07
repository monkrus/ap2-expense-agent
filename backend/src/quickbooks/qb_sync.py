"""
QuickBooks expense sync service.

Syncs approved expenses from AP2 to QuickBooks Online as Purchase entries.
Maps expense categories to QB accounts and vendors.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import Expense
from ..models_billing import QuickBooksConnection
from .qb_client import QuickBooksClient
from .token_encryption import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

# Default category -> QB account type mapping
DEFAULT_CATEGORY_MAP = {
    "office_supplies": "Office Supplies",
    "travel": "Travel",
    "meals": "Meals and Entertainment",
    "software": "Software",
    "equipment": "Equipment",
    "utilities": "Utilities",
    "marketing": "Advertising",
    "professional_services": "Professional Fees",
    "other": "Other Expenses",
}


class QuickBooksSync:
    """Syncs approved expenses to QuickBooks Online."""

    def __init__(self, db: Session):
        self.db = db
        self.client = QuickBooksClient()

    def _get_connection(self, organization_id: str) -> Optional[QuickBooksConnection]:
        """Get the QB connection for an organization."""
        return (
            self.db.query(QuickBooksConnection)
            .filter(
                QuickBooksConnection.organization_id == organization_id,
                QuickBooksConnection.sync_enabled == True,
            )
            .first()
        )

    async def _ensure_fresh_token(
        self, connection: QuickBooksConnection
    ) -> str:
        """Refresh the token if expired, return valid access token (decrypted)."""
        if connection.token_expires_at <= datetime.utcnow():
            plain_refresh = decrypt_token(connection.refresh_token)
            tokens = await self.client.refresh_tokens(plain_refresh)
            connection.access_token = encrypt_token(tokens["access_token"])
            connection.refresh_token = encrypt_token(tokens["refresh_token"])
            connection.token_expires_at = tokens["token_expires_at"]
            self.db.commit()
        return decrypt_token(connection.access_token)

    async def sync_expense(
        self,
        expense: Expense,
        organization_id: str,
        category_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Sync a single approved expense to QuickBooks as a Purchase."""
        connection = self._get_connection(organization_id)
        if not connection:
            return {"synced": False, "reason": "No QuickBooks connection"}

        access_token = await self._ensure_fresh_token(connection)
        realm_id = connection.realm_id

        # Map category to QB account name
        cat_map = category_map or DEFAULT_CATEGORY_MAP
        qb_account_name = cat_map.get(expense.category, "Other Expenses")

        # Build QuickBooks Purchase object
        purchase_data = {
            "PaymentType": "Cash",
            "TotalAmt": float(expense.amount),
            "TxnDate": expense.date.strftime("%Y-%m-%d") if expense.date else None,
            "Line": [
                {
                    "Amount": float(expense.amount),
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "AccountBasedExpenseLineDetail": {
                        "AccountRef": {"name": qb_account_name},
                    },
                    "Description": expense.description or "",
                }
            ],
            "PrivateNote": f"AP2 Expense #{expense.id}",
        }

        # Add vendor if available
        if expense.vendor:
            purchase_data["EntityRef"] = {"name": expense.vendor}

        try:
            result = await self.client.create_purchase(
                realm_id, access_token, purchase_data
            )
            connection.last_sync_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Synced expense {expense.id} to QB as Purchase")
            return {"synced": True, "qb_purchase_id": result.get("Purchase", {}).get("Id")}
        except Exception as e:
            logger.error(f"Failed to sync expense {expense.id} to QB: {e}")
            return {"synced": False, "reason": str(e)}

    async def sync_pending_expenses(
        self, organization_id: str
    ) -> List[Dict[str, Any]]:
        """Sync all approved but un-synced expenses for an organization."""
        connection = self._get_connection(organization_id)
        if not connection:
            return []

        # Find approved expenses that haven't been synced
        expenses = (
            self.db.query(Expense)
            .filter(
                Expense.organization_id == organization_id,
                Expense.status == "approved",
            )
            .all()
        )

        results = []
        for expense in expenses:
            result = await self.sync_expense(expense, organization_id)
            results.append({"expense_id": expense.id, **result})

        return results

    async def get_sync_status(self, organization_id: str) -> Dict[str, Any]:
        """Get the sync status for an organization."""
        connection = self._get_connection(organization_id)
        if not connection:
            return {"connected": False}

        return {
            "connected": True,
            "realm_id": connection.realm_id,
            "sync_enabled": connection.sync_enabled,
            "last_sync_at": (
                connection.last_sync_at.isoformat()
                if connection.last_sync_at
                else None
            ),
            "token_valid": connection.token_expires_at > datetime.utcnow(),
        }
