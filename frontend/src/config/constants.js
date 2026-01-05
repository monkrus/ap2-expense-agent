/**
 * Shared Application Constants
 * Single source of truth for configuration values
 */

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const API_VERSION = "v1";
export const API_URL = `${API_BASE_URL}/api/${API_VERSION}`;

// App Configuration
export const APP_NAME = "AP2 Expense Management Agent";
export const APP_VERSION = "1.0.0";

// Feature Flags
export const FEATURES = {
  AI_CATEGORIZATION: import.meta.env.VITE_ENABLE_AI === "true",
  OCR_SCANNING: import.meta.env.VITE_ENABLE_OCR === "true",
  AP2_PROTOCOL: import.meta.env.VITE_ENABLE_AP2 === "true",
};

// Tier Limits (CRITICAL: Must match backend billing_tiers table)
// DO NOT MODIFY - These are enforced by the billing system
export const TIER_LIMITS = {
  FREE: {
    MAX_USERS: 2,
    MAX_ORGANIZATIONS: 1,
    MAX_EXPENSES_PER_MONTH: 30,
    MAX_RECEIPT_SIZE_MB: 5,
    MAX_STORAGE_GB: 0.5,
    OCR_SCANS_PER_MONTH: 20,
    OCR_SCANS_PER_DAY: 3,
    AI_CATEGORIZATIONS_PER_MONTH: 0,
    AP2_TRANSACTIONS_PER_MONTH: 20,
    DATA_RETENTION_DAYS: 90,
    API_ACCESS: false,
    APPROVAL_WORKFLOWS: false,
    ADVANCED_ANALYTICS: false,
  },
  STARTER: {
    MAX_USERS: 10,
    MAX_ORGANIZATIONS: 3,
    MAX_EXPENSES_PER_MONTH: 100,
    MAX_RECEIPT_SIZE_MB: 10,
    MAX_STORAGE_GB: 5,
    OCR_SCANS_PER_MONTH: 100,
    OCR_SCANS_PER_DAY: 20,
    AI_CATEGORIZATIONS_PER_MONTH: 50,
    AP2_TRANSACTIONS_PER_MONTH: 100,
    DATA_RETENTION_DAYS: 365,
    API_ACCESS: false,
    APPROVAL_WORKFLOWS: true,
    ADVANCED_ANALYTICS: true,
  },
  PROFESSIONAL: {
    MAX_USERS: 50,
    MAX_ORGANIZATIONS: 10,
    MAX_EXPENSES_PER_MONTH: 500,
    MAX_RECEIPT_SIZE_MB: 10,
    MAX_STORAGE_GB: 50,
    OCR_SCANS_PER_MONTH: null, // Unlimited
    OCR_SCANS_PER_DAY: null, // Unlimited
    AI_CATEGORIZATIONS_PER_MONTH: 200,
    AP2_TRANSACTIONS_PER_MONTH: null, // Unlimited
    DATA_RETENTION_DAYS: 1095, // 3 years
    API_ACCESS: true,
    APPROVAL_WORKFLOWS: true,
    ADVANCED_ANALYTICS: true,
  },
};

// Legacy constant for backwards compatibility
export const FREE_TIER_LIMITS = TIER_LIMITS.FREE;

// API Response Status Codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  PAYMENT_REQUIRED: 402,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
};

// Validation Constants
export const VALIDATION = {
  USERNAME_MIN: 3,
  USERNAME_MAX: 50,
  PASSWORD_MIN: 8,
  PASSWORD_MAX: 128,
  EMAIL_MAX: 255,
  FULL_NAME_MAX: 100,
  ORG_NAME_MIN: 1,
  ORG_NAME_MAX: 255,
  ORG_SLUG_MIN: 3,
  ORG_SLUG_MAX: 255,
};

// Required Headers for API Calls
export const REQUIRED_HEADERS = {
  ORGANIZATION_ID: "X-Organization-Id",
  CONTENT_TYPE: "Content-Type",
  AUTHORIZATION: "Authorization",
};

export default {
  API_BASE_URL,
  API_VERSION,
  API_URL,
  APP_NAME,
  APP_VERSION,
  FEATURES,
  FREE_TIER_LIMITS,
  TIER_LIMITS,
  HTTP_STATUS,
  VALIDATION,
  REQUIRED_HEADERS,
};
