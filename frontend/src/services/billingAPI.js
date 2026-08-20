/**
 * Billing & Subscription API Service
 * Handles billing, usage tracking, and subscription management
 */

import { apiFetch } from "../utils/apiClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

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
  const response = await apiFetch(
    `${API_BASE_URL}/api/billing/org/usage/track`,
    {
      method: "POST",
      body: JSON.stringify({
        usage_type: usageType,
        quantity,
        metadata,
      }),
    },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to track usage");
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

  const response = await apiFetch(url);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch usage statistics");
  }

  return response.json();
};

/**
 * Check if usage limit exceeded for a specific type
 * @param {string} usageType - Usage type to check
 */
export const checkUsageLimit = async (usageType) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/billing/org/usage/check-limit/${usageType}`,
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to check usage limit");
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
  const response = await apiFetch(
    `${API_BASE_URL}/api/billing/org/subscription`,
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch subscription");
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
  const response = await apiFetch(`${API_BASE_URL}/api/billing/org/tiers`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch tiers");
  }

  return response.json();
};

/**
 * Get specific tier information
 * @param {string} tier - Tier name
 */
export const getTierInfo = async (tier) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/billing/org/tiers/${tier}`,
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch tier info");
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

  // Tiers
  getAllTiers,
  getTierInfo,
};
