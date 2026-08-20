/**
 * API Helper Functions
 *
 * Centralized error handling and response processing for API calls.
 */

import {
  API_BASE_URL,
  REQUIRED_HEADERS,
  HTTP_STATUS,
} from "../config/constants";

/**
 * Extract user data from API response (handles both nested and flat structures)
 * @param {Object} response - API response
 * @returns {Object} User data
 */
export function extractUserData(response) {
  // Correct nested structure (from backend standardization)
  if (response.user) {
    return response.user;
  }

  // Legacy flat structure (backwards compatibility)
  return {
    id: response.id,
    username: response.username,
    email: response.email,
    full_name: response.full_name,
    role: response.role,
    is_active: response.is_active,
    is_verified: response.is_verified,
    created_at: response.created_at,
    updated_at: response.updated_at,
    last_login: response.last_login,
  };
}

/**
 * Extract error message from API error response
 * @param {any} error - Error object or response
 * @returns {string} Human-readable error message
 */
export function extractErrorMessage(error) {
  // Check for standardized error response
  if (error.success === false && error.message) {
    return error.detail || error.message;
  }

  // Check for detail object
  if (error.detail) {
    if (typeof error.detail === "string") {
      return error.detail;
    }
    if (typeof error.detail === "object") {
      return error.detail.message || error.detail.detail || "An error occurred";
    }
  }

  // Fallback to message field
  if (error.message) {
    return error.message;
  }

  return "An unknown error occurred";
}

/**
 * Check if response indicates missing required header
 * @param {Object} error - Error response
 * @returns {boolean}
 */
export function isMissingHeaderError(error) {
  return (
    error && error.error === "MISSING_REQUIRED_HEADER" && error.required_header
  );
}

/**
 * Check if response is a validation error
 * @param {Object} error - Error response
 * @returns {boolean}
 */
export function isValidationError(error) {
  return error && error.error === "VALIDATION_ERROR";
}

/**
 * Get required headers for API request with organization context
 * @param {string|null} organizationId - Organization ID (optional)
 * @returns {Object} Headers object
 */
export function getApiHeaders(organizationId = null) {
  const headers = {
    [REQUIRED_HEADERS.CONTENT_TYPE]: "application/json",
  };

  // Add auth token from localStorage
  const token = localStorage.getItem("access_token");
  if (token) {
    headers[REQUIRED_HEADERS.AUTHORIZATION] = `Bearer ${token}`;
  }

  // Add organization context if provided
  if (organizationId) {
    headers[REQUIRED_HEADERS.ORGANIZATION_ID] = organizationId;
  }

  return headers;
}

/**
 * Make API request with standardized error handling
 * @param {string} endpoint - API endpoint (relative to API_BASE_URL)
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>} Response data
 * @throws {Error} With formatted error message
 */
export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getApiHeaders(),
        ...options.headers,
      },
    });

    // Parse JSON response
    const data = await response.json().catch(() => ({}));

    // Handle HTTP errors
    if (!response.ok) {
      // Check for specific error types
      if (response.status === HTTP_STATUS.UNAUTHORIZED) {
        // Clear auth and redirect to login
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
        throw new Error("Session expired. Please log in again.");
      }

      if (response.status === HTTP_STATUS.PAYMENT_REQUIRED) {
        const message = data.upgrade_message || extractErrorMessage(data);
        throw new Error(`Payment required: ${message}`);
      }

      if (response.status === HTTP_STATUS.FORBIDDEN) {
        throw new Error("You do not have permission to perform this action");
      }

      if (isMissingHeaderError(data)) {
        throw new Error(
          `Missing required header: ${data.required_header}. ${data.detail || ""}`,
        );
      }

      if (isValidationError(data)) {
        if (data.errors && Array.isArray(data.errors)) {
          const errorMessages = data.errors
            .map((e) => `${e.field}: ${e.message}`)
            .join(", ");
          throw new Error(`Validation failed: ${errorMessages}`);
        }
        throw new Error(data.message || "Validation failed");
      }

      // Generic error
      throw new Error(extractErrorMessage(data));
    }

    return data;
  } catch (error) {
    // Re-throw with formatted message
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(
      "Network error. Please check your connection and try again.",
      { cause: error },
    );
  }
}

/**
 * Validate required fields before making API request
 * @param {Object} data - Data to validate
 * @param {string[]} requiredFields - List of required field names
 * @throws {Error} If validation fails
 */
export function validateRequiredFields(data, requiredFields) {
  const missing = requiredFields.filter((field) => !data[field]);

  if (missing.length > 0) {
    throw new Error(`Missing required fields: ${missing.join(", ")}`);
  }
}
