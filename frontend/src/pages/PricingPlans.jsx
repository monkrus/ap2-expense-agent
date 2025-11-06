import React, { useState, useEffect, useMemo } from 'react';
import {
  Check, X, Zap, Users, CreditCard, Image, TrendingUp,
  ArrowRight, ExternalLink, Shield, Star, Sparkles, ArrowLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import billingAPI from '../services/billingAPI';
import paymentAPI from '../services/paymentAPI';

/**
 * Pricing Plans Page
 *
 * Displays all subscription tiers with:
 * - Feature comparison
 * - Pricing information
 * - Upgrade/downgrade actions
 * - GCP Marketplace integration
 */
const PricingPlans = () => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  const [tiers, setTiers] = useState([]);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState('monthly'); // 'monthly' or 'annual'

  useEffect(() => {
    loadPricingData();
  }, []);

  const loadPricingData = async () => {
    try {
      setLoading(true);

      // Load available tiers
      const tiersData = await billingAPI.getAllTiers();
      setTiers(tiersData.tiers || []);

      // Load current subscription
      try {
        const subscription = await billingAPI.getSubscription();
        // Only set if user actually has a subscription
        if (subscription?.has_subscription) {
          setCurrentSubscription(subscription);
        } else {
          setCurrentSubscription(null);
        }
      } catch (err) {
        // User might not have a subscription yet
        setCurrentSubscription(null);
      }
    } catch (err) {
      showError('Failed to load pricing information');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPlan = async (tierName) => {
    console.log('handleSelectPlan called with:', tierName);
    console.log('Current user:', user);

    if (!user) {
      console.log('No user, redirecting to login');
      window.location.href = '/login';
      return;
    }

    // If GCP customer, redirect to GCP Marketplace
    if (currentSubscription?.gcp_entitlement_id) {
      window.open(
        'https://console.cloud.google.com/marketplace',
        '_blank'
      );
      return;
    }

    try {
      setLoading(true);

      if (currentSubscription?.subscription_id) {
        // For existing subscriptions, use Stripe Customer Portal
        const { url } = await paymentAPI.createPortalSession();
        window.location.href = url;
      } else {
        // For new subscriptions, use Stripe Checkout
        const { url } = await paymentAPI.createCheckoutSession(tierName);
        window.location.href = url;
      }
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to start checkout');
      console.error(err);
      setLoading(false);
    }
  };

  const getTierBadge = (tierName) => {
    switch (tierName.toLowerCase()) {
      case 'professional':
        return (
          <span className="inline-flex items-center justify-center gap-1 px-3 py-1 bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-full min-w-[110px]">
            <Star className="w-3 h-3" />
            Most Popular
          </span>
        );
      case 'enterprise':
        return (
          <span className="inline-flex items-center justify-center gap-1 px-3 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full min-w-[110px]">
            <Sparkles className="w-3 h-3" />
            Best Value
          </span>
        );
      default:
        return null;
    }
  };

  const getButtonText = (tier) => {
    if (!currentSubscription) return 'Get Started';

    const currentTier = currentSubscription.tier?.toLowerCase();
    const thisTier = tier.tier.toLowerCase();

    if (currentTier === thisTier) return 'Active';
    if (tier.price_monthly > (currentSubscription.tier_price || 0)) return 'Upgrade';
    return 'Downgrade';
  };

  const getButtonStyle = (tier) => {
    if (!currentSubscription) {
      return tier.tier.toLowerCase() === 'professional'
        ? 'bg-indigo-600 text-white hover:bg-indigo-700'
        : 'bg-gray-100 text-gray-900 hover:bg-gray-200 border border-gray-300';
    }

    const currentTier = currentSubscription.tier?.toLowerCase();
    const thisTier = tier.tier.toLowerCase();

    if (currentTier === thisTier) {
      return 'bg-gray-100 text-gray-500 cursor-not-allowed';
    }

    return tier.price_monthly > (currentSubscription.tier_price || 0)
      ? 'bg-indigo-600 text-white hover:bg-indigo-700'
      : 'bg-gray-100 text-gray-900 hover:bg-gray-200 border border-gray-300';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading pricing plans...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-indigo-50">
      {/* Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Back to Dashboard Button */}
        <div className="mb-8">
          <button
            onClick={() => window.location.href = '/dashboard'}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Dashboard
          </button>
        </div>

        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Choose the plan that's right for your team. All plans include our core expense management features with AI-powered categorization.
          </p>
        </div>

        {/* GCP Marketplace Badge */}
        {currentSubscription?.gcp_entitlement_id && (
          <div className="inline-flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-6 py-3 mb-8">
            <img
              src="https://www.gstatic.com/images/branding/product/2x/gcp_48dp.png"
              alt="GCP"
              className="w-6 h-6"
            />
            <span className="text-blue-900 font-medium">
              You're a Google Cloud Marketplace customer
            </span>
            <a
              href="https://console.cloud.google.com/marketplace"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700 font-semibold inline-flex items-center gap-1"
            >
              Manage in GCP
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        )}

        {/* Billing Cycle Toggle */}
        <div className="inline-flex items-center bg-gray-100 rounded-full p-1.5 shadow-inner mb-12">
          <button
            onClick={() => {
              console.log('Monthly clicked!');
              setBillingCycle('monthly');
            }}
            className={`px-8 py-3 rounded-full text-sm font-semibold transition-all duration-150 ease-in-out z-10 ${
              billingCycle === 'monthly'
                ? 'bg-white text-indigo-600 shadow-md scale-105'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => {
              console.log('Annual clicked!');
              setBillingCycle('annual');
            }}
            className={`px-8 py-3 rounded-full text-sm font-semibold transition-all duration-150 ease-in-out relative z-10 ${
              billingCycle === 'annual'
                ? 'bg-white text-indigo-600 shadow-md scale-105'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Annual
            <span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs font-bold px-2.5 py-1 rounded-full whitespace-nowrap shadow-sm pointer-events-none">
              Save 20%
            </span>
          </button>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 items-stretch">
          {tiers.map((tier) => {
            const isCurrent = currentSubscription?.tier?.toLowerCase() === tier.tier.toLowerCase();
            const isPopular = tier.tier.toLowerCase() === 'professional';
            const price = billingCycle === 'annual' ? tier.price_monthly * 12 * 0.8 : tier.price_monthly;

            return (
              <div
                key={tier.tier}
                className={`relative bg-white rounded-2xl shadow-lg overflow-hidden transition-all hover:shadow-2xl flex flex-col h-full ${
                  isCurrent ? 'ring-4 ring-green-500 scale-105' : ''
                }`}
              >
                {/* Badge */}
                <div className="absolute top-4 right-4 z-10">
                  {isCurrent ? (
                    <span className="inline-flex items-center justify-center gap-1 px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full min-w-[110px]">
                      <Check className="w-3 h-3" />
                      Current Plan
                    </span>
                  ) : (
                    getTierBadge(tier.tier || tier.display_name)
                  )}
                </div>

                <div className="p-8 flex flex-col flex-grow">
                  {/* Tier Name - Add padding-right to avoid badge overlap */}
                  <h3 className="text-2xl font-bold text-gray-900 mb-2 pr-32 whitespace-nowrap">
                    {(() => {
                      const tierName = tier.display_name || tier.tier;
                      if (tierName.toLowerCase() === 'enterprise_plus') return 'enterprise +';
                      return tierName.toLowerCase();
                    })()}
                  </h3>

                  {/* Price */}
                  <div className="mb-6">
                    <span className="text-5xl font-bold text-gray-900">
                      ${billingCycle === 'annual' ? Math.floor(price / 12) : price}
                    </span>
                    <span className="text-gray-600 ml-2">
                      {billingCycle === 'annual' ? '/month (billed annually)' : '/month'}
                    </span>
                  </div>

                  {/* Description */}
                  <p className="text-gray-600 mb-6 min-h-[48px]">
                    {tier.description || `Perfect for ${tier.tier === 'free' ? 'individuals' : tier.tier === 'starter' ? 'small teams' : tier.tier === 'professional' ? 'growing businesses' : 'large enterprises'}`}
                  </p>

                  {/* CTA Button */}
                  <button
                    onClick={() => handleSelectPlan(tier.tier)}
                    disabled={isCurrent}
                    className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors mb-8 ${getButtonStyle(tier)}`}
                  >
                    {getButtonText(tier)}
                    {!isCurrent && <ArrowRight className="inline ml-2 w-4 h-4" />}
                  </button>

                  {/* Features */}
                  <div className="space-y-4 border-t pt-6 flex-grow">
                    <h4 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">
                      Features
                    </h4>

                    <Feature
                      icon={<Users className="w-4 h-4" />}
                      text={`${tier.limits?.max_users == null ? 'Unlimited' : tier.limits.max_users} users`}
                    />

                    <Feature
                      icon={<TrendingUp className="w-4 h-4" />}
                      text={`${tier.limits?.max_expenses_per_month == null ? 'Unlimited' : tier.limits.max_expenses_per_month.toLocaleString()} expenses/month`}
                    />

                    <Feature
                      icon={<Zap className="w-4 h-4" />}
                      text={`${tier.limits?.max_ai_categorizations == null ? 'Unlimited' : tier.limits.max_ai_categorizations.toLocaleString()} AI categorizations`}
                    />

                    <Feature
                      icon={<CreditCard className="w-4 h-4" />}
                      text={`${tier.limits?.max_ap2_transactions == null ? 'Unlimited' : tier.limits.max_ap2_transactions} AP2 transactions`}
                    />

                    <Feature
                      icon={<Image className="w-4 h-4" />}
                      text={`${tier.limits?.ocr_scans_included == null ? 'Unlimited' : tier.limits.ocr_scans_included} OCR scans`}
                    />

                    {/* Advanced Features - Always show in same order */}
                    <Feature
                      icon={<Shield className="w-4 h-4" />}
                      text={tier.features?.priority_support
                        ? `Priority support${tier.features?.support_channels ? ` (${tier.features.support_channels.join(', ')})` : ''}`
                        : 'Email support only'}
                      muted={!tier.features?.priority_support}
                    />

                    <Feature
                      icon={<Check className="w-4 h-4" />}
                      text="SSO & SAML"
                      muted={!tier.features?.sso_enabled}
                    />

                    <Feature
                      icon={<Check className="w-4 h-4" />}
                      text="Custom integrations"
                      muted={!tier.features?.custom_integrations}
                    />

                    <Feature
                      icon={<Check className="w-4 h-4" />}
                      text="API access"
                      muted={!tier.features?.api_access}
                    />

                    <Feature
                      icon={<Check className="w-4 h-4" />}
                      text="Advanced analytics"
                      muted={!tier.features?.advanced_analytics}
                    />

                    <Feature
                      icon={<Check className="w-4 h-4" />}
                      text="White-label branding"
                      muted={!tier.features?.white_label}
                    />

                    <Feature
                      icon={<Check className="w-4 h-4" />}
                      text="Dedicated account manager"
                      muted={!tier.features?.dedicated_account_manager}
                    />

                    <Feature
                      icon={<Check className="w-4 h-4" />}
                      text={tier.features?.sla_guarantee ? `${tier.features.sla_guarantee} SLA` : 'Standard SLA'}
                      muted={!tier.features?.sla_guarantee}
                    />
                  </div>

                  {/* Overage Pricing */}
                  {tier.tier !== 'enterprise' && tier.tier !== 'enterprise_plus' && tier.tier !== 'free' && (
                    <div className="mt-6 pt-6 border-t">
                      <h4 className="font-semibold text-gray-900 text-sm mb-3">
                        Overage Pricing
                      </h4>
                      <div className="text-sm text-gray-600 space-y-1">
                        <p>• $0.05 per extra AI categorization</p>
                        <p>• $0.10 per extra AP2 transaction</p>
                        <p>• $0.02 per extra OCR scan</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature Comparison Table */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">
          Compare All Features
        </h2>

        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                  Feature
                </th>
                {tiers.map((tier) => (
                  <th key={tier.tier} className="px-6 py-4 text-center text-sm font-semibold text-gray-900">
                    {(() => {
                      const tierName = tier.display_name || tier.tier;
                      if (tierName.toLowerCase() === 'enterprise_plus') return 'enterprise +';
                      return tierName.toLowerCase();
                    })()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {/* Core Limits */}
              <ComparisonRow
                feature="Users"
                values={tiers.map(t => t.limits?.max_users == null ? 'Unlimited' : t.limits.max_users)}
              />
              <ComparisonRow
                feature="Expenses per month"
                values={tiers.map(t => t.limits?.max_expenses_per_month == null ? 'Unlimited' : t.limits.max_expenses_per_month.toLocaleString())}
              />
              <ComparisonRow
                feature="AI Categorizations"
                values={tiers.map(t => t.limits?.max_ai_categorizations == null ? 'Unlimited' : t.limits.max_ai_categorizations.toLocaleString())}
              />
              <ComparisonRow
                feature="AP2 Transactions"
                values={tiers.map(t => t.limits?.max_ap2_transactions == null ? 'Unlimited' : t.limits.max_ap2_transactions)}
              />
              <ComparisonRow
                feature="OCR Scans"
                values={tiers.map(t => t.limits?.ocr_scans_included == null ? 'Unlimited' : t.limits.ocr_scans_included)}
              />

              {/* Advanced Features - Same order as pricing cards */}
              <ComparisonRow
                feature="Support"
                values={tiers.map((t) => t.features?.priority_support
                  ? (t.features?.support_channels?.join(', ') || 'Priority')
                  : 'Email only')}
              />
              <ComparisonRow
                feature="SSO & SAML"
                values={tiers.map((t) => t.features?.sso_enabled || false)}
              />
              <ComparisonRow
                feature="Custom Integrations"
                values={tiers.map((t) => t.features?.custom_integrations || false)}
              />
              <ComparisonRow
                feature="API Access"
                values={tiers.map((t) => t.features?.api_access || false)}
              />
              <ComparisonRow
                feature="Advanced Analytics"
                values={tiers.map((t) => t.features?.advanced_analytics || false)}
              />
              <ComparisonRow
                feature="White-Label Branding"
                values={tiers.map((t) => t.features?.white_label || false)}
              />
              <ComparisonRow
                feature="Dedicated Account Manager"
                values={tiers.map((t) => t.features?.dedicated_account_manager || false)}
              />
              <ComparisonRow
                feature="SLA Guarantee"
                values={tiers.map((t) => t.features?.sla_guarantee || 'Standard')}
              />
              <ComparisonRow
                feature="Data Retention"
                values={tiers.map((t) => `${t.limits?.data_retention_days || 30} days`)}
              />
            </tbody>
          </table>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">
          Frequently Asked Questions
        </h2>

        <div className="space-y-6">
          <FAQItem
            question="Can I change my plan later?"
            answer="Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any charges."
          />
          <FAQItem
            question="What happens if I exceed my plan limits?"
            answer="You'll be charged overage fees based on your usage. Pro plan: $0.05/AI categorization, $0.10/AP2 transaction. Enterprise plan has no overage fees."
          />
          <FAQItem
            question="Do you offer annual billing?"
            answer="Yes! Annual billing saves you 20% compared to monthly billing. Simply toggle to 'Annual' above to see the discounted rates."
          />
          <FAQItem
            question="Is there a free trial?"
            answer="Yes! All paid plans come with a 14-day free trial. No credit card required to start."
          />
          <FAQItem
            question="What payment methods do you accept?"
            answer="We accept all major credit cards via Stripe. Google Cloud Marketplace customers are billed through their GCP account."
          />
          <FAQItem
            question="Can I cancel anytime?"
            answer="Yes! You can cancel your subscription at any time. You'll retain access until the end of your billing period."
          />
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to streamline your expense management?
          </h2>
          <p className="text-xl text-indigo-100 mb-8">
            Join hundreds of companies using AP2 Expense Agent to automate their expense workflows
          </p>
          <button
            onClick={() => handleSelectPlan('professional')}
            className="bg-white text-indigo-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-colors inline-flex items-center gap-2"
          >
            Start Free Trial
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

// Feature Component
const Feature = ({ icon, text, muted = false }) => (
  <div className={`flex items-center gap-3 ${muted ? 'text-gray-400' : 'text-gray-700'}`}>
    <div className={`flex-shrink-0 ${muted ? 'text-gray-300' : 'text-green-500'}`}>
      {icon}
    </div>
    <span className={`text-sm ${muted ? 'line-through' : ''}`}>{text}</span>
  </div>
);

// Comparison Row Component
const ComparisonRow = ({ feature, values }) => (
  <tr>
    <td className="px-6 py-4 text-sm font-medium text-gray-900">
      {feature}
    </td>
    {values.map((value, index) => (
      <td key={index} className="px-6 py-4 text-center text-sm text-gray-700">
        {typeof value === 'boolean' ? (
          value ? (
            <Check className="w-5 h-5 text-green-500 mx-auto" />
          ) : (
            <X className="w-5 h-5 text-gray-300 mx-auto" />
          )
        ) : (
          value
        )}
      </td>
    ))}
  </tr>
);

// FAQ Item Component
const FAQItem = ({ question, answer }) => (
  <div className="bg-white rounded-lg shadow-md p-6">
    <h3 className="text-lg font-semibold text-gray-900 mb-2">
      {question}
    </h3>
    <p className="text-gray-600">
      {answer}
    </p>
  </div>
);

export default PricingPlans;
