import React from 'react';
import { AlertTriangle, TrendingUp, ArrowRight } from 'lucide-react';

/**
 * UsageLimitWarning - Inline warning when approaching limits
 *
 * Usage:
 * <UsageLimitWarning
 *   feature="AI categorizations"
 *   currentUsage={85}
 *   limit={100}
 * />
 */
const UsageLimitWarning = ({
  feature,
  currentUsage,
  limit,
  showUpgradeLink = true,
  variant = 'auto' // 'auto', 'warning', 'critical', 'info'
}) => {
  const percentage = Math.round((currentUsage / limit) * 100);

  // Auto-determine variant based on percentage
  let effectiveVariant = variant;
  if (variant === 'auto') {
    if (percentage >= 100) effectiveVariant = 'critical';
    else if (percentage >= 90) effectiveVariant = 'critical';
    else if (percentage >= 70) effectiveVariant = 'warning';
    else return null; // Don't show if under 70%
  }

  const styles = {
    warning: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      icon: 'text-amber-500',
      text: 'text-amber-800',
      subtext: 'text-amber-600',
      bar: 'bg-amber-500',
      button: 'text-amber-700 hover:text-amber-800'
    },
    critical: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: 'text-red-500',
      text: 'text-red-800',
      subtext: 'text-red-600',
      bar: 'bg-red-500',
      button: 'text-red-700 hover:text-red-800'
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-500',
      text: 'text-blue-800',
      subtext: 'text-blue-600',
      bar: 'bg-blue-500',
      button: 'text-blue-700 hover:text-blue-800'
    }
  };

  const s = styles[effectiveVariant];

  const getMessage = () => {
    if (percentage >= 100) {
      return `You've reached your ${feature} limit for this month.`;
    }
    if (percentage >= 90) {
      return `You're almost out of ${feature}! Only ${limit - currentUsage} remaining.`;
    }
    return `You've used ${percentage}% of your ${feature} this month.`;
  };

  return (
    <div className={`${s.bg} ${s.border} border rounded-lg p-4`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className={`w-5 h-5 ${s.icon} flex-shrink-0 mt-0.5`} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium ${s.text}`}>
            {getMessage()}
          </p>

          {/* Progress bar */}
          <div className="mt-2 mb-2">
            <div className="flex justify-between text-xs mb-1">
              <span className={s.subtext}>{currentUsage} used</span>
              <span className={s.subtext}>{limit} limit</span>
            </div>
            <div className="h-1.5 bg-white rounded-full overflow-hidden">
              <div
                className={`h-full ${s.bar} rounded-full transition-all`}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
          </div>

          {showUpgradeLink && (
            <a
              href="/pricing"
              className={`inline-flex items-center gap-1 text-sm font-medium ${s.button} mt-1`}
            >
              Upgrade for more
              <ArrowRight className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * UsageMeter - Compact usage indicator for sidebars/headers
 */
export const UsageMeter = ({ feature, currentUsage, limit, onClick }) => {
  const percentage = Math.round((currentUsage / limit) * 100);

  const getColor = () => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-amber-500';
    return 'bg-green-500';
  };

  return (
    <button
      onClick={onClick}
      className="w-full p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left"
    >
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-medium text-gray-600">{feature}</span>
        <span className="text-xs text-gray-500">{currentUsage}/{limit}</span>
      </div>
      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor()} rounded-full transition-all`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      {percentage >= 70 && (
        <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          {percentage >= 90 ? 'Almost at limit' : 'Running low'}
        </p>
      )}
    </button>
  );
};

export default UsageLimitWarning;
