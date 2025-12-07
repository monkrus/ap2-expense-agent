import React, { useState } from "react";
import { X, Sparkles, ArrowRight, Zap, Gift, TrendingUp } from "lucide-react";

/**
 * UpgradeBanner - Dismissible banner for dashboard/pages
 *
 * Usage:
 * <UpgradeBanner
 *   variant="trial"
 *   daysLeft={7}
 * />
 */
const UpgradeBanner = ({
  variant = "upgrade", // 'upgrade', 'trial', 'limit', 'promo'
  daysLeft = null,
  feature = null,
  usagePercent = null,
  promoCode = null,
  promoDiscount = null,
  onDismiss = null,
  dismissible = true,
}) => {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) return null;

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  const variants = {
    upgrade: {
      bg: "bg-gradient-to-r from-indigo-600 to-purple-600",
      icon: Sparkles,
      title: "Unlock the full power of AP2",
      subtitle:
        "Get unlimited expenses, AI categorization, and priority support.",
      buttonText: "View Plans",
      buttonStyle: "bg-white text-indigo-600 hover:bg-gray-100",
    },
    trial: {
      bg: "bg-gradient-to-r from-amber-500 to-orange-500",
      icon: Gift,
      title: `Your free trial ends in ${daysLeft} day${daysLeft !== 1 ? "s" : ""}`,
      subtitle: "Add a payment method to keep all your features.",
      buttonText: "Upgrade Now",
      buttonStyle: "bg-white text-amber-600 hover:bg-gray-100",
    },
    limit: {
      bg: "bg-gradient-to-r from-red-500 to-pink-500",
      icon: TrendingUp,
      title: `You've used ${usagePercent}% of your ${feature || "monthly limit"}`,
      subtitle: "Upgrade to avoid interruptions to your workflow.",
      buttonText: "Get More",
      buttonStyle: "bg-white text-red-600 hover:bg-gray-100",
    },
    promo: {
      bg: "bg-gradient-to-r from-green-500 to-emerald-500",
      icon: Zap,
      title: `Special offer: ${promoDiscount || "20%"} off your first 3 months!`,
      subtitle: promoCode
        ? `Use code ${promoCode} at checkout.`
        : "Limited time offer.",
      buttonText: "Claim Offer",
      buttonStyle: "bg-white text-green-600 hover:bg-gray-100",
    },
  };

  const v = variants[variant];
  const Icon = v.icon;

  return (
    <div className={`${v.bg} text-white px-4 py-3 relative`}>
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 flex-shrink-0" />
          <div>
            <span className="font-semibold">{v.title}</span>
            <span className="hidden sm:inline text-white/90 ml-2">
              {v.subtitle}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="/pricing"
            className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-lg font-medium text-sm transition-colors ${v.buttonStyle}`}
          >
            {v.buttonText}
            <ArrowRight className="w-4 h-4" />
          </a>

          {dismissible && (
            <button
              onClick={handleDismiss}
              className="text-white/80 hover:text-white p-1"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * SidebarUpgradeCard - Compact card for sidebar placement
 */
export const SidebarUpgradeCard = ({ userPlan = "Free", className = "" }) => {
  if (userPlan === "Enterprise") return null;

  return (
    <div
      className={`bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100 rounded-xl p-4 ${className}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-4 h-4 text-indigo-600" />
        <span className="text-sm font-semibold text-indigo-900">
          {userPlan === "Free" ? "Upgrade to Pro" : "Go Enterprise"}
        </span>
      </div>
      <p className="text-xs text-indigo-700 mb-3">
        {userPlan === "Free"
          ? "Unlock unlimited expenses and AI features."
          : "Get unlimited everything with dedicated support."}
      </p>
      <a
        href="/pricing"
        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
      >
        Learn more
        <ArrowRight className="w-3 h-3" />
      </a>
    </div>
  );
};

/**
 * InlineUpgradePrompt - Small inline prompt for use within content
 */
export const InlineUpgradePrompt = ({ feature, plan = "Professional" }) => {
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-50 border border-indigo-100 rounded-lg text-sm">
      <Sparkles className="w-4 h-4 text-indigo-500" />
      <span className="text-indigo-900">
        <span className="font-medium">{feature}</span> is a {plan} feature.
      </span>
      <a
        href="/pricing"
        className="font-medium text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1"
      >
        Upgrade
        <ArrowRight className="w-3 h-3" />
      </a>
    </div>
  );
};

export default UpgradeBanner;
