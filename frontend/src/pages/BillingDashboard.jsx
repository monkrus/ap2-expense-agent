import React, { useState, useEffect } from "react";
import {
  CreditCard,
  TrendingUp,
  Users,
  Zap,
  AlertCircle,
  ExternalLink,
  Calendar,
  DollarSign,
  BarChart3,
  Download,
  ArrowLeft,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../hooks/useToast";
import billingAPI from "../services/billingAPI";
import organizationAPI from "../services/organizationAPI";

const API_BASE = import.meta.env.VITE_API_URL || "";

/**
 * Billing Dashboard
 *
 * Shows organization-level billing information:
 * - Current subscription tier
 * - Usage metrics with progress bars
 * - Estimated monthly bill
 * - Upgrade/downgrade options via Stripe
 */
const BillingDashboard = () => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [tiers, setTiers] = useState([]);

  // Open Stripe Customer Portal for managing billing
  const openStripePortal = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE}/api/v1/stripe/portal`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          return_url: `${window.location.origin}/billing`,
        }),
      });
      const data = await res.json();
      if (data.portal_url) {
        window.location.href = data.portal_url;
      }
    } catch (err) {
      console.error("Failed to open billing portal:", err);
      showError("Failed to open billing portal");
    }
  };

  useEffect(() => {
    loadBillingData();

    // Listen for organization changes from other components
    const handleStorageChange = (e) => {
      if (e.key === "currentOrganizationId" && e.newValue !== e.oldValue) {
        console.log("Organization changed, reloading billing data");
        loadBillingData();
      }
    };

    window.addEventListener("storage", handleStorageChange);

    // Also listen for custom events (for same-tab changes)
    const handleOrgChange = () => {
      console.log(
        "Organization changed (custom event), reloading billing data",
      );
      loadBillingData();
    };

    window.addEventListener("organizationChanged", handleOrgChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("organizationChanged", handleOrgChange);
    };
  }, []);

  const loadBillingData = async () => {
    try {
      setLoading(true);

      // Get current organization
      try {
        let orgId = organizationAPI.getCurrentOrganizationId();
        let org = null;

        // Try to fetch the stored organization
        if (orgId) {
          try {
            org = await organizationAPI.getOrganization(orgId);
            setOrganization(org);
          } catch (err) {
            // Stored org ID is invalid (deleted or no access), clear it
            console.warn(
              "Stored organization not accessible, fetching new one",
            );
            organizationAPI.setCurrentOrganizationId(null);
            orgId = null;
          }
        }

        // If no valid org, get first available
        if (!org) {
          const orgs = await organizationAPI.listOrganizations();
          if (orgs && orgs.length > 0) {
            organizationAPI.setCurrentOrganizationId(orgs[0].id);
            setOrganization(orgs[0]);
          } else {
            showError(
              "No organizations found. Please create an organization first.",
            );
            setLoading(false);
            return;
          }
        }
      } catch (orgErr) {
        console.error("Failed to fetch organizations:", orgErr);
        showError("Failed to load organization data");
        // Continue loading billing data even if org fetch fails
      }

      // Load subscription
      const sub = await billingAPI.getSubscription();
      setSubscription(sub);

      // Load usage
      const usageData = await billingAPI.getMonthlyUsage();
      setUsage(usageData);

      // Load available tiers
      const tiersData = await billingAPI.getAllTiers();
      setTiers(tiersData.tiers || []);
    } catch (err) {
      showError("Failed to load billing information");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tierName) => {
    if (tierName === "free") return;
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE}/api/v1/stripe/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          tier: tierName,
          success_url: `${window.location.origin}/billing?session_id={CHECKOUT_SESSION_ID}`,
          cancel_url: `${window.location.origin}/billing`,
        }),
      });
      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      console.error("Failed to create checkout:", err);
      showError("Failed to start checkout");
    }
  };

  const getUsagePercentage = (current, limit) => {
    if (!limit || limit === null || limit === -1) return 0; // Unlimited
    return Math.min((current / limit) * 100, 100);
  };

  const getUsageColor = (percentage) => {
    if (percentage >= 90) return "text-red-600 bg-red-100 border-red-200";
    if (percentage >= 75)
      return "text-orange-600 bg-orange-100 border-orange-200";
    return "text-green-600 bg-green-100 border-green-200";
  };

  const getProgressBarColor = (percentage) => {
    if (percentage >= 90) return "bg-red-500";
    if (percentage >= 75) return "bg-orange-500";
    return "bg-green-500";
  };

  const UsageProgressBar = ({
    label,
    current,
    limit,
    overage,
    overageFee,
    unit = "",
  }) => {
    const percentage = getUsagePercentage(current, limit);
    const isUnlimited = limit === null || limit === undefined || limit === -1;
    const isNotAvailable = limit === 0;

    return (
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="font-semibold text-gray-900">{label}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {isNotAvailable ? (
                <span className="text-gray-400 italic">Manual only - Not available on this plan</span>
              ) : (
                <>
                  {current?.toLocaleString() || 0} {unit}
                  {!isUnlimited && ` / ${limit?.toLocaleString()} ${unit}`}
                  {isUnlimited && " (Unlimited)"}
                </>
              )}
            </p>
          </div>
          {overage > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded">
              +{overage} over
            </span>
          )}
        </div>

        {!isUnlimited && !isNotAvailable && (
          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
            <div
              className={`h-2 rounded-full transition-all ${getProgressBarColor(percentage)}`}
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
        )}

        {isNotAvailable && (
          <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
            <div className="h-2 rounded-full bg-gray-300" style={{ width: "0%" }} />
          </div>
        )}

        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600">
            {isNotAvailable
              ? "Upgrade to enable"
              : isUnlimited
                ? "∞ Unlimited"
                : `${percentage.toFixed(1)}% used`}
          </span>
          {overageFee > 0 && (
            <span className="text-orange-600 font-medium">
              Overage: ${overageFee.toFixed(2)}
            </span>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-100 rounded-full mb-4">
            <RefreshCw className="w-8 h-8 animate-spin text-purple-600" />
          </div>
          <p className="text-gray-600">Loading billing information...</p>
        </div>
      </div>
    );
  }

  const estimatedBill = subscription?.tier_price || 0;
  const totalOverage = usage?.total_overage_fees || 0;
  const totalEstimated = estimatedBill + totalOverage;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <button
                onClick={() => (window.location.href = "/dashboard")}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                Back to Dashboard
              </button>
              <button
                onClick={loadBillingData}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </button>
              <div className="border-l h-8"></div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Billing Dashboard
                </h1>
                {organization && (
                  <p className="text-gray-600 mt-1">{organization.name}</p>
                )}
              </div>
            </div>

            {subscription?.stripe_subscription_id && (
              <button
                onClick={openStripePortal}
                className="flex items-center gap-2 bg-purple-50 text-purple-700 px-4 py-2 rounded-lg hover:bg-purple-100 transition-colors"
              >
                <CreditCard className="w-5 h-5" />
                <span className="text-sm font-medium">
                  Manage Billing
                </span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Current Plan Card */}
        <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl p-8 text-white mb-8">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-purple-200 text-sm font-medium mb-2">
                Current Plan
              </p>
              <h2 className="text-4xl font-bold mb-2">
                {(() => {
                  const tierName =
                    subscription?.tier_display_name ||
                    subscription?.tier ||
                    "Free";
                  // Map enterprise_plus to enterprise +
                  if (tierName.toLowerCase() === "enterprise_plus")
                    return "enterprise +";
                  return tierName.toLowerCase();
                })()}
              </h2>
              <p className="text-2xl font-semibold mb-4">
                ${estimatedBill.toFixed(2)}{" "}
                <span className="text-lg font-normal text-indigo-200">
                  /month
                </span>
              </p>
              {subscription?.cancel_at ? (
                <div className="bg-orange-500/20 border border-orange-300/30 rounded-lg px-4 py-3 mb-2">
                  <div className="flex items-center gap-2 text-white">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-sm">
                        Subscription Scheduled to Cancel
                      </p>
                      <p className="text-sm text-purple-100">
                        Expires on{" "}
                        {new Date(subscription.cancel_at).toLocaleDateString(
                          "en-US",
                          {
                            month: "long",
                            day: "numeric",
                            year: "numeric",
                          },
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-purple-100">
                  <Calendar className="w-4 h-4" />
                  <span className="text-sm">
                    Billing period:{" "}
                    {new Date().toLocaleDateString("en-US", {
                      month: "long",
                      year: "numeric",
                    })}
                  </span>
                </div>
              )}
            </div>

            {subscription?.stripe_subscription_id ? (
              <button
                onClick={openStripePortal}
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-purple-600 rounded-lg font-semibold hover:bg-purple-50 transition-colors"
              >
                Manage Billing
                <ExternalLink className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => window.location.href = "/pricing"}
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-purple-600 rounded-lg font-semibold hover:bg-purple-50 transition-colors"
              >
                Upgrade Plan
                <ExternalLink className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Usage Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <p className="text-gray-600 text-xs mb-1">Active Users</p>
            <p className="text-2xl font-bold text-gray-900">
              {usage?.usage?.active_users?.quantity || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Limit: {subscription?.limits?.max_users === -1 || subscription?.limits?.max_users == null ? "Unlimited" : subscription?.limits?.max_users}
            </p>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-gray-600 text-xs mb-1">Expenses</p>
            <p className="text-2xl font-bold text-gray-900">
              {usage?.usage?.expense?.quantity || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">This month</p>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <p className="text-gray-600 text-xs mb-1">AP2 Transactions</p>
            <p className="text-2xl font-bold text-gray-900">
              {usage?.usage?.ap2_transaction?.quantity || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">This month</p>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-orange-600" />
              </div>
            </div>
            <p className="text-gray-600 text-xs mb-1">OCR Scans</p>
            <p className="text-2xl font-bold text-gray-900">
              {usage?.usage?.ocr_scan?.quantity || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">This month</p>
          </div>
        </div>

        {/* Usage Metrics */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Usage Details
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <UsageProgressBar
              label="Expenses Submitted"
              current={usage?.usage?.expense?.quantity || 0}
              limit={
                usage?.usage?.expense?.limit ??
                subscription?.limits?.max_expenses_per_month
              }
              overage={usage?.usage?.expense?.overage || 0}
              overageFee={usage?.usage?.expense?.overage_fee || 0}
              unit="expenses"
            />

            <UsageProgressBar
              label="AP2 Transactions"
              current={usage?.usage?.ap2_transaction?.quantity || 0}
              limit={
                usage?.usage?.ap2_transaction?.limit ??
                subscription?.limits?.max_ap2_transactions
              }
              overage={usage?.usage?.ap2_transaction?.overage || 0}
              overageFee={usage?.usage?.ap2_transaction?.overage_fee || 0}
              unit="transactions"
            />

            <UsageProgressBar
              label="OCR Scans"
              current={usage?.usage?.ocr_scan?.quantity || 0}
              limit={
                usage?.usage?.ocr_scan?.limit ??
                subscription?.limits?.ocr_scans_included
              }
              overage={usage?.usage?.ocr_scan?.overage || 0}
              overageFee={usage?.usage?.ocr_scan?.overage_fee || 0}
              unit="scans"
            />

            <UsageProgressBar
              label="Active Users"
              current={usage?.usage?.active_users?.quantity || 0}
              limit={
                usage?.usage?.active_users?.limit ??
                subscription?.limits?.max_users
              }
              overage={usage?.usage?.active_users?.overage || 0}
              overageFee={usage?.usage?.active_users?.overage_fee || 0}
              unit="users"
            />
          </div>
        </div>

        {/* Estimated Bill */}
        <div className="bg-white rounded-lg border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Estimated Monthly Bill
          </h2>

          <div className="space-y-4">
            <div className="flex justify-between items-center pb-4">
              <span className="text-gray-700">Base Subscription</span>
              <span className="text-2xl font-bold text-gray-900">
                ${estimatedBill.toFixed(2)}
              </span>
            </div>

            {totalOverage > 0 && (
              <>
                <div className="flex justify-between items-center text-orange-600">
                  <span>Usage Overages</span>
                  <span className="text-xl font-semibold">
                    +${totalOverage.toFixed(2)}
                  </span>
                </div>

                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-orange-900 mb-1">
                        You're currently over your plan limits
                      </p>
                      <p className="text-xs text-orange-700">
                        Consider upgrading to eliminate overage charges and save
                        money
                      </p>
                    </div>
                  </div>
                </div>
              </>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-gray-300">
              <span className="text-xl font-bold text-gray-900">
                Total Estimated
              </span>
              <span className="text-3xl font-bold text-purple-600">
                ${totalEstimated.toFixed(2)}
              </span>
            </div>

            {subscription?.stripe_subscription_id && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-blue-900">
                  <strong>Note:</strong> This bill is charged to your card on
                  file. You can view invoices and update payment methods in the{" "}
                  <button
                    onClick={openStripePortal}
                    className="text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
                  >
                    Billing Portal
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Available Plans */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6 text-center">
            Choose Your Plan
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Free Tier */}
            <div className={`relative rounded-xl border-2 p-6 flex flex-col ${
              subscription?.tier === "free"
                ? "border-purple-600 bg-purple-50"
                : "border-gray-200 hover:border-purple-300"
            }`}>
              {subscription?.tier === "free" && (
                <div className="absolute top-4 right-4">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-purple-600 text-white">
                    Current Plan
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">Free</h3>
                <div className="mb-4">
                  <span className="text-4xl font-bold text-gray-900">$0</span>
                  <span className="text-gray-600">/month</span>
                </div>
                <p className="text-sm text-gray-600">Perfect for getting started</p>
              </div>

              <ul className="space-y-3 mb-6 flex-grow">
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>1 Organization</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>2 Users</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>30 Expenses/month</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>20 AP2 Transactions</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>0.5GB Storage</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>90 days retention</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>Approval Workflows</span>
                </li>
              </ul>

              <div className="mt-auto">
              {subscription?.tier === "free" ? (
                <button
                  disabled
                  className="w-full py-3 bg-gray-300 text-gray-600 rounded-lg font-semibold cursor-not-allowed"
                >
                  Current Plan
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade("free")}
                  className="w-full py-3 bg-gray-100 text-gray-700 rounded-lg font-semibold hover:bg-gray-200"
                >
                  Downgrade
                </button>
              )}
              </div>
            </div>

            {/* Starter Tier */}
            <div className={`relative rounded-xl border-2 p-6 flex flex-col ${
              subscription?.tier === "starter"
                ? "border-purple-600 bg-purple-50"
                : "border-gray-200 hover:border-purple-300"
            }`}>
              {subscription?.tier === "starter" && (
                <div className="absolute top-4 right-4">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-purple-600 text-white">
                    Current Plan
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">Starter</h3>
                <div className="mb-4">
                  <span className="text-4xl font-bold text-gray-900">$29</span>
                  <span className="text-gray-600">/month</span>
                </div>
                <p className="text-sm text-gray-600">For growing teams</p>
              </div>

              <ul className="space-y-3 mb-6 flex-grow">
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>3 Organizations</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>10 Users</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>100 Expenses/month</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>100 AP2 Transactions</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>5GB Storage</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>1 year retention</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>Approval Workflows</span>
                </li>
              </ul>

              <div className="mt-auto">
              {subscription?.tier === "starter" ? (
                <button
                  disabled
                  className="w-full py-3 bg-gray-300 text-gray-600 rounded-lg font-semibold cursor-not-allowed"
                >
                  Current Plan
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade("starter")}
                  className="block w-full py-3 bg-purple-600 text-white text-center rounded-lg font-semibold hover:bg-purple-700 transition-colors"
                >
                  {subscription?.tier === "free" ? "Upgrade" : "Change Plan"}
                </button>
              )}
              </div>
            </div>

            {/* Professional Tier */}
            <div className={`relative rounded-xl border-2 p-6 flex flex-col ${
              subscription?.tier === "professional"
                ? "border-purple-600 bg-purple-50"
                : "border-purple-300 hover:border-purple-400 shadow-lg"
            }`}>
              {subscription?.tier === "professional" && (
                <div className="absolute top-4 right-4">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-purple-600 text-white">
                    Current Plan
                  </span>
                </div>
              )}

              {subscription?.tier !== "professional" && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="inline-flex items-center px-4 py-1 rounded-full text-xs font-semibold bg-purple-600 text-white">
                    POPULAR
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">Professional</h3>
                <div className="mb-4">
                  <span className="text-4xl font-bold text-gray-900">$99</span>
                  <span className="text-gray-600">/month</span>
                </div>
                <p className="text-sm text-gray-600">For large organizations</p>
              </div>

              <ul className="space-y-3 mb-6 flex-grow">
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>10 Organizations</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>50 Users</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>500 Expenses/month</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span><strong>Unlimited</strong> AP2 Transactions</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>50GB Storage</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>3 years retention</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>API Access</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>Approval Workflows</span>
                </li>
              </ul>

              <div className="mt-auto">
              {subscription?.tier === "professional" ? (
                <button
                  disabled
                  className="w-full py-3 bg-gray-300 text-gray-600 rounded-lg font-semibold cursor-not-allowed"
                >
                  Current Plan
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade("professional")}
                  className="block w-full py-3 bg-purple-600 text-white text-center rounded-lg font-semibold hover:bg-purple-700 transition-colors"
                >
                  Upgrade Now
                </button>
              )}
              </div>
            </div>
          </div>

          <div className="mt-6 text-center text-sm text-gray-600">
            Payments processed securely via Stripe. Cancel or change plans anytime.
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4 mt-8">
          <button
            onClick={() => {
              // Helper function to properly escape CSV fields
              const escapeCSV = (field) => {
                if (field === null || field === undefined) return '""';
                const str = String(field);
                // Wrap in quotes if contains comma, newline, or quote
                if (str.includes(",") || str.includes("\n") || str.includes('"')) {
                  return `"${str.replace(/"/g, '""')}"`;
                }
                return `"${str}"`;
              };

              // Generate billing report as CSV with proper formatting
              const reportData = [
                ["AP2 Expense Agent - Billing Report", ""],
                ["Generated", new Date().toLocaleString()],
                ["Organization", organization?.name || "N/A"],
                ["", ""],
                ["Current Plan", ""],
                ["Tier", subscription?.tier_display_name || subscription?.tier || "N/A"],
                ["Monthly Price", `$${estimatedBill.toFixed(2)}`],
                ["Billing Period", new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" })],
                ["", ""],
                ["Usage This Month", "Quantity"],
                ["Active Users", usage?.usage?.active_users?.quantity || 0],
                ["Expenses Submitted", usage?.usage?.expense?.quantity || 0],
                ["AP2 Transactions", usage?.usage?.ap2_transaction?.quantity || 0],
                ["OCR Scans", usage?.usage?.ocr_scan?.quantity || 0],
                ["", ""],
                ["Estimated Bill", "Amount"],
                ["Base Subscription", `$${estimatedBill.toFixed(2)}`],
                ["Usage Overages", `$${totalOverage.toFixed(2)}`],
                ["Total Estimated", `$${totalEstimated.toFixed(2)}`],
              ];

              const csvContent = reportData
                .map((row) => row.map(escapeCSV).join(","))
                .join("\n");
              const blob = new Blob([csvContent], {
                type: "text/csv;charset=utf-8;",
              });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = `billing-report-${new Date().toISOString().split("T")[0]}.csv`;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              URL.revokeObjectURL(url);
              success("Billing report exported as CSV");
            }}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>

          <button
            onClick={() => {
              // Generate billing report as JSON
              const reportData = {
                report_title: "AP2 Expense Agent - Billing Report",
                generated_at: new Date().toISOString(),
                organization: {
                  name: organization?.name || "N/A",
                  id: organization?.id
                },
                current_plan: {
                  tier: subscription?.tier_display_name || subscription?.tier || "N/A",
                  monthly_price: estimatedBill,
                  billing_period: new Date().toLocaleDateString("en-US", {
                    month: "long",
                    year: "numeric",
                  }),
                },
                usage_this_month: {
                  active_users: usage?.usage?.active_users?.quantity || 0,
                  expenses_submitted: usage?.usage?.expense?.quantity || 0,
                  ap2_transactions: usage?.usage?.ap2_transaction?.quantity || 0,
                  ocr_scans: usage?.usage?.ocr_scan?.quantity || 0,
                },
                estimated_bill: {
                  base_subscription: estimatedBill,
                  usage_overages: totalOverage,
                  total_estimated: totalEstimated,
                  currency: "USD"
                }
              };

              const jsonContent = JSON.stringify(reportData, null, 2);
              const blob = new Blob([jsonContent], {
                type: "application/json;charset=utf-8;",
              });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = `billing-report-${new Date().toISOString().split("T")[0]}.json`;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              URL.revokeObjectURL(url);
              success("Billing report exported as JSON");
            }}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Download className="w-4 h-4" />
            Export JSON
          </button>
        </div>
      </div>
    </div>
  );
};

export default BillingDashboard;
