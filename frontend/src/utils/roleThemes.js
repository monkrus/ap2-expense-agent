/**
 * Role-based UI theming for clear visual differentiation
 * Each role has a distinct color scheme and visual identity
 */

export const ROLE_THEMES = {
  EMPLOYEE: {
    name: "Employee",
    icon: "👤",
    primary: "green",
    colors: {
      gradient: "from-green-50 to-emerald-100",
      primary: "green-600",
      primaryHover: "green-700",
      primaryLight: "green-100",
      primaryText: "green-800",
      accent: "emerald-500",
      badge: "bg-green-100 text-green-800",
      button: "bg-green-600 hover:bg-green-700",
      border: "border-green-600",
      iconColor: "text-green-600",
      statsCard: "bg-green-50 border-green-200",
    },
    description: "Submit and track your expenses",
  },

  MANAGER: {
    name: "Manager",
    icon: "👔",
    primary: "blue",
    colors: {
      gradient: "from-blue-50 to-cyan-100",
      primary: "blue-600",
      primaryHover: "blue-700",
      primaryLight: "blue-100",
      primaryText: "blue-800",
      accent: "cyan-500",
      badge: "bg-blue-100 text-blue-800",
      button: "bg-blue-600 hover:bg-blue-700",
      border: "border-blue-600",
      iconColor: "text-blue-600",
      statsCard: "bg-blue-50 border-blue-200",
    },
    description: "Review and approve team expenses",
  },

  ADMIN: {
    name: "Administrator",
    icon: "👑",
    primary: "purple",
    colors: {
      gradient: "from-purple-50 to-indigo-100",
      primary: "purple-600",
      primaryHover: "purple-700",
      primaryLight: "purple-100",
      primaryText: "purple-800",
      accent: "indigo-500",
      badge: "bg-purple-100 text-purple-800",
      button: "bg-purple-600 hover:bg-purple-700",
      border: "border-purple-600",
      iconColor: "text-purple-600",
      statsCard: "bg-purple-50 border-purple-200",
    },
    description: "System administration and user management",
  },
};

/**
 * Get theme configuration for a specific role
 * @param {string} role - User role (EMPLOYEE, MANAGER, ADMIN)
 * @returns {object} Theme configuration
 */
export const getRoleTheme = (role) => {
  return ROLE_THEMES[role] || ROLE_THEMES.EMPLOYEE;
};

/**
 * Generate dynamic className for role-specific styling
 * @param {string} role - User role
 * @param {string} type - Type of styling (gradient, primary, button, etc.)
 * @returns {string} Tailwind CSS class names
 */
export const getThemeClass = (role, type) => {
  const theme = getRoleTheme(role);
  return theme.colors[type] || "";
};

/**
 * Role-specific capability descriptions
 */
export const ROLE_CAPABILITIES = {
  EMPLOYEE: [
    "✅ Submit expenses",
    "✅ View and edit your own expenses",
    "✅ Upload receipts",
    "✅ Track expense status",
    "✅ Withdraw pending expenses",
  ],

  MANAGER: [
    "✅ All employee capabilities",
    "✅ Approve/reject team expenses (up to $5,000)",
    "✅ View department expenses",
    "✅ Bulk approve/reject",
    "✅ Export team reports",
  ],

  ADMIN: [
    "✅ All permissions (superuser)",
    "✅ Approve unlimited expense amounts",
    "✅ Manage user accounts",
    "✅ Assign roles and departments",
    "✅ System configuration",
  ],
};

/**
 * Get user capabilities based on role
 * @param {string} role - User role
 * @returns {array} List of capabilities
 */
export const getRoleCapabilities = (role) => {
  return ROLE_CAPABILITIES[role] || ROLE_CAPABILITIES.EMPLOYEE;
};
