/**
 * Organization API Service
 * Handles all organization-related API calls
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
 * Get current organization ID from localStorage
 */
export const getCurrentOrganizationId = () => {
  return localStorage.getItem("current_organization_id");
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
  const response = await fetch(`${API_BASE_URL}/api/v1/organizations`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch organizations");
  }

  return response.json();
};

/**
 * Get organization details
 */
export const getOrganization = async (orgId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}`,
    {
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
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

  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/validate/name?name=${encodeURIComponent(name)}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    },
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

  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/validate/slug?slug=${encodeURIComponent(slug)}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    },
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
  const response = await fetch(`${API_BASE_URL}/api/v1/organizations`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();

    // Handle 402 Payment Required - Free tier limit
    if (response.status === 402) {
      const errorData =
        typeof error.detail === "object"
          ? error.detail
          : { message: error.detail };
      const customError = new Error("Organization limit reached");
      customError.status = 402;
      customError.data = errorData;
      throw customError;
    }

    // Handle 400 Bad Request - Validation errors with suggestions
    if (response.status === 400 && typeof error.detail === "object") {
      const customError = new Error(
        error.detail.message || "Validation failed",
      );
      customError.status = 400;
      customError.data = error.detail;
      throw customError;
    }

    throw new Error(error.detail || "Failed to create organization");
  }

  return response.json();
};

/**
 * Update organization
 */
export const updateOrganization = async (orgId, data) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update organization");
  }

  return response.json();
};

/**
 * Delete organization
 */
export const deleteOrganization = async (orgId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
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
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/members`,
    {
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch members");
  }

  return response.json();
};

/**
 * Update member role
 */
export const updateMemberRole = async (orgId, memberId, role) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/members/${memberId}/role`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ role }),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update member role");
  }

  return response.json();
};

/**
 * Remove member from organization
 */
export const removeMember = async (orgId, memberId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/members/${memberId}`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
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
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/invitations`,
    {
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch invitations");
  }

  return response.json();
};

/**
 * Create invitation
 */
export const createInvitation = async (orgId, email, role = "member") => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/invitations`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ email, role }),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create invitation");
  }

  return response.json();
};

/**
 * Revoke invitation
 */
export const revokeInvitation = async (orgId, invitationId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/${orgId}/invitations/${invitationId}`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to revoke invitation");
  }

  return true;
};

/**
 * Accept invitation
 */
export const acceptInvitation = async (token) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/organizations/invitations/${token}/accept`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to accept invitation");
  }

  return response.json();
};

// ============================================================================
// Bulk Operations
// ============================================================================

/**
 * Bulk invite members
 */
export const bulkInviteMembers = async (orgId, emails, role = "member") => {
  const results = {
    successful: [],
    failed: [],
  };

  for (const email of emails) {
    try {
      const result = await createInvitation(orgId, email.trim(), role);
      results.successful.push({ email, result });
    } catch (error) {
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

  // Helpers
  getCurrentOrganizationId,
  setCurrentOrganizationId,
};
