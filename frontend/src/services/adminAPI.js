/**
 * Admin API Service
 * Handles admin-only operations: user management, system stats, maintenance
 */

import { API_BASE_URL } from "../config/constants";

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

// ============================================================================
// Dashboard & Statistics
// ============================================================================

/**
 * Get admin dashboard statistics
 */
export const getDashboardStats = async () => {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/dashboard/stats`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch dashboard stats");
  }

  return response.json();
};

/**
 * Get database statistics
 */
export const getDatabaseStats = async () => {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/stats/database`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch database stats");
  }

  return response.json();
};

/**
 * Get usage analytics
 * @param {number} days - Number of days to fetch (default: 30)
 */
export const getUsageAnalytics = async (days = 30) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/analytics/usage?days=${days}`,
    {
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch usage analytics");
  }

  return response.json();
};

/**
 * Get system health status
 */
export const getSystemHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/system/health`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch system health");
  }

  return response.json();
};

// ============================================================================
// User Management
// ============================================================================

/**
 * List all users with pagination and filters
 * @param {number} page - Page number (default: 1)
 * @param {number} perPage - Items per page (default: 50)
 * @param {string} search - Search query
 * @param {string} role - Filter by role
 */
export const listUsers = async (
  page = 1,
  perPage = 50,
  search = null,
  role = null,
) => {
  let url = `${API_BASE_URL}/api/v1/admin/users?page=${page}&per_page=${perPage}`;

  if (search) {
    url += `&search=${encodeURIComponent(search)}`;
  }

  if (role) {
    url += `&role=${role}`;
  }

  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch users");
  }

  return response.json();
};

/**
 * Get user details
 * @param {string} userId - User ID
 */
export const getUserDetails = async (userId) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/users/${userId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch user details");
  }

  return response.json();
};

/**
 * Create a new user
 * @param {object} userData - User data
 */
export const createUser = async (userData) => {
  const orgId = localStorage.getItem("current_organization_id");
  const headers = {
    ...getAuthHeaders(),
    "X-Organization-Id": orgId,
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/admin/users/create`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create user");
  }

  return response.json();
};

/**
 * Update user role
 * @param {string} userId - User ID
 * @param {string} role - New role (admin, manager, employee)
 */
export const updateUserRole = async (userId, role) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/role`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ role }),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update user role");
  }

  return response.json();
};

/**
 * Suspend user account
 * @param {string} userId - User ID
 * @param {string} reason - Suspension reason
 */
export const suspendUser = async (userId, reason) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/suspend`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ reason }),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to suspend user");
  }

  return response.json();
};

/**
 * Activate user account
 * @param {string} userId - User ID
 */
export const activateUser = async (userId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/activate`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to activate user");
  }

  return response.json();
};

/**
 * Unlock user account
 * @param {string} userId - User ID
 */
export const unlockUser = async (userId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/unlock`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to unlock user");
  }

  return response.json();
};

/**
 * Delete user account
 * @param {string} userId - User ID
 */
export const deleteUser = async (userId) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/users/${userId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete user");
  }

  return response.json();
};

/**
 * Update user profile (username, full_name, email)
 * @param {string} userId - User ID
 * @param {object} profileData - Profile data to update
 */
export const updateUserProfile = async (userId, profileData) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/profile`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(profileData),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update user profile");
  }

  return response.json();
};

/**
 * Update user department
 * @param {string} userId - User ID
 * @param {string} departmentId - Department ID
 */
export const updateUserDepartment = async (userId, departmentId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/department`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ department_id: departmentId }),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update user department");
  }

  return response.json();
};

/**
 * Update user email
 * @param {string} userId - User ID
 * @param {string} email - New email
 */
export const updateUserEmail = async (userId, email) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/email`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ email }),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update user email");
  }

  return response.json();
};

/**
 * Get user permissions
 * @param {string} userId - User ID
 */
export const getUserPermissions = async (userId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/users/${userId}/permissions`,
    {
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch user permissions");
  }

  return response.json();
};

/**
 * Get all available permissions
 */
export const getAllPermissions = async () => {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/permissions/all`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch permissions");
  }

  return response.json();
};

// ============================================================================
// Expense Management
// ============================================================================

/**
 * Get all expenses (admin view)
 * @param {string} status - Filter by status (pending, approved, rejected, all)
 */
export const getAllExpenses = async (status = null) => {
  const url = status
    ? `${API_BASE_URL}/api/v1/admin/expenses?status=${status}`
    : `${API_BASE_URL}/api/v1/admin/expenses`;

  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch expenses");
  }

  return response.json();
};

/**
 * Get archived expenses
 */
export const getArchivedExpenses = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/expenses/archived`,
    {
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch archived expenses");
  }

  return response.json();
};

/**
 * Archive single expense
 * @param {string} expenseId - Expense ID
 */
export const archiveExpense = async (expenseId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/expenses/${expenseId}/archive`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to archive expense");
  }

  return response.json();
};

/**
 * Unarchive single expense
 * @param {string} expenseId - Expense ID
 */
export const unarchiveExpense = async (expenseId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/expenses/${expenseId}/unarchive`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to unarchive expense");
  }

  return response.json();
};

/**
 * Archive all expenses (non-pending)
 */
export const archiveAllExpenses = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/expenses/archive-all`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to archive all expenses");
  }

  return response.json();
};

/**
 * Unarchive all expenses
 */
export const unarchiveAllExpenses = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/expenses/unarchive-all`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to unarchive all expenses");
  }

  return response.json();
};

/**
 * Clear pending expenses only
 */
export const clearPendingExpenses = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/expenses-pending/clear`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to clear pending expenses");
  }

  return response.json();
};

// ============================================================================
// Maintenance
// ============================================================================

/**
 * Run all maintenance tasks
 */
export const runMaintenance = async () => {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/maintenance`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to run maintenance");
  }

  return response.json();
};

/**
 * Cleanup audit logs
 */
export const cleanupAuditLogs = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/maintenance/audit-logs`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to cleanup audit logs");
  }

  return response.json();
};

/**
 * Cleanup old sessions
 */
export const cleanupSessions = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/maintenance/sessions`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to cleanup sessions");
  }

  return response.json();
};

/**
 * Cleanup expired tokens
 */
export const cleanupTokens = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/maintenance/tokens`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to cleanup tokens");
  }

  return response.json();
};

export default {
  // Dashboard & stats
  getDashboardStats,
  getDatabaseStats,
  getUsageAnalytics,
  getSystemHealth,

  // User management
  listUsers,
  getUserDetails,
  createUser,
  updateUserRole,
  suspendUser,
  activateUser,
  unlockUser,
  deleteUser,
  updateUserProfile,
  updateUserDepartment,
  updateUserEmail,
  getUserPermissions,
  getAllPermissions,

  // Expense management
  getAllExpenses,
  getArchivedExpenses,
  archiveExpense,
  unarchiveExpense,
  archiveAllExpenses,
  unarchiveAllExpenses,
  clearPendingExpenses,

  // Maintenance
  runMaintenance,
  cleanupAuditLogs,
  cleanupSessions,
  cleanupTokens,
};
