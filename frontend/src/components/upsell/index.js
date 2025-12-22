/**
 * Upsell Components
 *
 * Soft upsell components for converting free users to paid plans.
 *
 * Components:
 * - UpgradePrompt: Modal popup for upgrade prompts
 * - UsageLimitWarning: Inline warning when approaching limits
 * - UsageMeter: Compact usage indicator for sidebars
 * - FeatureGate: Wraps premium features to show upgrade prompt
 * - FeatureBadge: Small badge to indicate premium features
 * - LockedFeatureButton: Button that shows feature is locked
 * - UpgradeBanner: Dismissible banner for dashboard/pages
 * - SidebarUpgradeCard: Compact card for sidebar placement
 * - InlineUpgradePrompt: Small inline prompt for use within content
 *
 * Usage Examples:
 *
 * 1. Show upgrade modal when user hits limit:
 * ```jsx
 * import { UpgradePrompt } from '../components/upsell';
 *
 * <UpgradePrompt
 *   isOpen={showUpgrade}
 *   onClose={() => setShowUpgrade(false)}
 *   feature="AI Categorization"
 *   currentUsage={95}
 *   limit={100}
 * />
 * ```
 *
 * 2. Show warning when approaching limits:
 * ```jsx
 * import { UsageLimitWarning } from '../components/upsell';
 *
 * <UsageLimitWarning
 *   feature="AI categorizations"
 *   currentUsage={85}
 *   limit={100}
 * />
 * ```
 *
 * 3. Gate premium features:
 * ```jsx
 * import { FeatureGate } from '../components/upsell';
 *
 * <FeatureGate
 *   feature="Advanced Analytics"
 *   requiredPlan="Professional"
 *   userPlan={user.plan}
 * >
 *   <AdvancedAnalyticsDashboard />
 * </FeatureGate>
 * ```
 *
 * 4. Show banner on dashboard:
 * ```jsx
 * import { UpgradeBanner } from '../components/upsell';
 *
 * <UpgradeBanner variant="trial" daysLeft={7} />
 * ```
 */

export { default as UpgradePrompt } from "./UpgradePrompt";
export { default as UsageLimitWarning, UsageMeter } from "./UsageLimitWarning";
export {
  default as FeatureGate,
  FeatureBadge,
  LockedFeatureButton,
} from "./FeatureGate";
export {
  default as UpgradeBanner,
  SidebarUpgradeCard,
  InlineUpgradePrompt,
} from "./UpgradeBanner";
