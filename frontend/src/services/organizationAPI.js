/**
 * Organization API Service
 * Handles all organization-related API calls
 *
 * ⚠️ CRITICAL: All functions MUST use createAPIError for error responses
 *
 * Pattern for ALL API functions:
 * ```
 * if (!response.ok) {
 *   const errorData = await response.json();
 *   throw createAPIError(response, errorData);  // ✅ Has status & data
 * }
 * ```
 *
 * This ensures:
 * - error.status is set (for checking 402, 400, etc.)
 * - error.data contains full error info
 * - Components can show upgrade modal for 402 errors
 *
 * See: frontend/API_ERROR_HANDLING_GUIDE.md
 */

import { createAPIError } from "../utils/apiErrorHandler";
import { apiFetch } from "../utils/apiClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/**
 * Get current organization ID from localStorage
 */
export const getCurrentOrganizationId = () => {
  const orgId = localStorage.getItem("current_organization_id");
  if (!orgId || orgId === "null" || orgId === "undefined") {
    return null;
  }
  return orgId;
};

/**
 * Set current organization ID in localStorage
 */
export const setCurrentOrganizationId = (orgId) => {
  if (orgId) {
    localStorage.setItem("current_organization_id", orgId);
  } else {
    localStorage.removeItem("current_organization_id");
  }
};

// ============================================================================
// Organization CRUD
// ============================================================================

/**
 * List all organizations for current user
 */
export const listOrganizations = async () => {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/organizations`);

  if (!response.ok) {
    let errorMessage = "Failed to fetch organizations";
    try {
      const error = await response.json();
      errorMessage = error.detail || errorMessage;
    } catch {
      // Server returned non-JSON response
    }
    throw new Error(errorMessage);
  }

  return response.json();
};

/**
 * Get organization details
 */
export const getOrganization = async (orgId) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch organization");
  }

  return response.json();
};

/**
 * Check if organization name is available (real-time validation)
 */
export const checkNameAvailability = async (name) => {
  if (!name || name.trim().length === 0) {
    return { available: false, message: "Name cannot be empty" };
  }

  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/validate/name?name=${encodeURIComponent(name)}`
  );

  if (!response.ok) {
    return { available: false, message: "Failed to check availability" };
  }

  return response.json();
};

/**
 * Check if organization slug is available (real-time validation)
 */
export const checkSlugAvailability = async (slug) => {
  if (!slug || slug.trim().length === 0) {
    return { available: false, message: "Slug cannot be empty" };
  }

  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/validate/slug?slug=${encodeURIComponent(slug)}`
  );

  if (!response.ok) {
    return { available: false, message: "Failed to check availability" };
  }

  return response.json();
};

/**
 * Create new organization
 */
export const createOrganization = async (data) => {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/organizations`, {
    method: "POST",
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    // Use standardized error handler - ensures status and data properties
    throw createAPIError(response, errorData);
  }

  return response.json();
};

/**
 * Update organization
 */
export const updateOrganization = async (orgId, data) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update organization");
  }

  return response.json();
};

/**
 * Delete organization
 */
export const deleteOrganization = async (orgId) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to delete organization");
  }

  return true;
};

// ============================================================================
// Member Management
// ============================================================================

/**
 * List organization members
 */
export const listMembers = async (orgId) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/members`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch members");
  }

  return response.json();
};

/**
 * Update member role
 */
export const updateMemberRole = async (orgId, memberId, role) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/members/${memberId}/role`,
    {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update member role");
  }

  return response.json();
};

/**
 * Remove member from organization
 */
export const removeMember = async (orgId, memberId) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/members/${memberId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to remove member");
  }

  return true;
};

// ============================================================================
// Invitations
// ============================================================================

/**
 * List pending invitations
 */
export const listInvitations = async (orgId) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/invitations`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch invitations");
  }

  return response.json();
};

/**
 * Create invitation
 */
export const createInvitation = async (orgId, email, role = "employee") => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/invitations`,
    {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    // Use standardized error handler - ensures status and data properties
    throw createAPIError(response, errorData);
  }

  return response.json();
};

/**
 * Revoke invitation
 */
export const revokeInvitation = async (orgId, invitationId) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/invitations/${invitationId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to revoke invitation");
  }

  return true;
};

/**
 * Accept invitation
 */
export const acceptInvitation = async (token) => {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/organizations/invitations/${token}/accept`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || "Failed to accept invitation";
    throw new Error(message);
  }

  return response.json();
};

// ============================================================================
// Bulk Operations
// ============================================================================

/**
 * Bulk invite members
 */
export const bulkInviteMembers = async (orgId, emails, role = "employee") => {
  const results = {
    successful: [],
    failed: [],
  };

  for (const email of emails) {
    try {
      const result = await createInvitation(orgId, email.trim(), role);
      results.successful.push({ email, result });
    } catch (error) {
      // If it's a 402 Payment Required error (tier limit), throw immediately
      // This will show the upgrade modal instead of continuing with other emails
      if (error.status === 402) {
        throw error;
      }
      // For other errors, collect them in results
      results.failed.push({ email, error: error.message });
    }
  }

  return results;
};

/**
 * Bulk invite members with per-email roles
 * @param {string} orgId
 * @param {{email: string, role: string}[]} inviteList
 */
export const bulkInviteMembersWithRoles = async (orgId, inviteList) => {
  const results = {
    successful: [],
    failed: [],
  };

  for (const { email, role } of inviteList) {
    try {
      const result = await createInvitation(orgId, email.trim(), role || "employee");
      results.successful.push({ email, role, result });
    } catch (error) {
      if (error.status === 402) {
        throw error;
      }
      results.failed.push({ email, error: error.message });
    }
  }

  return results;
};

export default {
  // Organization CRUD
  listOrganizations,
  getOrganization,
  createOrganization,
  updateOrganization,
  deleteOrganization,

  // Validation
  checkNameAvailability,
  checkSlugAvailability,

  // Members
  listMembers,
  updateMemberRole,
  removeMember,

  // Invitations
  listInvitations,
  createInvitation,
  revokeInvitation,
  acceptInvitation,
  bulkInviteMembers,
  bulkInviteMembersWithRoles,

  // Helpers
  getCurrentOrganizationId,
  setCurrentOrganizationId,
};
