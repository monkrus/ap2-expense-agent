/**
 * API Client with Automatic Token Refresh
 *
 * This utility provides a fetch wrapper that automatically refreshes
 * expired tokens when receiving 401 errors.
 *
 * Usage:
 * import { apiFetch, safeJson } from '../utils/apiClient';
 * const response = await apiFetch('/api/endpoint', { method: 'POST', body: ... });
 * const data = await safeJson(response);  // never throws on empty/invalid JSON
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/**
 * Get authentication headers
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
};

/**
 * Refresh the access token using the refresh token
 */
const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem("refresh_token");

  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    // Refresh token is invalid/expired, clear everything
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    localStorage.removeItem("current_organization_id");

    // Redirect to login
    window.location.href = "/login";
    throw new Error("Session expired. Please login again.");
  }

  const data = await response.json().catch(() => ({}));
  localStorage.setItem("access_token", data.access_token);

  return data.access_token;
};

/**
 * Enhanced fetch with automatic token refresh
 *
 * @param {string} url - API endpoint URL (can be relative or absolute)
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise<Response>} - Fetch response
 */
export const apiFetch = async (url, options = {}) => {
  // Merge auth headers with any custom headers
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  };

  // Make initial request
  let response = await fetch(url, {
    ...options,
    headers,
  });

  // If we get 401 Unauthorized, try to refresh token and retry
  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken();

    // Retry the request with new token
    const retryHeaders = {
      ...headers,
      Authorization: `Bearer ${newAccessToken}`,
    };

    response = await fetch(url, {
      ...options,
      headers: retryHeaders,
    });
  }

  // If account is suspended/inactive, clear session and redirect
  if (response.status === 403) {
    try {
      const errorData = await response.clone().json();
      if (errorData.detail === "User account is inactive") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        localStorage.removeItem("current_organization_id");

        window.location.href = "/login";
        throw new Error("Your account has been suspended. Please contact your administrator.");
      }
    } catch (error) {
      // If it's already our custom error, re-throw it
      if (error.message && error.message.includes("suspended")) {
        throw error;
      }
      // Otherwise, it's a different 403 error, let it pass through
    }
  }

  return response;
};

/**
 * Safely parse JSON from a Response. Returns fallback (default {}) if the
 * body is empty, not valid JSON, or already consumed.
 *
 * @param {Response} response - Fetch Response object
 * @param {any} fallback - Value to return on parse failure (default: {})
 * @returns {Promise<any>} Parsed JSON or fallback
 */
export const safeJson = async (response, fallback = {}) => {
  try {
    const text = await response.text();
    if (!text) return fallback;
    return JSON.parse(text);
  } catch {
    return fallback;
  }
};

export default apiFetch;
