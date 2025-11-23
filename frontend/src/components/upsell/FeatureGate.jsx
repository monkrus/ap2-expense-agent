import React, { useState } from 'react';
import { Lock, Sparkles, ArrowRight, Crown } from 'lucide-react';

/**
 * FeatureGate - Wraps premium features to show upgrade prompt
 *
 * Usage:
 * <FeatureGate
 *   feature="Advanced Analytics"
 *   requiredPlan="Professional"
 *   userPlan="Free"
 * >
 *   <AdvancedAnalyticsDashboard />
 * </FeatureGate>
 */
const FeatureGate = ({
  children,
  feature,
  requiredPlan = "Professional",
  userPlan = "Free",
  description = null,
  showPreview = false, // Show blurred preview of content
}) => {
  const [isHovered, setIsHovered] = useState(false);

  // Plan hierarchy for comparison
  const planHierarchy = ['Free', 'Starter', 'Professional', 'Enterprise'];
  const userPlanIndex = planHierarchy.indexOf(userPlan);
  const requiredPlanIndex = planHierarchy.indexOf(requiredPlan);

  // User has access if their plan is equal or higher
  const hasAccess = userPlanIndex >= requiredPlanIndex;

  if (hasAccess) {
    return children;
  }

  return (
    <div
      className="relative"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Blurred preview (optional) */}
      {showPreview && (
        <div className="absolute inset-0 overflow-hidden rounded-lg">
          <div className="blur-sm opacity-50 pointer-events-none">
            {children}
          </div>
        </div>
      )}

      {/* Lock overlay */}
      <div className={`relative ${showPreview ? '' : 'min-h-[200px]'} bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-dashed border-gray-300 rounded-xl p-8 flex flex-col items-center justify-center text-center`}>
        {/* Lock icon */}
        <div className={`p-4 rounded-full mb-4 transition-all ${
          isHovered
            ? 'bg-indigo-100 scale-110'
            : 'bg-gray-200'
        }`}>
          <Lock className={`w-8 h-8 transition-colors ${
            isHovered ? 'text-indigo-600' : 'text-gray-400'
          }`} />
        </div>

        {/* Feature name */}
        <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
          {feature}
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full">
            <Crown className="w-3 h-3" />
            {requiredPlan}
          </span>
        </h3>

        {/* Description */}
        <p className="text-gray-600 text-sm mb-6 max-w-sm">
          {description || `Upgrade to ${requiredPlan} to unlock ${feature.toLowerCase()} and take your expense management to the next level.`}
        </p>

        {/* Upgrade button */}
        <a
          href="/pricing"
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-all hover:shadow-lg"
        >
          <Sparkles className="w-4 h-4" />
          Upgrade to {requiredPlan}
          <ArrowRight className="w-4 h-4" />
        </a>

        {/* Current plan indicator */}
        <p className="text-xs text-gray-500 mt-4">
          You're currently on the {userPlan} plan
        </p>
      </div>
    </div>
  );
};

/**
 * FeatureBadge - Small badge to indicate premium features
 *
 * Usage:
 * <FeatureBadge plan="Professional" />
 */
export const FeatureBadge = ({ plan = "Pro", size = "sm" }) => {
  const sizes = {
    xs: 'text-[10px] px-1.5 py-0.5',
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
  };

  return (
    <span className={`inline-flex items-center gap-1 ${sizes[size]} bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-medium rounded-full`}>
      <Crown className={size === 'xs' ? 'w-2.5 h-2.5' : 'w-3 h-3'} />
      {plan}
    </span>
  );
};

/**
 * LockedFeatureButton - Button that shows feature is locked
 *
 * Usage:
 * <LockedFeatureButton feature="Export to CSV" requiredPlan="Starter" />
 */
export const LockedFeatureButton = ({
  feature,
  requiredPlan = "Starter",
  className = "",
}) => {
  return (
    <button
      onClick={() => window.location.href = '/pricing'}
      className={`inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-500 rounded-lg border border-gray-200 hover:bg-gray-200 hover:text-gray-700 transition-colors ${className}`}
    >
      <Lock className="w-4 h-4" />
      {feature}
      <FeatureBadge plan={requiredPlan} size="xs" />
    </button>
  );
};

export default FeatureGate;
