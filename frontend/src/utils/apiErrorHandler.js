/**
 * API Error Handler Utility
 *
 * Ensures all API errors have consistent structure with status and data properties.
 * This is critical for proper error handling in components (e.g., showing upgrade modals for 402 errors).
 */

/**
 * Creates a standardized API error with status and data properties
 *
 * @param {Response} response - Fetch API response object
 * @param {Object} errorData - Parsed error JSON from response
 * @returns {Error} Error object with status and data properties
 *
 * @example
 * const response = await fetch('/api/endpoint');
 * if (!response.ok) {
 *   const errorData = await response.json();
 *   throw createAPIError(response, errorData);
 * }
 */
export function createAPIError(response, errorData) {
  // Extract the most user-friendly error message
  let message = "An error occurred";

  if (errorData.detail) {
    if (typeof errorData.detail === "string") {
      // Simple string detail
      message = errorData.detail;
    } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
      // Pydantic validation errors array
      const errors = errorData.detail.map(err => {
        const field = err.loc ? err.loc[err.loc.length - 1] : 'field';
        let msg = err.msg || 'Validation error';

        // Make validation messages more user-friendly
        if (msg.includes('at least 3 characters')) {
          msg = 'must be at least 3 characters long';
        } else if (msg.includes('string does not match regex')) {
          msg = 'can only contain lowercase letters, numbers, and hyphens';
        }

        return `${field}: ${msg}`;
      });
      message = errors.join(', ');
    } else if (typeof errorData.detail === "object") {
      // Structured detail object (e.g., 402 Payment Required)
      message =
        typeof errorData.detail.message === "string" ? errorData.detail.message :
        typeof errorData.detail.upgrade_message === "string" ? errorData.detail.upgrade_message :
        typeof errorData.detail.error === "string" ? errorData.detail.error :
        message;
    }
  } else if (errorData.message) {
    message = typeof errorData.message === "string" ? errorData.message : message;
  } else if (errorData.error) {
    message = typeof errorData.error === "string" ? errorData.error : message;
  }

  // Create error with message
  const error = new Error(message);

  // CRITICAL: Attach status and data for proper error handling
  error.status = response.status;
  error.data = errorData;

  // Add helper method to check error type
  error.is402PaymentRequired = () => error.status === 402;
  error.is401Unauthorized = () => error.status === 401;
  error.is403Forbidden = () => error.status === 403;
  error.is404NotFound = () => error.status === 404;
  error.is422ValidationError = () => error.status === 422;

  return error;
}

/**
 * Handles fetch response and throws standardized error if not ok
 *
 * @param {Response} response - Fetch API response object
 * @returns {Promise<any>} Parsed JSON response if ok
 * @throws {Error} Standardized API error with status and data
 *
 * @example
 * const data = await handleResponse(response);
 */
export async function handleResponse(response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw createAPIError(response, errorData);
  }

  return response.json();
}

/**
 * Check if error is a tier limit error (402 Payment Required)
 *
 * @param {Error} error - Error object to check
 * @returns {boolean} True if it's a 402 tier limit error
 *
 * @example
 * catch (err) {
 *   if (isTierLimitError(err)) {
 *     // Show upgrade modal
 *   }
 * }
 */
export function isTierLimitError(error) {
  return error && error.status === 402;
}

/**
 * Extract tier limit info from 402 error for upgrade modal
 *
 * @param {Error} error - 402 error object
 * @returns {Object} Tier info for upgrade modal
 *
 * @example
 * if (isTierLimitError(err)) {
 *   const tierInfo = extractTierLimitInfo(err);
 *   setUpgradeTierInfo(tierInfo);
 *   setShowUpgradePrompt(true);
 * }
 */
export function extractTierLimitInfo(error) {
  if (!isTierLimitError(error)) {
    return null;
  }

  const errorData = error.data?.detail || error.data || {};

  return {
    currentTier: errorData.current_tier || "Free",
    currentLimit: errorData.limit || 1,
    currentCount: errorData.current || 1,
    message:
      typeof errorData.message === "string"
        ? errorData.message
        : errorData.upgrade_message ||
          "You have reached your plan's limit. Upgrade to unlock more features.",
    upgradeOptions: errorData.upgrade_options || { next_tier: "Starter" },
  };
}

/**
 * VALIDATION: Ensures error has required properties for component error handling
 * This function is used in development to catch errors early.
 *
 * @param {Error} error - Error to validate
 * @throws {Error} If error is missing required properties
 */
export function validateAPIError(error) {
  if (!(error instanceof Error)) {
    throw new Error(
      "API error must be an Error instance. Use createAPIError() to create errors."
    );
  }

  if (typeof error.status !== "number") {
    console.error("Invalid API error:", error);
    throw new Error(
      `API error is missing 'status' property. Error: ${error.message}`
    );
  }

  if (!error.data) {
    console.warn(
      `API error is missing 'data' property. Status: ${error.status}, Message: ${error.message}`
    );
  }

  return true;
}

// Export all functions
export default {
  createAPIError,
  handleResponse,
  isTierLimitError,
  extractTierLimitInfo,
  validateAPIError,
};
