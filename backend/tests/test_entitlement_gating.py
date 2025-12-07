from types import SimpleNamespace

import pytest

from src.middleware.entitlement_gating import ALLOWED_FEATURES, can_access_feature, ensure_feature_access


class DummySub(SimpleNamespace):
    tier_id: str = ""
    tier_name: str = ""


def test_can_access_feature_allows_unknown():
    assert can_access_feature("starter", "nonexistent_feature") is True


def test_can_access_feature_respects_map():
    assert can_access_feature("professional", "ap2_payments") is True
    assert can_access_feature("starter", "ap2_payments") is False


def test_ensure_feature_access_passes_allowed():
    sub = DummySub(tier_id="professional")
    ensure_feature_access(sub, "ap2_payments")  # should not raise


def test_ensure_feature_access_blocks_disallowed():
    sub = DummySub(tier_id="starter")
    with pytest.raises(Exception) as excinfo:
        ensure_feature_access(sub, "ap2_payments")
    detail = excinfo.value.detail
    assert detail["error"] == "feature_not_in_plan"
    assert "ap2_payments" in detail["feature"]
