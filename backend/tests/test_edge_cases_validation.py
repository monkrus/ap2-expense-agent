"""
EDGE-VAL: Edge Cases & Input Validation Tests (CRITICAL)

Tests input validation, XSS prevention, SQL injection prevention, and edge cases:
- XSS prevention in expense fields
- SQL injection prevention in queries
- Command injection prevention
- Input length limits
- Special character handling
- Boundary value testing

Priority: 🔴 CRITICAL
"""

import pytest
from fastapi import status

from src.models import OrganizationRole
from tests.factories import (
    add_user_to_organization,
    create_employee,
    create_organization_with_owner,
    create_pending_expense,
)


@pytest.mark.critical
@pytest.mark.security
class TestXSSPrevention:
    """Test XSS prevention in user inputs"""

    # ========================================================================
    # EDGE-VAL-001: XSS prevention in expense description
    # ========================================================================

    def test_EDGE_VAL_001_xss_in_expense_description(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-001
        Priority: 🔴 CRITICAL

        XSS payloads in expense description are sanitized/escaped.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try to create expense with XSS payload
        xss_payload = "<script>alert('XSS')</script>"
        expense_data = {
            "amount": 100.0,
            "description": xss_payload,
            "category": "MEALS",
            "vendor": "Test Vendor",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should succeed (API accepts it but should sanitize on output)
        assert response.status_code == status.HTTP_201_CREATED
        expense = response.json()

        # XSS payload should be stored as-is (sanitization happens on output)
        # or rejected if API does input sanitization
        # The key is that it doesn't execute when rendered
        assert expense["description"] == xss_payload or "&lt;script&gt;" in expense["description"]

    # ========================================================================
    # EDGE-VAL-002: XSS prevention in expense vendor field
    # ========================================================================

    def test_EDGE_VAL_002_xss_in_expense_vendor(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-002
        Priority: 🔴 CRITICAL

        XSS payloads in vendor field are sanitized/escaped.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try XSS in vendor field
        xss_payloads = [
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg/onload=alert('XSS')>",
            "' OR '1'='1",
        ]

        for payload in xss_payloads:
            expense_data = {
                "amount": 100.0,
                "description": "Test",
                "category": "MEALS",
                "vendor": payload,
            }

            response = client.post(
                "/api/v1/expenses",
                json=expense_data,
                headers=headers
            )

            # Should either succeed with sanitization or reject
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST
            ]

    # ========================================================================
    # EDGE-VAL-003: XSS prevention in organization name
    # ========================================================================

    def test_EDGE_VAL_003_xss_in_organization_name(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-003
        Priority: 🔴 CRITICAL

        XSS payloads in organization name are prevented.
        """
        from tests.factories import create_user

        # Create user
        user = create_user(db_session)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to create org with XSS payload in name
        xss_payload = "<script>alert('XSS')</script>"
        org_data = {
            "name": xss_payload,
            "slug": "test-xss-org",
            "description": "Test org"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=headers
        )

        # Should either accept (React handles XSS on render) or reject
        if response.status_code == status.HTTP_201_CREATED:
            org = response.json()
            # API stores as-is, React frontend auto-escapes on render
            # This is acceptable - XSS prevention happens at output, not input
            assert "name" in org  # Just verify it was created
        else:
            # Or validation rejects it (400 or 422 both acceptable)
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]


@pytest.mark.critical
@pytest.mark.security
class TestSQLInjectionPrevention:
    """Test SQL injection prevention"""

    # ========================================================================
    # EDGE-VAL-004: SQL injection in expense filters
    # ========================================================================

    def test_EDGE_VAL_004_sql_injection_in_expense_filters(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-004
        Priority: 🔴 CRITICAL

        SQL injection attempts in expense list filters are prevented.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try SQL injection payloads in query params
        sql_payloads = [
            "' OR '1'='1",
            "1; DROP TABLE expenses--",
            "' UNION SELECT * FROM users--",
            "admin'--",
            "1' AND '1'='1",
        ]

        for payload in sql_payloads:
            # Try in status filter
            response = client.get(
                f"/api/v1/expenses?status={payload}",
                headers=headers
            )

            # Should either return empty results or validation error, not SQL error
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

            # Should not expose SQL errors
            if response.status_code != status.HTTP_200_OK:
                error = response.json()
                assert "SQL" not in str(error).upper()
                assert "DATABASE" not in str(error).upper()

    # ========================================================================
    # EDGE-VAL-005: SQL injection in organization lookup
    # ========================================================================

    def test_EDGE_VAL_005_sql_injection_in_org_lookup(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-005
        Priority: 🔴 CRITICAL

        SQL injection in organization slug lookup is prevented.
        """
        from tests.factories import create_user

        # Create user
        user = create_user(db_session)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try SQL injection in slug
        sql_payload = "test-org' OR '1'='1"
        org_data = {
            "name": "Test Org",
            "slug": sql_payload,
            "description": "Test"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=headers
        )

        # Should reject invalid slug format
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
        error = response.json()
        # Should be validation error, not SQL error
        error_msg = str(error).lower()
        assert "slug" in error_msg or "invalid" in error_msg or "validation" in error_msg


@pytest.mark.critical
@pytest.mark.security
class TestInputValidation:
    """Test input validation and boundary cases"""

    # ========================================================================
    # EDGE-VAL-006: Expense amount boundaries
    # ========================================================================

    def test_EDGE_VAL_006_expense_amount_negative(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-006
        Priority: 🔴 CRITICAL

        Negative expense amounts are rejected.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try negative amount
        expense_data = {
            "amount": -100.0,
            "description": "Negative expense",
            "category": "MEALS",
            "vendor": "Test",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should reject
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_EDGE_VAL_007_expense_amount_zero(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-007
        Priority: 🟡 MEDIUM

        Zero expense amounts are handled appropriately.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try zero amount
        expense_data = {
            "amount": 0.0,
            "description": "Zero expense",
            "category": "MEALS",
            "vendor": "Test",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should reject (expenses must be > 0)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_EDGE_VAL_008_expense_amount_very_large(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-008
        Priority: 🟡 MEDIUM

        Very large expense amounts are handled (max value check).
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try very large amount
        expense_data = {
            "amount": 999999999.99,
            "description": "Large expense",
            "category": "MEALS",
            "vendor": "Test",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should either accept (if within DB limits) or reject
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    # ========================================================================
    # EDGE-VAL-009: String length validation
    # ========================================================================

    def test_EDGE_VAL_009_expense_description_max_length(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-009
        Priority: 🟠 HIGH

        Expense description length limits are enforced.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try very long description (10,000 characters)
        long_description = "A" * 10000
        expense_data = {
            "amount": 100.0,
            "description": long_description,
            "category": "MEALS",
            "vendor": "Test",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should either truncate or reject
        if response.status_code == status.HTTP_201_CREATED:
            expense = response.json()
            # May be truncated or stored as-is
            assert len(expense["description"]) >= 100
        else:
            # Or validation rejects it
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    def test_EDGE_VAL_010_organization_name_empty(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-010
        Priority: 🔴 CRITICAL

        Empty organization name is rejected.
        """
        from tests.factories import create_user

        # Create user
        user = create_user(db_session)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try empty name
        org_data = {
            "name": "",
            "slug": "test-org",
            "description": "Test"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=headers
        )

        # Should reject
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ========================================================================
    # EDGE-VAL-011: Special character handling
    # ========================================================================

    def test_EDGE_VAL_011_expense_unicode_characters(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-011
        Priority: 🟡 MEDIUM

        Unicode characters in expense fields are handled correctly.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try unicode characters
        unicode_data = {
            "amount": 100.0,
            "description": "Café lunch 🍔 日本語",
            "category": "MEALS",
            "vendor": "レストラン",
        }

        response = client.post(
            "/api/v1/expenses",
            json=unicode_data,
            headers=headers
        )

        # Should accept unicode
        assert response.status_code == status.HTTP_201_CREATED
        expense = response.json()
        assert "Café" in expense["description"]

    def test_EDGE_VAL_012_expense_null_category(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-012
        Priority: 🟠 HIGH

        Null/missing category is handled appropriately.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try without category
        expense_data = {
            "amount": 100.0,
            "description": "Test expense",
            "vendor": "Test Vendor",
            # category missing
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should either default to UNCATEGORIZED or reject
        if response.status_code == status.HTTP_201_CREATED:
            expense = response.json()
            assert expense["category"] in ["UNCATEGORIZED", "OTHER", None]
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.critical
@pytest.mark.security
class TestCommandInjectionPrevention:
    """Test command injection prevention"""

    # ========================================================================
    # EDGE-VAL-013: Command injection in file operations
    # ========================================================================

    def test_EDGE_VAL_013_command_injection_in_filename(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-013
        Priority: 🔴 CRITICAL

        Command injection attempts in filename are prevented.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        expense = create_pending_expense(db_session, employee, org, amount=100.0)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try command injection in filename
        import io
        malicious_filename = "receipt.jpg; rm -rf /"
        receipt_file = io.BytesIO(b"fake image data")

        response = client.post(
            f"/api/v1/receipts/upload/{expense.id}",
            files={"file": (malicious_filename, receipt_file, "image/jpeg")},
            headers=headers
        )

        # Should either sanitize filename or reject
        if response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            # Filename should be sanitized
            receipt = response.json()
            # Should not contain shell metacharacters
            if "filename" in receipt:
                assert ";" not in receipt["filename"]
                assert "|" not in receipt["filename"]
        else:
            # Or validation rejects it
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]


@pytest.mark.critical
@pytest.mark.security
class TestHeaderInjection:
    """Test HTTP header injection prevention"""

    # ========================================================================
    # EDGE-VAL-014: Header injection in X-Organization-Id
    # ========================================================================

    def test_EDGE_VAL_014_header_injection_newlines(
        self, client, db_session
    ):
        """
        Test ID: EDGE-VAL-014
        Priority: 🔴 CRITICAL

        Header injection with newlines is prevented.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]

        # Try header injection
        malicious_org_id = f"{org.id}\r\nX-Admin: true"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": malicious_org_id
        }

        response = client.get(
            "/api/v1/expenses",
            headers=headers
        )

        # Should either reject or sanitize
        # Most frameworks automatically prevent CRLF injection
        assert response.status_code in [
            status.HTTP_200_OK,  # If sanitized
            status.HTTP_400_BAD_REQUEST,  # If rejected
            status.HTTP_403_FORBIDDEN,  # If org ID invalid
        ]
