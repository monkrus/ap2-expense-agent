const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";
let orgContextPromise = null;

class APIError extends Error {
  constructor(message, status, data, errorCode = null) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.data = data;
    this.errorCode = errorCode;

    // Extract validation errors if present
    if (data?.error?.details?.errors) {
      this.validationErrors = data.error.details.errors;
    }
  }

  // User-friendly error message
  getUserMessage() {
    // Use specific error messages for common scenarios
    if (this.status === 401) {
      return "Your session has expired. Please log in again.";
    }
    if (this.status === 403) {
      return "You do not have permission to perform this action.";
    }
    if (this.status === 404) {
      return "The requested resource was not found.";
    }
    if (this.status === 409) {
      return "This resource already exists or conflicts with an existing resource.";
    }
    if (this.status === 422) {
      return "Please check your input and try again.";
    }
    if (this.status === 429) {
      return "Too many requests. Please slow down and try again.";
    }
    if (this.status >= 500) {
      return "A server error occurred. Please try again later.";
    }
    if (this.status === 0) {
      return "Network error. Please check your internet connection.";
    }

    // Return the actual error message if available
    return this.message || "An error occurred. Please try again.";
  }
}

const getAuthToken = () => {
  const token = localStorage.getItem("access_token");
  return token;
};

const getStoredOrgId = () => {
  const orgId = localStorage.getItem("current_organization_id");
  if (!orgId || orgId === "null" || orgId === "undefined") {
    return null;
  }
  return orgId;
};

const normalizeOrganizations = (data) => {
  if (Array.isArray(data)) {
    return data;
  }
  if (data && typeof data === "object") {
    return [data];
  }
  return [];
};

