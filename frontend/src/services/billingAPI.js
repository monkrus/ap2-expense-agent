/**
 * Billing & Subscription API Service
 * Handles billing, usage tracking, and subscription management
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Get authentication headers
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
};

// ============================================================================
// Usage Tracking
// ============================================================================

/**
 * Track a usage event
 * @param {string} usageType - expense, ai_categorization, ocr_scan, ap2_transaction
 * @param {number} quantity - Quantity to track (default: 1)
 * @param {object} metadata - Optional metadata
 */
export const trackUsage = async (usageType, quantity = 1, metadata = null) => {
  const response = await fetch(`${API_BASE_URL}/api/billing/usage/track`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      usage_type: usageType,
      quantity,
      metadata
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to track usage');
  }

  return response.json();
};

/**
 * Get monthly usage statistics
 * @param {string} usageType - Optional filter by usage type
 */
export const getMonthlyUsage = async (usageType = null) => {
  // Use organization-based endpoint
  const url = `${API_BASE_URL}/api/billing/org/usage/monthly`;

  const response = await fetch(url, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch usage statistics');
  }

  return response.json();
};

/**
 * Check if usage limit exceeded for a specific type
 * @param {string} usageType - Usage type to check
 */
export const checkUsageLimit = async (usageType) => {
  const response = await fetch(`${API_BASE_URL}/api/billing/usage/check-limit/${usageType}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to check usage limit');
  }

  return response.json();
};

// ============================================================================
// Subscription Management
// ============================================================================

/**
 * Get current subscription status
 */
export const getSubscription = async () => {
  // Use organization-based endpoint
  const response = await fetch(`${API_BASE_URL}/api/billing/org/subscription`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch subscription');
  }

  return response.json();
};

/**
 * Create a new subscription for the user's organization
 * @param {string} tier - Subscription tier (starter, professional, enterprise, enterprise_plus)
 * @param {number} trialDays - Number of trial days (default: 14)
 */
export const createSubscription = async (tier, trialDays = 14) => {
  // Use organization-based endpoint
  const response = await fetch(`${API_BASE_URL}/api/billing/org/subscription`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      tier,
      trial_days: trialDays
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create subscription');
  }

  return response.json();
};

/**
 * Upgrade subscription to a new tier
 * @param {string} subscriptionId - Subscription ID (not used in org-based API)
 * @param {string} newTier - New tier to upgrade to
 */
export const upgradeSubscription = async (subscriptionId, newTier) => {
  // Use organization-based endpoint (doesn't need subscriptionId)
  const response = await fetch(`${API_BASE_URL}/api/billing/org/subscription/upgrade?new_tier=${newTier}`, {
    method: 'PUT',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upgrade subscription');
  }

  return response.json();
};

/**
 * Cancel subscription
 * @param {string} subscriptionId - Subscription ID
 * @param {boolean} immediate - Cancel immediately vs at period end
 */
export const cancelSubscription = async (subscriptionId, immediate = false) => {
  const response = await fetch(`${API_BASE_URL}/api/billing/subscription/${subscriptionId}?immediate=${immediate}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to cancel subscription');
  }

  return response.json();
};

/**
 * Reactivate a canceled subscription
 * @param {string} subscriptionId - Subscription ID
 */
export const reactivateSubscription = async (subscriptionId) => {
  const response = await fetch(`${API_BASE_URL}/api/billing/subscription/${subscriptionId}/reactivate`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to reactivate subscription');
  }

  return response.json();
};

// ============================================================================
// Billing Tiers
// ============================================================================

/**
 * Get all available billing tiers
 */
export const getAllTiers = async () => {
  // Use organization-based endpoint
  const response = await fetch(`${API_BASE_URL}/api/billing/org/tiers`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch tiers');
  }

  return response.json();
};

/**
 * Get specific tier information
 * @param {string} tier - Tier name
 */
export const getTierInfo = async (tier) => {
  const response = await fetch(`${API_BASE_URL}/api/billing/tiers/${tier}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch tier info');
  }

  return response.json();
};

export default {
  // Usage tracking
  trackUsage,
  getMonthlyUsage,
  checkUsageLimit,

  // Subscription management
  getSubscription,
  createSubscription,
  upgradeSubscription,
  cancelSubscription,
  reactivateSubscription,

  // Tiers
  getAllTiers,
  getTierInfo
};
