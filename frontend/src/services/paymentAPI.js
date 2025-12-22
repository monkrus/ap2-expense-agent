/**
 * Payment API Service
 *
 * Handles Stripe payment operations:
 * - Setup intents for collecting payment methods
 * - Subscription creation
 * - Customer portal access
 * - Checkout sessions
 */

import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Create axios instance with auth header
const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add auth token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const paymentAPI = {
  /**
   * Create a setup intent for collecting payment method
   *
   * @returns {Promise<{client_secret: string, customer_id: string}>}
   */
  createSetupIntent: async () => {
    const response = await api.post("/api/payment/setup-intent");
    return response.data;
  },

  /**
   * Create a subscription with payment method
   *
   * @param {string} tierName - Tier name (starter, professional, enterprise)
   * @param {string} paymentMethodId - Stripe payment method ID
   * @returns {Promise<{success: boolean, subscription_id: string, status: string, tier: string}>}
   */
  createSubscription: async (tierName, paymentMethodId) => {
    const response = await api.post("/api/payment/subscribe", null, {
      params: {
        tier_name: tierName,
        payment_method_id: paymentMethodId,
      },
    });
    return response.data;
  },

  /**
   * Create a Stripe Checkout session
   *
   * This provides a hosted checkout page
   *
   * @param {string} tierName - Tier name (starter, professional, enterprise)
   * @param {string} billingCycle - Billing cycle ('monthly' or 'annual')
   * @returns {Promise<{session_id: string, url: string, billing_cycle: string}>}
   */
  createCheckoutSession: async (tierName, billingCycle = "monthly") => {
    const response = await api.post("/api/payment/checkout-session", null, {
      params: {
        tier_name: tierName,
        billing_cycle: billingCycle,
      },
    });
    return response.data;
  },

  /**
   * Create a Stripe Customer Portal session
   *
   * Allows customers to manage subscription, payment methods, view invoices
   *
   * @returns {Promise<{url: string}>}
   */
  createPortalSession: async () => {
    const response = await api.post("/api/payment/portal-session");
    return response.data;
  },
};

export default paymentAPI;
