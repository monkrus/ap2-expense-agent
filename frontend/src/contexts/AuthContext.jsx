import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const storedAccessToken = localStorage.getItem('access_token');
    const storedRefreshToken = localStorage.getItem('refresh_token');
    const storedUser = localStorage.getItem('user');

    if (storedAccessToken && storedUser) {
      setAccessToken(storedAccessToken);
      setRefreshToken(storedRefreshToken);
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const login = async (username, password, totpCode = null) => {
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password, totp_code: totpCode }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();

      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      setUser(data.user);

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const register = async (userData) => {
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      const data = await response.json();
      return { success: true, user: data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    try {
      if (refreshToken) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
          },
          body: JSON.stringify(refreshToken),
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setAccessToken(null);
      setRefreshToken(null);
      setUser(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  };

  const refreshAccessToken = async () => {
    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      setAccessToken(data.access_token);
      localStorage.setItem('access_token', data.access_token);

      return data.access_token;
    } catch (error) {
      logout();
      throw error;
    }
  };

  const apiRequest = async (url, options = {}) => {
    const headers = {
      ...options.headers,
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    };

    let response = await fetch(url, { ...options, headers });

    // If token expired, try to refresh
    if (response.status === 401 && refreshToken) {
      try {
        const newAccessToken = await refreshAccessToken();
        headers['Authorization'] = `Bearer ${newAccessToken}`;
        response = await fetch(url, { ...options, headers });
      } catch (error) {
        logout();
        throw error;
      }
    }

    return response;
  };

  const value = {
    user,
    accessToken,
    refreshToken,
    loading,
    isAuthenticated: !!accessToken,
    login,
    register,
    logout,
    refreshAccessToken,
    apiRequest,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
