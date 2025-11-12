import React, { useState, useEffect } from 'react';
import {
  CreditCard, TrendingUp, Users, Zap, AlertCircle, ExternalLink,
  Calendar, DollarSign, BarChart3, ArrowUpRight, Settings, Download, ArrowLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import billingAPI from '../services/billingAPI';
import organizationAPI from '../services/organizationAPI';
import paymentAPI from '../services/paymentAPI';

/**
 * Billing Dashboard
 *
 * Shows organization-level billing information:
 * - Current subscription tier
 * - Usage metrics with progress bars
 * - Estimated monthly bill
 * - Upgrade/downgrade options
 * - GCP Marketplace integration status
 */
const BillingDashboard = () => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [tiers, setTiers] = useState([]);

  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    try {
      setLoading(true);

      // Get current organization
      try {
        const orgId = organizationAPI.getCurrentOrganizationId();
        if (!orgId) {
          const orgs = await organizationAPI.listOrganizations();
          if (orgs && orgs.length > 0) {
            organizationAPI.setCurrentOrganizationId(orgs[0].id);
            setOrganization(orgs[0]);
          }
        } else {
          const org = await organizationAPI.getOrganization(orgId);
          setOrganization(org);
        }
      } catch (orgErr) {
        console.error('Failed to fetch organizations:', orgErr);
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
      showError('Failed to load billing information');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = (tierName) => {
    if (subscription?.gcp_entitlement_id) {
      // GCP customer - redirect to GCP Console
      window.open(
        `https://console.cloud.google.com/marketplace/product/google/${subscription.gcp_entitlement_id}`,
        '_blank'
      );
    } else {
      // Direct customer - navigate to pricing page
      window.location.href = '/pricing';
    }
  };

  const handleManagePayment = async () => {
    try {
      setLoading(true);
      const { url } = await paymentAPI.createPortalSession();
      window.location.href = url;
    } catch (err) {
      showError('Failed to open payment portal');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getUsagePercentage = (current, limit) => {
    if (!limit || limit === null) return 0; // Unlimited
    return Math.min((current / limit) * 100, 100);
  };

  const getUsageColor = (percentage) => {
    if (percentage >= 90) return 'text-red-600 bg-red-100 border-red-200';
    if (percentage >= 75) return 'text-orange-600 bg-orange-100 border-orange-200';
    return 'text-green-600 bg-green-100 border-green-200';
  };

  const getProgressBarColor = (percentage) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-orange-500';
    return 'bg-green-500';
  };

  const UsageProgressBar = ({ label, current, limit, overage, overageFee, unit = '' }) => {
    const percentage = getUsagePercentage(current, limit);
    const isUnlimited = limit === null || limit === undefined;

    return (
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="font-semibold text-gray-900">{label}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {current?.toLocaleString() || 0} {unit}
              {!isUnlimited && ` / ${limit?.toLocaleString()} ${unit}`}
              {isUnlimited && ' (Unlimited)'}
            </p>
          </div>
          {overage > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded">
              +{overage} over
            </span>
          )}
        </div>

        {!isUnlimited && (
          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
            <div
              className={`h-2 rounded-full transition-all ${getProgressBarColor(percentage)}`}
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
        )}

        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600">
            {isUnlimited ? '∞ Unlimited' : `${percentage.toFixed(1)}% used`}
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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
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
                onClick={() => window.location.href = '/dashboard'}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                Back to Dashboard
              </button>
              <div className="border-l h-8"></div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Billing Dashboard</h1>
                {organization && (
                  <p className="text-gray-600 mt-1">{organization.name}</p>
                )}
              </div>
            </div>

            {subscription?.gcp_entitlement_id && (
              <div className="flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-2 rounded-lg">
                <img
                  src="https://www.gstatic.com/images/branding/product/2x/gcp_48dp.png"
                  alt="GCP"
                  className="w-5 h-5"
                />
                <span className="text-sm font-medium">Managed via GCP Marketplace</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Current Plan Card */}
        <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl p-8 text-white mb-8">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-indigo-200 text-sm font-medium mb-2">Current Plan</p>
              <h2 className="text-4xl font-bold mb-2">
                {(() => {
                  const tierName = subscription?.tier_display_name || subscription?.tier || 'professional';
                  // Map enterprise_plus to enterprise +
                  if (tierName.toLowerCase() === 'enterprise_plus') return 'enterprise +';
                  return tierName.toLowerCase();
                })()}
              </h2>
              <p className="text-2xl font-semibold mb-4">
                ${estimatedBill.toFixed(2)} <span className="text-lg font-normal text-indigo-200">/month</span>
              </p>
              <div className="flex items-center gap-2 text-indigo-100">
                <Calendar className="w-4 h-4" />
                <span className="text-sm">
                  Billing period: {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </span>
              </div>
            </div>

            {!subscription?.gcp_entitlement_id && (
              <div className="flex gap-3">
                <button
                  onClick={handleManagePayment}
                  className="px-6 py-3 bg-white/10 text-white border border-white/20 rounded-lg font-semibold hover:bg-white/20 transition-colors"
                >
                  Manage Payment
                </button>
                <button
                  onClick={() => window.location.href = '/pricing'}
                  className="px-6 py-3 bg-white text-indigo-600 rounded-lg font-semibold hover:bg-indigo-50 transition-colors"
                >
                  Upgrade Plan
                </button>
              </div>
            )}

            {subscription?.gcp_entitlement_id && (
              <a
                href={`https://console.cloud.google.com/marketplace`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-indigo-600 rounded-lg font-semibold hover:bg-indigo-50 transition-colors"
              >
                Manage in GCP
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>
        </div>

        {/* Usage Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-indigo-600" />
              </div>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <p className="text-gray-600 text-sm mb-1">Active Users</p>
            <p className="text-3xl font-bold text-gray-900">
              {usage?.usage?.active_users?.quantity || 0}
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Limit: {subscription?.limits?.max_users || 'Unlimited'}
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Zap className="w-6 h-6 text-green-600" />
              </div>
              <BarChart3 className="w-5 h-5 text-blue-500" />
            </div>
            <p className="text-gray-600 text-sm mb-1">AI Categorizations</p>
            <p className="text-3xl font-bold text-gray-900">
              {usage?.usage?.ai_categorization?.quantity || 0}
            </p>
            <p className="text-xs text-gray-500 mt-2">
              This month
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <CreditCard className="w-6 h-6 text-purple-600" />
              </div>
              <DollarSign className="w-5 h-5 text-orange-500" />
            </div>
            <p className="text-gray-600 text-sm mb-1">AP2 Transactions</p>
            <p className="text-3xl font-bold text-gray-900">
              {usage?.usage?.ap2_transaction?.quantity || 0}
            </p>
            <p className="text-xs text-gray-500 mt-2">
              This month
            </p>
          </div>
        </div>

        {/* Usage Metrics */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Usage This Month</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <UsageProgressBar
              label="AI Categorizations"
              current={usage?.usage?.ai_categorization?.quantity || 0}
              limit={subscription?.limits?.max_ai_categorizations}
              overage={Math.max(0, (usage?.usage?.ai_categorization?.quantity || 0) - (subscription?.limits?.max_ai_categorizations || Infinity))}
              overageFee={usage?.usage?.ai_categorization?.fees || 0}
              unit="categorizations"
            />

            <UsageProgressBar
              label="AP2 Transactions"
              current={usage?.usage?.ap2_transaction?.quantity || 0}
              limit={subscription?.limits?.max_ap2_transactions}
              overage={Math.max(0, (usage?.usage?.ap2_transaction?.quantity || 0) - (subscription?.limits?.max_ap2_transactions || Infinity))}
              overageFee={usage?.usage?.ap2_transaction?.fees || 0}
              unit="transactions"
            />

            <UsageProgressBar
              label="OCR Scans"
              current={usage?.usage?.ocr_scan?.quantity || 0}
              limit={subscription?.limits?.ocr_scans_included}
              overage={Math.max(0, (usage?.usage?.ocr_scan?.quantity || 0) - (subscription?.limits?.ocr_scans_included || Infinity))}
              overageFee={usage?.usage?.ocr_scan?.fees || 0}
              unit="scans"
            />

            <UsageProgressBar
              label="Expenses Submitted"
              current={usage?.usage?.expense?.quantity || 0}
              limit={subscription?.limits?.max_expenses_per_month}
              unit="expenses"
            />
          </div>
        </div>

        {/* Estimated Bill */}
        <div className="bg-white rounded-lg border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Estimated Monthly Bill</h2>

          <div className="space-y-4">
            <div className="flex justify-between items-center pb-4 border-b">
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
                        Consider upgrading to eliminate overage charges and save money
                      </p>
                    </div>
                  </div>
                </div>
              </>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-gray-300">
              <span className="text-xl font-bold text-gray-900">Total Estimated</span>
              <span className="text-3xl font-bold text-indigo-600">
                ${totalEstimated.toFixed(2)}
              </span>
            </div>

            {subscription?.gcp_entitlement_id && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-blue-900">
                  <strong>Note:</strong> This bill will be charged to your Google Cloud billing account.
                  You can view detailed invoices in the{' '}
                  <a
                    href="https://console.cloud.google.com/billing"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
                  >
                    GCP Console
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Available Plans (if direct customer) */}
        {!subscription?.gcp_entitlement_id && tiers.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Upgrade Your Plan</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {tiers.map((tier) => {
                const isCurrent = tier.tier === subscription?.tier;
                const isHigher = tier.price_monthly > estimatedBill;

                return (
                  <div
                    key={tier.tier}
                    className={`p-6 rounded-lg border-2 ${
                      isCurrent
                        ? 'border-indigo-600 bg-indigo-50'
                        : 'border-gray-200 hover:border-indigo-300'
                    }`}
                  >
                    <h3 className="text-xl font-bold mb-2">{tier.display_name || tier.tier}</h3>
                    <p className="text-3xl font-bold text-gray-900 mb-4">
                      ${tier.price_monthly}
                      <span className="text-lg font-normal text-gray-600">/mo</span>
                    </p>

                    <ul className="space-y-2 mb-6 text-sm">
                      <li className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-green-500" />
                        {tier.limits?.max_users == null ? 'Unlimited' : tier.limits.max_users} users
                      </li>
                      <li className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-green-500" />
                        {tier.limits?.max_ai_categorizations == null
                          ? 'Unlimited'
                          : tier.limits.max_ai_categorizations.toLocaleString()}{' '}
                        AI categorizations
                      </li>
                      <li className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4 text-green-500" />
                        {tier.limits?.max_ap2_transactions == null
                          ? 'Unlimited'
                          : tier.limits.max_ap2_transactions}{' '}
                        AP2 transactions
                      </li>
                    </ul>

                    {isCurrent ? (
                      <button
                        disabled
                        className="w-full py-2 bg-indigo-600 text-white rounded-lg font-semibold opacity-50 cursor-not-allowed"
                      >
                        Current Plan
                      </button>
                    ) : (
                      <button
                        onClick={() => handleUpgrade(tier.tier)}
                        className={`w-full py-2 rounded-lg font-semibold ${
                          isHigher
                            ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {isHigher ? 'Upgrade' : 'Downgrade'}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4 mt-8">
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Download className="w-4 h-4" />
            Export Report
          </button>

          <button
            onClick={() => window.location.href = '/settings'}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Settings className="w-4 h-4" />
            Billing Settings
          </button>
        </div>
      </div>
    </div>
  );
};

export default BillingDashboard;
