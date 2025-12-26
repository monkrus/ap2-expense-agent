import React, { useState, useEffect } from "react";
import {
  Check,
  X,
  ArrowRight,
  ArrowLeft,
  Shield,
  Zap,
  Users,
  Building2,
  Sparkles,
  HelpCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import billingAPI from "../services/billingAPI";

/**
 * Pricing Plans Page - Redesigned
 *
 * Shows 3 pricing tiers with monthly/annual options
 * and clear feature comparison
 */

// Define the 3 pricing tiers
const PRICING_TIERS = [
  {
    id: "free",
    name: "Free",
    tagline: "Experience AP2 Automation",
    description:
      "Try our revolutionary AP2 payment protocol free forever. Perfect for individuals getting started.",
    highlights: ["20 AP2 transactions/month", "OCR receipt scanning", "No credit card required"],
    icon: Zap,
    color: "gray",
    buttonText: "Get Started Free",
    monthlyPrice: 0,
    annualPrice: 0,
    features: {
      users: "1 user",
      organizations: "1 organization",
      expenses: "30 expenses/month",
      aiCategorization: "Manual only",
      receiptScanning: "20 OCR scans",
      ap2Transactions: "20 AP2 payments/month",
      support: "Help docs only",
      reporting: "Basic reports",
      integrations: "None",
      apiAccess: false,
      customCategories: false,
      approvalWorkflows: false,
      sso: false,
      dedicatedManager: false,
      sla: "None",
      dataRetention: "90 days",
    },
  },
  {
    id: "starter",
    name: "Starter",
    tagline: "AI-Powered Productivity",
    description:
      "Stop manual categorization! Let AI handle your expenses automatically. Perfect for small teams.",
    highlights: ["Everything in Free", "200 AI categorizations", "100 AP2 transactions", "Email support"],
    icon: Users,
    color: "blue",
    buttonText: "Subscribe in GCP",
    monthlyPrice: 29,
    annualPrice: 24,
    features: {
      users: "25 users",
      organizations: "3 organizations",
      expenses: "500 expenses/month",
      aiCategorization: "200 AI categorizations",
      receiptScanning: "200 OCR scans",
      ap2Transactions: "100 AP2 payments/month",
      support: "Email support",
      reporting: "Advanced reports",
      integrations: "Basic integrations",
      apiAccess: false,
      customCategories: true,
      approvalWorkflows: false,
      sso: false,
      dedicatedManager: false,
      sla: "Standard",
      dataRetention: "365 days",
    },
  },
  {
    id: "professional",
    name: "Professional",
    tagline: "Best for growing teams",
    description:
      "Scale your business with powerful AI, advanced workflows, and priority support. Perfect for companies up to 100 users.",
    highlights: [
      "100 users included",
      "2,000 expenses/month",
      "1,000 AI categorizations",
      "500 AP2 transactions",
      "Advanced approval workflows",
      "Priority support",
    ],
    icon: Building2,
    color: "indigo",
    popular: true,
    buttonText: "Subscribe in GCP",
    monthlyPrice: 99,
    annualPrice: 82,
    features: {
      users: "100 users",
      organizations: "10 organizations",
      expenses: "2,000 expenses/month",
      aiCategorization: "1,000 AI categorizations",
      receiptScanning: "1,000 OCR scans",
      ap2Transactions: "500 AP2 payments/month",
      support: "Priority support",
      reporting: "Advanced analytics",
      integrations: "All integrations",
      apiAccess: true,
      customCategories: true,
      approvalWorkflows: true,
      sso: false,
      dedicatedManager: false,
      sla: "99.9% uptime",
      dataRetention: "730 days (2 years)",
    },
  },
];

// GCP Marketplace product page URL (where users can subscribe)
const MARKETPLACE_PRODUCT_URL =
  import.meta.env.VITE_GCP_MARKETPLACE_URL ||
  "https://console.cloud.google.com/marketplace";

// Feature comparison data for the table
const FEATURE_CATEGORIES = [
  {
    name: "Usage Limits",
    features: [
      { name: "Team members", key: "users" },
      { name: "Organizations", key: "organizations" },
      { name: "Monthly expenses", key: "expenses" },
      { name: "AI categorizations", key: "aiCategorization" },
      { name: "Receipt scanning (OCR)", key: "receiptScanning" },
      { name: "Data retention", key: "dataRetention" },
    ],
  },
  {
    name: "Core Features",
    features: [
      {
        name: "Custom expense categories",
        key: "customCategories",
        boolean: true,
      },
      { name: "Approval workflows", key: "approvalWorkflows", boolean: true },
      { name: "Reports & analytics", key: "reporting" },
      { name: "Third-party integrations", key: "integrations" },
      { name: "API access", key: "apiAccess", boolean: true },
    ],
  },
  {
    name: "Support & Security",
    features: [
      { name: "Customer support", key: "support" },
      { name: "Single Sign-On (SSO)", key: "sso", boolean: true },
      {
        name: "Dedicated account manager",
        key: "dedicatedManager",
        boolean: true,
      },
      { name: "SLA guarantee", key: "sla" },
    ],
  },
];

const PricingPlans = () => {
  const { user } = useAuth();
  const [billingCycle, setBillingCycle] = useState("monthly");
  const [processingTier, setProcessingTier] = useState(null);
  const [expandedFAQ, setExpandedFAQ] = useState(null);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [loadingPlan, setLoadingPlan] = useState(false);

  // Fetch current subscription when user is logged in
  useEffect(() => {
    const fetchCurrentPlan = async () => {
      if (!user) {
        setCurrentPlan(null);
        return;
      }

      try {
        setLoadingPlan(true);
        const subscription = await billingAPI.getSubscription();
        // Get the tier name, default to 'free' if no subscription
        const tierName = subscription?.tier?.toLowerCase() || "free";
        setCurrentPlan(tierName);
      } catch (err) {
        console.error("Failed to fetch subscription:", err);
        // Default to free if error
        setCurrentPlan("free");
      } finally {
        setLoadingPlan(false);
      }
    };

    fetchCurrentPlan();
  }, [user]);

  const handleSelectPlan = async (tierId, selectedBillingCycle = "monthly") => {
    // SAFEGUARD: Prevent multiple simultaneous checkout attempts
    if (processingTier) {
      console.warn("Checkout already in progress, ignoring duplicate request");
      return;
    }

    // Free tier - just redirect to signup/dashboard
    if (tierId === "free") {
      if (!user) {
        window.location.href = "/register";
      } else {
        window.location.href = "/dashboard";
      }
      return;
    }

    if (!user) {
      localStorage.setItem("intended_plan", tierId);
      localStorage.setItem("intended_billing_cycle", selectedBillingCycle);
      window.location.href = "/login?redirect=pricing";
      return;
    }

    setProcessingTier(tierId);
    window.open(MARKETPLACE_PRODUCT_URL, "_blank");
    setProcessingTier(null);
  };

  const getPrice = (tier) => {
    return billingCycle === "annual" ? tier.annualPrice : tier.monthlyPrice;
  };

  const getAnnualSavings = (tier) => {
    const monthlyCost = tier.monthlyPrice * 12;
    const annualCost = tier.annualPrice * 12;
    return monthlyCost - annualCost;
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 pb-8">
        {/* Back Button */}
        <button
          onClick={() => (window.location.href = "/dashboard")}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-8 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Dashboard
        </button>

        {/* Title */}
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4">
            Choose Your Plan
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Subscribe via Google Cloud Marketplace. Trials and billing are
            managed in your GCP account.
          </p>

          {/* Billing Toggle */}
          <div className="inline-flex items-center bg-gray-100 rounded-full p-1.5 mb-8 relative z-20">
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                setBillingCycle("monthly");
              }}
              className={`px-8 py-3 rounded-full text-sm font-semibold transition-all cursor-pointer ${
                billingCycle === "monthly"
                  ? "bg-white text-gray-900 shadow-md"
                  : "text-gray-600 hover:text-gray-900 bg-transparent"
              }`}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                setBillingCycle("annual");
              }}
              className={`px-8 py-3 rounded-full text-sm font-semibold transition-all relative cursor-pointer ${
                billingCycle === "annual"
                  ? "bg-white text-gray-900 shadow-md"
                  : "text-gray-600 hover:text-gray-900 bg-transparent"
              }`}
            >
              Annual
              <span className="absolute -top-3 -right-3 bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full shadow-sm">
                Save 17%
              </span>
            </button>
          </div>

          {/* Current Selection Indicator */}
          <p className="text-sm font-semibold text-gray-700 mb-4">
            {billingCycle === "annual"
              ? "Billed annually (save 17%)"
              : "Billed monthly"}
          </p>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
          {PRICING_TIERS.map((tier) => {
            const TierIcon = tier.icon;
            const isProcessing = processingTier === tier.id;
            const price = getPrice(tier);
            const annualSavings = getAnnualSavings(tier);
            const isCurrentPlan = currentPlan === tier.id;

            return (
              <div
                key={tier.id}
                className={`relative bg-white rounded-2xl shadow-lg border-2 transition-all hover:shadow-xl ${
                  isCurrentPlan
                    ? "border-green-500 ring-4 ring-green-100"
                    : tier.popular
                      ? "border-indigo-500 ring-4 ring-indigo-100"
                      : "border-gray-200 hover:border-gray-300"
                }`}
              >
                {/* Current Plan Badge */}
                {isCurrentPlan && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="bg-green-500 text-white text-sm font-semibold px-4 py-1 rounded-full flex items-center gap-1">
                      <Check className="w-4 h-4" />
                      Current Plan
                    </span>
                  </div>
                )}

                {/* Popular Badge (only show if not current plan) */}
                {tier.popular && !isCurrentPlan && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="bg-indigo-500 text-white text-sm font-semibold px-4 py-1 rounded-full flex items-center gap-1">
                      <Sparkles className="w-4 h-4" />
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="p-6 flex flex-col h-full">
                  {/* Tier Header */}
                  <div className="flex items-center gap-3 mb-2">
                    <div
                      className={`p-2 rounded-lg ${
                        tier.color === "gray"
                          ? "bg-gray-100 text-gray-600"
                          : tier.color === "blue"
                            ? "bg-blue-100 text-blue-600"
                            : tier.color === "indigo"
                              ? "bg-indigo-100 text-indigo-600"
                              : "bg-purple-100 text-purple-600"
                      }`}
                    >
                      <TierIcon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-gray-900">
                        {tier.name}
                      </h3>
                      <p
                        className={`text-xs font-medium ${
                          tier.color === "gray"
                            ? "text-gray-600"
                            : tier.color === "blue"
                              ? "text-blue-600"
                              : tier.color === "indigo"
                                ? "text-indigo-600"
                                : "text-purple-600"
                        }`}
                      >
                        {tier.tagline}
                      </p>
                    </div>
                  </div>

                  {/* Description - fixed height */}
                  <p className="text-gray-600 mb-3 text-xs leading-relaxed h-14">
                    {tier.description}
                  </p>

                  {/* Key Highlights - fixed height */}
                  <div className="mb-4 bg-gray-50 rounded-lg p-3 h-32">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                      Highlights
                    </p>
                    <ul className="space-y-1">
                      {tier.highlights.map((highlight, idx) => (
                        <li
                          key={idx}
                          className="flex items-center gap-2 text-xs text-gray-700"
                        >
                          <Sparkles
                            className={`w-3 h-3 flex-shrink-0 ${
                              tier.color === "gray"
                                ? "text-gray-400"
                                : tier.color === "blue"
                                  ? "text-blue-500"
                                  : tier.color === "indigo"
                                    ? "text-indigo-500"
                                    : "text-purple-500"
                            }`}
                          />
                          {highlight}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Price */}
                  <div className="mb-4">
                    <div className="flex items-baseline gap-1">
                      {tier.id === "free" ? (
                        <span className="text-4xl font-bold text-gray-900">
                          Free
                        </span>
                      ) : (
                        <>
                          <span className="text-4xl font-bold text-gray-900">
                            ${price}
                          </span>
                          <span className="text-gray-500 text-sm">/month</span>
                        </>
                      )}
                    </div>
                    <p
                      className={`text-xs mt-1 h-4 ${tier.id === "free" ? "text-green-600 font-medium" : billingCycle === "annual" ? "text-green-600 font-medium" : "text-gray-500"}`}
                    >
                      {tier.id === "free"
                        ? "Forever free"
                        : billingCycle === "annual"
                          ? `$${tier.annualPrice * 12}/year (save $${annualSavings})`
                          : `or $${tier.annualPrice}/mo annually`}
                    </p>
                  </div>

                  {/* CTA Button */}
                  <button
                    onClick={() =>
                      !isCurrentPlan && handleSelectPlan(tier.id, billingCycle)
                    }
                    disabled={isProcessing || isCurrentPlan}
                    className={`w-full py-3 px-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 text-sm ${
                      isCurrentPlan
                        ? "bg-green-100 text-green-700 cursor-default"
                        : tier.popular
                          ? "bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
                          : tier.id === "enterprise"
                            ? "bg-purple-600 text-white hover:bg-purple-700"
                            : tier.id === "free"
                              ? "bg-gray-600 text-white hover:bg-gray-700"
                              : "bg-gray-900 text-white hover:bg-gray-800"
                    } ${isProcessing ? "opacity-75 cursor-wait" : ""}`}
                  >
                    {isCurrentPlan ? (
                      <>
                        <Check className="w-4 h-4" />
                        Current Plan
                      </>
                    ) : isProcessing ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                        Processing...
                      </>
                    ) : (
                      <>
                        {tier.buttonText}
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>

                  <p className="text-center text-xs text-gray-500 mt-2 flex items-center justify-center gap-1">
                    <Shield className="w-3 h-3" />
                    {tier.id === "free"
                      ? "No credit card required"
                      : tier.id === "enterprise"
                        ? "Custom pricing available"
                        : "14-day free trial"}
                  </p>

                  {/* Key Features - grows to fill remaining space */}
                  <div className="mt-4 pt-4 border-t border-gray-200 flex-grow">
                    <h4 className="font-semibold text-gray-900 mb-3 text-xs">
                      {tier.id === "free"
                        ? "What's included:"
                        : tier.id === "starter"
                          ? "Everything in Free, plus:"
                          : tier.id === "professional"
                            ? "Everything in Starter, plus:"
                            : "Everything in Professional, plus:"}
                    </h4>
                    <ul className="space-y-1.5">
                      <FeatureItem text={tier.features.users} small />
                      <FeatureItem text={tier.features.expenses} small />
                      <FeatureItem
                        text={tier.features.aiCategorization}
                        small
                      />
                      <FeatureItem text={tier.features.receiptScanning} small />
                      <FeatureItem text={tier.features.support} small />
                      {tier.features.apiAccess && (
                        <FeatureItem text="API access" highlight small />
                      )}
                      {tier.features.approvalWorkflows && (
                        <FeatureItem
                          text="Approval workflows"
                          highlight
                          small
                        />
                      )}
                      {tier.features.sso && (
                        <FeatureItem text="SSO / SAML" highlight small />
                      )}
                      {tier.features.dedicatedManager && (
                        <FeatureItem text="Dedicated manager" highlight small />
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Contact Sales CTA */}
        <div className="max-w-4xl mx-auto mt-16 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 text-center text-white shadow-xl">
          <h3 className="text-2xl font-bold mb-3">Need more than 100 users?</h3>
          <p className="text-indigo-100 mb-6 text-lg">
            We offer custom enterprise solutions with SSO, dedicated support, and tailored pricing for large teams.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href="mailto:sales@ap2expense.com"
              className="inline-flex items-center gap-2 bg-white text-indigo-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-all hover:shadow-lg"
            >
              Contact Sales
              <ArrowRight className="w-5 h-5" />
            </a>
            <span className="text-indigo-200 text-sm flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Custom pricing based on your needs
            </span>
          </div>
        </div>
      </div>

      {/* Feature Comparison Table */}
      <div className="bg-gray-50 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-4">
            Compare All Features
          </h2>
          <p className="text-gray-600 text-center mb-12 max-w-2xl mx-auto">
            A detailed comparison of what each plan offers to help you make the
            right choice.
          </p>

          <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
            <table className="w-full">
              {/* Table Header */}
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="py-4 px-6 text-left text-sm font-semibold text-gray-900 w-1/4">
                    Features
                  </th>
                  {PRICING_TIERS.map((tier) => (
                    <th key={tier.id} className="py-4 px-6 text-center">
                      <div className="text-lg font-bold text-gray-900">
                        {tier.name}
                      </div>
                      <div className="text-sm text-gray-500">
                        ${getPrice(tier)}/mo
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>

              {/* Table Body */}
              <tbody>
                {FEATURE_CATEGORIES.map((category, catIndex) => (
                  <React.Fragment key={category.name}>
                    {/* Category Header */}
                    <tr className="bg-gray-50">
                      <td
                        colSpan={4}
                        className="py-3 px-6 text-sm font-semibold text-gray-700 uppercase tracking-wide"
                      >
                        {category.name}
                      </td>
                    </tr>

                    {/* Features in Category */}
                    {category.features.map((feature, featIndex) => (
                      <tr
                        key={feature.key}
                        className={
                          featIndex !== category.features.length - 1
                            ? "border-b border-gray-100"
                            : ""
                        }
                      >
                        <td className="py-4 px-6 text-sm text-gray-700">
                          {feature.name}
                        </td>
                        {PRICING_TIERS.map((tier) => (
                          <td key={tier.id} className="py-4 px-6 text-center">
                            {feature.boolean ? (
                              tier.features[feature.key] ? (
                                <Check className="w-5 h-5 text-green-500 mx-auto" />
                              ) : (
                                <X className="w-5 h-5 text-gray-300 mx-auto" />
                              )
                            ) : (
                              <span className="text-sm text-gray-700">
                                {tier.features[feature.key]}
                              </span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="py-16">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-gray-600 text-center mb-12">
            Everything you need to know about our pricing
          </p>

          <div className="space-y-4">
            {FAQ_ITEMS.map((item, index) => (
              <FAQItem
                key={index}
                question={item.question}
                answer={item.answer}
                isOpen={expandedFAQ === index}
                onClick={() =>
                  setExpandedFAQ(expandedFAQ === index ? null : index)
                }
              />
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-indigo-600 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to get started?
          </h2>
          <p className="text-xl text-indigo-100 mb-8">
            Join thousands of teams managing expenses smarter with AP2
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button
              onClick={() => handleSelectPlan("professional", billingCycle)}
              className="bg-white text-indigo-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-all hover:shadow-lg inline-flex items-center gap-2"
            >
              Start Free Trial
              <ArrowRight className="w-5 h-5" />
            </button>
            <span className="text-indigo-200 text-sm flex items-center gap-2">
              <Shield className="w-4 h-4" />
              No credit card required
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Feature Item Component
const FeatureItem = ({ text, highlight = false, small = false }) => (
  <li
    className={`flex items-center ${small ? "gap-2" : "gap-3"} text-gray-700`}
  >
    <Check
      className={`${small ? "w-3 h-3" : "w-4 h-4"} flex-shrink-0 ${highlight ? "text-indigo-500" : "text-green-500"}`}
    />
    <span
      className={`${small ? "text-xs" : "text-sm"} ${highlight ? "font-medium text-gray-900" : ""}`}
    >
      {text}
    </span>
  </li>
);

// FAQ Item Component
const FAQItem = ({ question, answer, isOpen, onClick }) => (
  <div
    className={`bg-white rounded-xl border transition-all cursor-pointer ${
      isOpen
        ? "border-indigo-200 shadow-md"
        : "border-gray-200 hover:border-gray-300"
    }`}
    onClick={onClick}
  >
    <div className="p-5 flex items-center justify-between">
      <h3 className="font-semibold text-gray-900 flex items-center gap-3">
        <HelpCircle
          className={`w-5 h-5 ${isOpen ? "text-indigo-500" : "text-gray-400"}`}
        />
        {question}
      </h3>
      {isOpen ? (
        <ChevronUp className="w-5 h-5 text-indigo-500" />
      ) : (
        <ChevronDown className="w-5 h-5 text-gray-400" />
      )}
    </div>
    {isOpen && (
      <div className="px-5 pb-5 pt-0">
        <p className="text-gray-600 pl-8">{answer}</p>
      </div>
    )}
  </div>
);

// FAQ Data
const FAQ_ITEMS = [
  {
    question: "How does the 14-day free trial work?",
    answer:
      "Start any plan free for 14 days through Google Cloud Marketplace with full access to all features. No credit card required upfront. At the end of your trial, manage your subscription in Marketplace to continue.",
  },
  {
    question: "What's the difference between the plans?",
    answer:
      "Starter is perfect for small teams (up to 5 users) with basic needs. Professional is our most popular choice for growing businesses, offering unlimited expenses, advanced AI, and priority support. Enterprise provides unlimited everything plus dedicated support, SSO, and custom integrations.",
  },
  {
    question: "Can I upgrade or downgrade at any time?",
    answer:
      "Yes. Plan changes are managed in Google Cloud Marketplace and apply per Marketplace billing rules.",
  },
  {
    question: "What payment methods do you accept?",
    answer:
      "Billing is handled through Google Cloud Marketplace, so charges are billed to your Google Cloud billing account.",
  },
  {
    question: "How much can I save with annual billing?",
    answer:
      "Annual billing options are configured through the Marketplace listing. Contact sales or check the listing for current terms.",
  },
  {
    question: "What happens if I exceed my plan limits?",
    answer:
      "We'll notify you at 80% and 100% of your limits. You can upgrade anytime, or continue with small overage fees ($0.05 per AI categorization, $0.02 per OCR scan). Enterprise plans have unlimited usage.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Yes! We use bank-level 256-bit encryption, are SOC 2 Type II certified, and GDPR compliant. Enterprise plans include additional security features like SSO/SAML, audit logs, and data residency options.",
  },
  {
    question: "Can I cancel my subscription?",
    answer:
      "Cancel from Google Cloud Marketplace. Access continues until the end of your current billing period, per Marketplace terms.",
  },
  {
    question: "Do you offer discounts for nonprofits or startups?",
    answer:
      "Yes! We offer 50% off for registered nonprofits and special startup pricing through our partnership programs. Contact our sales team to learn more about eligibility and apply.",
  },
  {
    question: "How do I get help if I have questions?",
    answer:
      "Starter plans include email support (24-48 hour response). Professional plans get priority support with faster response times. Enterprise customers have access to 24/7 phone support and a dedicated account manager.",
  },
];

export default PricingPlans;
