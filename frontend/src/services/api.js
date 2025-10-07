const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
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
    const errorMessage = isJson ? (data.detail || data.message || 'Request failed') : 'Request failed';
    throw new APIError(errorMessage, response.status, data);
  }

  return data;
};

const request = async (endpoint, options = {}) => {
  const token = getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    return await handleResponse(response);
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError('Network error. Please check your connection.', 0, null);
  }
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

  // Get expense report
  getExpenseReport: async (userId = null) => {
    const queryParam = userId ? `?user_id=${userId}` : '';
    return request(`/expenses/report${queryParam}`, {
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
