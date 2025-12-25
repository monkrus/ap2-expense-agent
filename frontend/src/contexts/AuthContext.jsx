import React, { createContext, useState, useContext, useEffect } from "react";

const AuthContext = createContext(null);

// Export AuthContext for testing
export { AuthContext };

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const normalizeUserRole = (user) => {
    if (!user) return null;
    return {
      ...user,
      role: typeof user.role === "string" ? user.role.toLowerCase() : user.role,
    };
  };

  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const storedAccessToken = localStorage.getItem("access_token");
    const storedRefreshToken = localStorage.getItem("refresh_token");
    const storedUser = localStorage.getItem("user");

    if (storedAccessToken && storedUser) {
      setAccessToken(storedAccessToken);
      setRefreshToken(storedRefreshToken);
      const parsedUser = JSON.parse(storedUser);
      setUser(normalizeUserRole(parsedUser));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!accessToken) return;

    const validateOrganization = async () => {
      try {
        const orgResponse = await fetch("/api/v1/organizations", {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
        });
        if (!orgResponse.ok) return;

        const orgs = await orgResponse.json();
        const orgList = Array.isArray(orgs) ? orgs : orgs ? [orgs] : [];
        const savedOrgId = localStorage.getItem("current_organization_id");

        if (orgList.length === 0) {
          localStorage.removeItem("current_organization_id");
          return;
        }

        if (!savedOrgId || !orgList.some((org) => org.id === savedOrgId)) {
          localStorage.setItem("current_organization_id", orgList[0].id);
        }
      } catch (orgError) {
        console.warn("Failed to validate organizations:", orgError);
      }
    };

    validateOrganization();
  }, [accessToken]);

  const login = async (username, password, totpCode = null) => {
    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password, totp_code: totpCode }),
      });

      if (!response.ok) {
        const error = await response.json();
        // Use the detail message from the backend directly
        const errorMessage = error.detail || "Login failed";
        throw new Error(errorMessage);
      }

      const data = await response.json();

      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      const normalizedUser = normalizeUserRole(data.user);
      setUser(normalizedUser);

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(normalizedUser));

      const savedOrgId = localStorage.getItem("current_organization_id");
      try {
        const orgResponse = await fetch("/api/v1/organizations", {
          headers: {
            Authorization: `Bearer ${data.access_token}`,
            "Content-Type": "application/json",
          },
        });
        if (orgResponse.ok) {
          const orgs = await orgResponse.json();
          const orgList = Array.isArray(orgs) ? orgs : orgs ? [orgs] : [];
          if (orgList.length === 0) {
            localStorage.removeItem("current_organization_id");
          } else if (!savedOrgId) {
            localStorage.setItem("current_organization_id", orgList[0].id);
          } else if (!orgList.some((org) => org.id === savedOrgId)) {
            localStorage.setItem("current_organization_id", orgList[0].id);
          }
        }
      } catch (orgError) {
        console.warn("Failed to fetch organizations after login:", orgError);
      }

      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const register = async (userData) => {
    try {
      const response = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Registration failed");
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
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setAccessToken(null);
      setRefreshToken(null);
      setUser(null);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      localStorage.removeItem("current_organization_id");
    }
  };

  const refreshAccessToken = async () => {
    try {
      const response = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        throw new Error("Token refresh failed");
      }

      const data = await response.json();
      setAccessToken(data.access_token);
      localStorage.setItem("access_token", data.access_token);

      return data.access_token;
    } catch (error) {
      logout();
      throw error;
    }
  };

  const apiRequest = async (url, options = {}) => {
    const headers = {
      ...options.headers,
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    };

    let response = await fetch(url, { ...options, headers });

    // If token expired, try to refresh
    if (response.status === 401 && refreshToken) {
      try {
        const newAccessToken = await refreshAccessToken();
        headers["Authorization"] = `Bearer ${newAccessToken}`;
        response = await fetch(url, { ...options, headers });
      } catch (error) {
        logout();
        throw error;
      }
    }

    // If account is suspended/inactive, logout and notify user
    if (response.status === 403) {
      try {
        const errorData = await response.clone().json();
        if (errorData.detail === "User account is inactive") {
          logout();
          throw new Error(
            "Your account has been suspended. Please contact your administrator.",
          );
        }
      } catch (error) {
        // If it's already our custom error, re-throw it
        if (
          error.message ===
          "Your account has been suspended. Please contact your administrator."
        ) {
          throw error;
        }
        // Otherwise, it's a different 403 error, let it pass through
      }
    }

    return response;
  };

  const getAuthHeaders = () => {
    return {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    };
  };

  // Enhanced fetch with automatic token refresh
  const fetchWithAuth = async (url, options = {}) => {
    const headers = {
      ...options.headers,
      Authorization: `Bearer ${accessToken}`,
    };

    let response = await fetch(url, { ...options, headers });

    // If token expired, try to refresh and retry
    if (response.status === 401 && refreshToken) {
      try {
        const newAccessToken = await refreshAccessToken();
        headers["Authorization"] = `Bearer ${newAccessToken}`;
        response = await fetch(url, { ...options, headers });
      } catch (error) {
        // Token refresh failed, logout user
        logout();
        throw new Error("Session expired. Please login again.");
      }
    }

    // If account is suspended/inactive, logout and notify user
    if (response.status === 403) {
      try {
        const errorData = await response.clone().json();
        if (errorData.detail === "User account is inactive") {
          logout();
          throw new Error(
            "Your account has been suspended. Please contact your administrator.",
          );
        }
      } catch (error) {
        // If it's already our custom error, re-throw it
        if (
          error.message ===
          "Your account has been suspended. Please contact your administrator."
        ) {
          throw error;
        }
        // Otherwise, it's a different 403 error, let it pass through
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
    getAuthHeaders,
    fetchWithAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
