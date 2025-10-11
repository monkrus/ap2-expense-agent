const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

class APIError extends Error {
  constructor(message, status, data, errorCode = null) {
    super(message);
    this.name = 'APIError';
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
      return 'Your session has expired. Please log in again.';
    }
    if (this.status === 403) {
      return 'You do not have permission to perform this action.';
    }
    if (this.status === 404) {
      return 'The requested resource was not found.';
    }
    if (this.status === 409) {
      return 'This resource already exists or conflicts with an existing resource.';
    }
    if (this.status === 422) {
      return 'Please check your input and try again.';
    }
    if (this.status === 429) {
      return 'Too many requests. Please slow down and try again.';
    }
    if (this.status >= 500) {
      return 'A server error occurred. Please try again later.';
    }
    if (this.status === 0) {
      return 'Network error. Please check your internet connection.';
    }

    // Return the actual error message if available
    return this.message || 'An error occurred. Please try again.';
  }
}

const getAuthToken = () => {
  const token = localStorage.getItem('access_token');
  return token;
};

const handleResponse = async (response) => {
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');

  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    // Handle new error format from backend
    let errorMessage = 'Request failed';
    let errorCode = null;

    if (isJson && data.error) {
      // New error format: { error: { message, code, status, details } }
      errorMessage = data.error.message || errorMessage;
      errorCode = data.error.code;
    } else if (isJson) {
      // Legacy format: { detail, message }
      errorMessage = data.detail || data.message || errorMessage;
    }

    throw new APIError(errorMessage, response.status, data, errorCode);
  }

  return data;
};

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const request = async (endpoint, options = {}) => {
  const { retries = 0, retryDelay = 1000, ...fetchOptions } = options;
  const token = getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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
      lastError = error;

      // Don't retry on client errors (4xx) except 429 (rate limit)
      if (error instanceof APIError) {
        if (error.status >= 400 && error.status < 500 && error.status !== 429) {
          throw error;
        }
      }

      // Don't retry on last attempt
      if (attempt < retries) {
        // Exponential backoff
        const delay = retryDelay * Math.pow(2, attempt);
        console.log(`Request failed, retrying in ${delay}ms... (Attempt ${attempt + 1}/${retries + 1})`);
        await sleep(delay);
      }
    }
  }

  // If we got here, all retries failed
  if (lastError instanceof APIError) {
    throw lastError;
  }
  throw new APIError('Network error. Please check your connection.', 0, null);
};

// Expense API
export const expenseAPI = {
  // Submit a new expense
  submitExpense: async (expenseData) => {
    return request('/expenses', {
      method: 'POST',
      body: JSON.stringify({
        user_id: expenseData.user_id,
        amount: parseFloat(expenseData.amount),
        vendor: expenseData.vendor,
        category: expenseData.category,
        description: expenseData.description,
      }),
    });
  },

  // Approve an expense
  approveExpense: async (expenseId, approverId) => {
    return request('/expenses/approve', {
      method: 'POST',
      body: JSON.stringify({
        expense_id: expenseId,
        approver_id: approverId,
      }),
    });
  },

  // Reject an expense
  rejectExpense: async (expenseId, approverId, rejectionReason = null) => {
    return request('/expenses/reject', {
      method: 'POST',
      body: JSON.stringify({
        expense_id: expenseId,
        approver_id: approverId,
        rejection_reason: rejectionReason,
      }),
    });
  },

  // Withdraw an expense (employee only, pending expenses)
  withdrawExpense: async (expenseId) => {
    return request(`/expenses/${expenseId}/withdraw`, {
      method: 'DELETE',
    });
  },

  // Get expense report
  getExpenseReport: async (userId = null) => {
    const queryParam = userId ? `?user_id=${userId}` : '';
    return request(`/expenses/report${queryParam}`, {
      method: 'GET',
    });
  },

  // Get all pending expenses (admin only)
  getAllPendingExpenses: async () => {
    return request('/expenses/all-pending', {
      method: 'GET',
    });
  },

  // Get all expenses with optional status filter (admin only)
  getAllExpenses: async (status = null) => {
    const queryParam = status ? `?status=${status}` : '';
    return request(`/admin/expenses${queryParam}`, {
      method: 'GET',
    });
  },

  // Get audit trail
  getAuditTrail: async (transactionId) => {
    return request(`/audit/${transactionId}`, {
      method: 'GET',
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
    formData.append('username', email);
    formData.append('password', password);

    return fetch('/api/auth/login', {
      method: 'POST',
      body: formData,
    }).then(handleResponse);
  },

  register: async (userData) => {
    return request('/users/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  getCurrentUser: async () => {
    return request('/users/me', {
      method: 'GET',
    });
  },
};

export { APIError };
