import React from "react";
import { ArrowRight, Sparkles, X } from "lucide-react";

/**
 * UpgradePrompt - Modal/popup for upgrade prompts
 *
 * Usage:
 * <UpgradePrompt
 *   isOpen={showUpgrade}
 *   onClose={() => setShowUpgrade(false)}
 *   feature="AI Categorization"
 *   currentUsage={95}
 *   limit={100}
 * />
 */
const UpgradePrompt = ({
  isOpen,
  onClose,
  feature = "this feature",
  currentUsage = null,
  limit = null,
  title = null,
  description = null,
  recommendedPlan = "Professional",
}) => {
  if (!isOpen) return null;

  const defaultTitle =
    currentUsage !== null
      ? `You're running low on ${feature}`
      : `Unlock ${feature}`;

  const defaultDescription =
    currentUsage !== null
      ? `You've used ${currentUsage} of ${limit} ${feature.toLowerCase()}. Upgrade to get more and unlock advanced features.`
      : `This feature is available on our paid plans. Upgrade to ${recommendedPlan} to unlock ${feature.toLowerCase()} and more.`;

  const percentage =
    currentUsage !== null ? Math.round((currentUsage / limit) * 100) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
        {/* Header gradient */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-8 text-white">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-white/80 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-white/20 rounded-lg">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold">{title || defaultTitle}</h2>
          </div>

          <p className="text-indigo-100">{description || defaultDescription}</p>
        </div>

        {/* Usage bar (if applicable) */}
        {percentage !== null && (
          <div className="px-6 py-4 bg-gray-50 border-b">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Current usage</span>
              <span
                className={`font-semibold ${percentage >= 90 ? "text-red-600" : percentage >= 70 ? "text-amber-600" : "text-gray-900"}`}
              >
                {currentUsage} / {limit}
              </span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  percentage >= 90
                    ? "bg-red-500"
                    : percentage >= 70
                      ? "bg-amber-500"
                      : "bg-indigo-500"
                }`}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Benefits */}
        <div className="px-6 py-4">
          <p className="text-sm font-semibold text-gray-700 mb-3">
            With {recommendedPlan}, you get:
          </p>
          <ul className="space-y-2">
            {recommendedPlan === "Professional" ? (
              <>
                <BenefitItem text="Unlimited expenses" />
                <BenefitItem text="1,000 AI categorizations/month" />
                <BenefitItem text="500 receipt scans/month" />
                <BenefitItem text="Priority support" />
                <BenefitItem text="Dashboard analytics" />
              </>
            ) : (
              <>
                <BenefitItem text="Unlimited everything" />
                <BenefitItem text="SSO / SAML integration" />
                <BenefitItem text="Dedicated account manager" />
                <BenefitItem text="24/7 premium support" />
                <BenefitItem text="Custom integrations" />
              </>
            )}
          </ul>
        </div>

        {/* CTA */}
        <div className="px-6 py-4 bg-gray-50 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 px-4 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-100 transition-colors"
          >
            Maybe Later
          </button>
          <button
            onClick={() => (window.location.href = "/pricing")}
            className="flex-1 py-2.5 px-4 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
          >
            Upgrade Now
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

const BenefitItem = ({ text }) => (
  <li className="flex items-center gap-2 text-sm text-gray-600">
    <svg
      className="w-4 h-4 text-green-500 flex-shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
    {text}
  </li>
);

export default UpgradePrompt;
