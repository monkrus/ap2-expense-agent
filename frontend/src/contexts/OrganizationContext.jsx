import React, {
  createContext,
  useState,
  useContext,
  useEffect,
  useCallback,
} from "react";
import organizationAPI from "../services/organizationAPI";

const OrganizationContext = createContext(null);

export const useOrganization = () => {
  const context = useContext(OrganizationContext);
  if (!context) {
    throw new Error(
      "useOrganization must be used within an OrganizationProvider",
    );
  }
  return context;
};

export const OrganizationProvider = ({ children }) => {
  const [organizations, setOrganizations] = useState([]);
  const [currentOrganization, setCurrentOrganization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load organizations on mount — only if authenticated
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      loadOrganizations();
    } else {
      setLoading(false);
    }
  }, []);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      setError(null);

      const orgs = await organizationAPI.listOrganizations();
      setOrganizations(orgs);

      // Set current organization from localStorage or first org
      const savedOrgId = organizationAPI.getCurrentOrganizationId();
      if (savedOrgId) {
        const savedOrg = orgs.find((o) => o.id === savedOrgId);
        if (savedOrg) {
          setCurrentOrganization(savedOrg);
        } else if (orgs.length > 0) {
          setCurrentOrganization(orgs[0]);
          organizationAPI.setCurrentOrganizationId(orgs[0].id);
        }
      } else if (orgs.length > 0) {
        setCurrentOrganization(orgs[0]);
        organizationAPI.setCurrentOrganizationId(orgs[0].id);
      }
    } catch (err) {
      console.error("Failed to load organizations:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchOrganization = (orgId) => {
    const org = organizations.find((o) => o.id === orgId);
    if (org) {
      setCurrentOrganization(org);
      organizationAPI.setCurrentOrganizationId(org.id);
      return true;
    }
    return false;
  };

  const addOrganization = (org) => {
    setOrganizations((prev) => [...prev, org]);
    setCurrentOrganization(org);
    organizationAPI.setCurrentOrganizationId(org.id);
  };

  const updateOrganizationInList = (orgId, updates) => {
    setOrganizations((prev) =>
      prev.map((org) => (org.id === orgId ? { ...org, ...updates } : org)),
    );
    if (currentOrganization?.id === orgId) {
      setCurrentOrganization((prev) => ({ ...prev, ...updates }));
    }
  };

  const removeOrganization = (orgId) => {
    setOrganizations((prev) => prev.filter((org) => org.id !== orgId));
    if (currentOrganization?.id === orgId) {
      const remaining = organizations.filter((org) => org.id !== orgId);
      if (remaining.length > 0) {
        setCurrentOrganization(remaining[0]);
        organizationAPI.setCurrentOrganizationId(remaining[0].id);
      } else {
        setCurrentOrganization(null);
        organizationAPI.setCurrentOrganizationId(null);
      }
    }
  };

  const refetchOrganizations = async () => {
    await loadOrganizations();
  };

  // Get current organization's timezone (default to UTC)
  const timezone = currentOrganization?.timezone || "UTC";
  const currency = currentOrganization?.currency || "USD";

  // Format a date using the organization's timezone
  const formatDate = useCallback(
    (dateString, options = {}) => {
      if (!dateString) return "";

      // Backend sends UTC time without 'Z', so append it if missing
      const dateStr = dateString.endsWith("Z") ? dateString : dateString + "Z";
      const date = new Date(dateStr);

      if (isNaN(date.getTime())) {
        return dateString;
      }

      const defaultOptions = {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZone: timezone,
        ...options,
      };

      try {
        return date.toLocaleString("en-US", defaultOptions);
      } catch (error) {
        // Fallback to UTC if timezone is invalid
        return date.toLocaleString("en-US", {
          ...defaultOptions,
          timeZone: "UTC",
        });
      }
    },
    [timezone],
  );

  // Format date without time
  const formatDateOnly = useCallback(
    (dateString) => {
      return formatDate(dateString, {
        hour: undefined,
        minute: undefined,
      });
    },
    [formatDate],
  );

  // Format with timezone abbreviation
  const formatDateFull = useCallback(
    (dateString) => {
      return formatDate(dateString, {
        weekday: "short",
        timeZoneName: "short",
      });
    },
    [formatDate],
  );

  const value = {
    organizations,
    currentOrganization,
    loading,
    error,
    switchOrganization,
    addOrganization,
    updateOrganizationInList,
    removeOrganization,
    refetchOrganizations,
    // Timezone helpers
    timezone,
    currency,
    formatDate,
    formatDateOnly,
    formatDateFull,
  };

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
};