const ensureOrganizationId = async (token) => {
  const existingOrgId = getStoredOrgId();
  if (existingOrgId || !token) {
    return existingOrgId;
  }
  if (!orgContextPromise) {
    orgContextPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/organizations`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!response.ok) {
          return null;
        }
        const data = await response.json();
        const orgs = normalizeOrganizations(data);
        const orgId = orgs.length > 0 ? orgs[0].id : null;
        if (orgId) {
          localStorage.setItem("current_organization_id", orgId);
        }
        return orgId;
      } catch (error) {
        console.warn("[api] Failed to auto-select organization:", error);
        return null;
      } finally {
        orgContextPromise = null;
      }
    })();
  }
  return orgContextPromise;
};

const handleResponse = async (response) => {
  const contentType = response.headers.get("content-type");
  const isJson = contentType && contentType.includes("application/json");

  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    // Handle new error format from backend
    let errorMessage = "Request failed";
    let errorCode = null;

    if (isJson && data.error) {
      // New error format: { error: { message, code, status, details } }
      errorMessage = data.error.message || errorMessage;
      errorCode = data.error.code;
      if (data.error.details?.errors?.length) {
        errorMessage = data.error.details.errors[0].message || errorMessage;
      }
    } else if (isJson) {
      if (Array.isArray(data.detail) && data.detail.length > 0) {
        const firstDetail = data.detail[0];
        errorMessage =
          firstDetail.message ||
          firstDetail.msg ||
          firstDetail.detail ||
          firstDetail.error ||
          errorMessage;
        errorCode = firstDetail.error || errorCode;
      } else if (typeof data.detail === "object" && data.detail !== null) {
        // Extract message from structured detail object
        errorMessage =
          data.detail.message ||
          data.detail.upgrade_message ||
          data.detail.detail ||
          data.detail.error ||
          errorMessage;
        errorCode = data.detail.error || errorCode;
      } else {
        // Legacy format: { detail, message } where detail is a string
        errorMessage = data.detail || data.message || errorMessage;
      }
    }

    // Handle payment/upgrade required errors (402)
    if (response.status === 402) {
      // Throw error with upgrade message for tier limit issues
      throw new APIError(
        errorMessage, // Already extracted from detail.message or detail.upgrade_message
        response.status,
        data,
        errorCode,
      );
    }

    // Handle authentication errors (401)
    if (response.status === 401) {
      // Clear auth data
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");

      // Reload page to force re-authentication
      setTimeout(() => {
        window.location.href = "/login";
      }, 100);

      // Throw a special error with a user-friendly message
      throw new APIError(
        "Your session has expired. Please log in again.",
        response.status,
        data,
        errorCode,
      );
    }

    // Check if user account is suspended/inactive (403 with specific message)
    if (
      response.status === 403 &&
      (errorMessage === "User account is inactive" ||
        errorMessage ===
          "Your account has been suspended. Please contact your administrator." ||
        errorMessage === "Inactive user")
    ) {
      // Clear auth data
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");

      // Show alert to user
      alert(
        "Your account has been suspended. Please contact your administrator.",
      );

      // Redirect to login page
      setTimeout(() => {
        window.location.href = "/";
      }, 100);

      // Throw a special error with a user-friendly message
      throw new APIError(
        "Your account has been suspended. Please contact your administrator.",
        response.status,
        data,
        errorCode,
      );
    }

    throw new APIError(errorMessage, response.status, data, errorCode);
  }

  return data;
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const request = async (endpoint, options = {}) => {
  const { retries = 0, retryDelay = 1000, ...fetchOptions } = options;
  const token = getAuthToken();
  let orgId = getStoredOrgId();
  let attemptedOrgRefresh = false;

  const headers = {
    "Content-Type": "application/json",
    ...fetchOptions.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!orgId && token) {
    orgId = await ensureOrganizationId(token);
  }
  if (orgId) {
    headers["X-Organization-Id"] = orgId;
  }

  const config = {
    ...fetchOptions,
    headers,
  };

  let lastError;

  // Retry logic for failed requests
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
      return await handleResponse(response);
    } catch (error) {
      let currentError = error;
      lastError = error;

      if (currentError instanceof APIError && token && !attemptedOrgRefresh) {
        const message = currentError.message || "";
        const needsOrgRefresh =
          (currentError.status === 403 &&
            message.includes("access to this organization")) ||
          (currentError.status === 400 &&
            message.includes("Organization context required"));
        if (needsOrgRefresh) {
          attemptedOrgRefresh = true;
          localStorage.removeItem("current_organization_id");
          orgId = await ensureOrganizationId(token);
          if (orgId) {
            headers["X-Organization-Id"] = orgId;
            config.headers = { ...headers };
            try {
              const retryResponse = await fetch(
                `${API_BASE_URL}${endpoint}`,
                config,
              );
              return await handleResponse(retryResponse);
            } catch (retryError) {
              currentError = retryError;
              lastError = retryError;
            }
          }
        }
      }

      // Don't retry on client errors (4xx) except 429 (rate limit)
      if (currentError instanceof APIError) {
        if (
          currentError.status >= 400 &&
          currentError.status < 500 &&
          currentError.status !== 429
        ) {
          throw currentError;
        }
      }

      // Don't retry on last attempt
      if (attempt < retries) {
        // Exponential backoff
        const delay = retryDelay * Math.pow(2, attempt);
        console.log(
          `Request failed, retrying in ${delay}ms... (Attempt ${attempt + 1}/${retries + 1})`,
        );
        await sleep(delay);
      }
    }
  }

  // If we got here, all retries failed
  if (lastError instanceof APIError) {
    throw lastError;
  }
  throw new APIError("Network error. Please check your connection.", 0, null);
};

// Expense API
export const expenseAPI = {
  // Submit a new expense
  submitExpense: async (expenseData) => {
    return request("/expenses", {
      method: "POST",
      body: JSON.stringify({
        user_id: expenseData.user_id,
        amount: parseFloat(expenseData.amount),
        vendor: expenseData.vendor,
        category: expenseData.category,
        description: expenseData.description,
        date: expenseData.date,
      }),
    });
  },

  // Approve an expense
  approveExpense: async (expenseId, approverId) => {
    const data = await request(`/expenses/${expenseId}/approve`, {
      method: "PUT",
    });
    return { success: true, ...data };
  },

  // Reject an expense
  rejectExpense: async (expenseId, approverId, rejectionReason = null) => {
    const data = await request(`/expenses/${expenseId}/reject`, {
      method: "PUT",
      body: JSON.stringify({
        reason: rejectionReason,
      }),
    });
    return { success: true, ...data };
  },

  // Update an expense (employee only, pending expenses)
  updateExpense: async (expenseId, expenseData) => {
    console.log("Updating expense:", expenseId, expenseData); // Debug log

    return request(`/expenses/${expenseId}`, {
      method: "PUT",
      body: JSON.stringify({
        user_id: expenseData.user_id, // Backend requires user_id
        amount: parseFloat(expenseData.amount),
        vendor: expenseData.vendor,
        category: expenseData.category,
        description: expenseData.description,
      }),
    });
  },

  // Withdraw an expense (employee only, pending expenses)
  withdrawExpense: async (expenseId) => {
    return request(`/expenses/${expenseId}`, {
      method: "DELETE",
    });
  },

  // Get expense report
  getExpenseReport: async (userId = null) => {
    const queryParam = userId ? `?user_id=${userId}` : "";
    return request(`/expenses/report${queryParam}`, {
      method: "GET",
    });
  },

  // Get all pending expenses (admin only)
  getAllPendingExpenses: async () => {
    return request("/expenses?status_filter=pending", {
      method: "GET",
    });
  },

  // Get all expenses with optional status filter (admin only)
  getAllExpenses: async (status = null) => {
    const queryParam = status ? `?status_filter=${status}` : "";
    return request(`/expenses${queryParam}`, {
      method: "GET",
    });
  },

  // Get audit trail
  getAuditTrail: async (transactionId) => {
    return request(`/audit/${transactionId}`, {
      method: "GET",
    });
  },

  // Clear all expense history (admin only) - DEPRECATED
  clearExpenseHistory: async () => {
    return request("/admin/expenses/clear", {
      method: "DELETE",
    });
  },

  // Archive all non-pending expenses (admin only)
  archiveAllExpenses: async () => {
    return request("/admin/expenses/archive-all", {
      method: "POST",
    });
  },

  // Archive a single expense (admin only)
  archiveExpense: async (expenseId) => {
    return request(`/admin/expenses/${expenseId}/archive`, {
      method: "POST",
    });
  },

  // Unarchive a single expense (admin only)
  unarchiveExpense: async (expenseId) => {
    return request(`/admin/expenses/${expenseId}/unarchive`, {
      method: "POST",
    });
  },

  // Unarchive all archived expenses (admin only)
  unarchiveAllExpenses: async () => {
    return request("/admin/expenses/unarchive-all", {
      method: "POST",
    });
  },

  // Get archived expenses (admin only)
  getArchivedExpenses: async () => {
    return request("/admin/expenses/archived", {
      method: "GET",
    });
  },

  // Get analytics dashboard data
  getAnalytics: async (days = 30) => {
    return request(`/analytics/dashboard?days=${days}`, {
      method: "GET",
    });
  },

  // Get analytics summary
  getAnalyticsSummary: async () => {
    return request("/analytics/summary", {
      method: "GET",
    });
  },
};

// Chat API (if you want to add AI chat functionality)
export const chatAPI = {
  sendMessage: async (message) => {
    // For now, this would handle local logic
    // In the future, you could add an AI chat endpoint
    return { success: true, message };
  },
};

// Auth API helpers
export const authAPI = {
  login: async (email, password) => {
    const formData = new FormData();
    formData.append("username", email);
    formData.append("password", password);

    return fetch("/api/auth/login", {
      method: "POST",
      body: formData,
    }).then(handleResponse);
  },

  register: async (userData) => {
    return request("/users/register", {
      method: "POST",
      body: JSON.stringify(userData),
    });
  },

  getCurrentUser: async () => {
    return request("/auth/me", {
      method: "GET",
    });
  },
};

export { APIError };
