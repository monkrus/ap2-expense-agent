import React, { useState, useEffect } from "react";
import {
  Users,
  UserPlus,
  Edit,
  Trash2,
  Shield,
  Lock,
  Unlock,
  Search,
  Filter,
  RefreshCw,
  Eye,
  Check,
  X,
  AlertCircle,
  EyeOff,
  UserCheck,
  UserX,
} from "lucide-react";
import { useToast } from "../hooks/useToast";
import { useAuth } from "../contexts/AuthContext";
import adminAPI from "../services/adminAPI";

const UserManagementDashboard = () => {
  const { user: currentUser, getAuthHeaders, fetchWithAuth } = useAuth();
  const { success, error: showError } = useToast();

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showPermissionsModal, setShowPermissionsModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userPermissions, setUserPermissions] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [showCreatePassword, setShowCreatePassword] = useState(false);

  // Form states
  const [createForm, setCreateForm] = useState({
    email: "",
    username: "",
    full_name: "",
    password: "",
    role: "EMPLOYEE",
    department_id: "",
  });

  const [editForm, setEditForm] = useState({
    username: "",
    full_name: "",
    email: "",
    role: "",
    department_id: "",
    is_active: true,
  });

  useEffect(() => {
    // Debounce search to avoid too many API calls while typing
    const timer = setTimeout(() => {
      fetchUsers();
    }, 300); // 300ms delay

    return () => clearTimeout(timer);
  }, [searchTerm, roleFilter]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await adminAPI.listUsers(
        1, // page
        100, // per page
        searchTerm || null,
        roleFilter !== "all" ? roleFilter.toLowerCase() : null,
      );
      setUsers(data.users || []);
    } catch (err) {
      console.error("Error fetching users:", err);
      showError("Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setProcessing(true);

    try {
      const data = await adminAPI.createUser({
        ...createForm,
        role: createForm.role.toLowerCase(),
        department_id: createForm.department_id || null,
      });
      success(`User ${data.username} created successfully!`);
      setShowCreateModal(false);
      setCreateForm({
        email: "",
        username: "",
        full_name: "",
        password: "",
        role: "EMPLOYEE",
        department_id: "",
      });
      fetchUsers();
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    if (!selectedUser) return;

    setProcessing(true);

    try {
      // Check if profile fields changed (username, full_name, email)
      const profileChanged =
        editForm.username !== selectedUser.username ||
        editForm.full_name !== selectedUser.full_name ||
        editForm.email !== selectedUser.email;

      // Update profile (username, full_name, email) using new consolidated endpoint
      if (profileChanged) {
        const profileData = {};
        if (editForm.username !== selectedUser.username) {
          profileData.username = editForm.username;
        }
        if (editForm.full_name !== selectedUser.full_name) {
          profileData.full_name = editForm.full_name;
        }
        if (editForm.email !== selectedUser.email) {
          profileData.email = editForm.email;
        }

        const profileResponse = await fetchWithAuth(
          `${API_BASE_URL}/api/v1/admin/users/${selectedUser.id}/profile`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(profileData),
          },
        );

        if (!profileResponse.ok) {
          const errorData = await profileResponse.json().catch(() => ({}));
          const errorMessage =
            errorData.detail ||
            errorData.message ||
            `Failed to update profile (${profileResponse.status})`;
          throw new Error(errorMessage);
        }
      }

      // Update role (convert to lowercase for backend)
      const roleResponse = await fetchWithAuth(
        `${API_BASE_URL}/api/v1/admin/users/${selectedUser.id}/role`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ role: editForm.role.toLowerCase() }),
        },
      );

      if (!roleResponse.ok) {
        const errorData = await roleResponse.json().catch(() => ({}));
        const errorMessage =
          errorData.detail ||
          errorData.message ||
          `Failed to update role (${roleResponse.status})`;
        throw new Error(errorMessage);
      }

      // Update department
      const deptResponse = await fetchWithAuth(
        `${API_BASE_URL}/api/v1/admin/users/${selectedUser.id}/department`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            department_id: editForm.department_id || null,
          }),
        },
      );

      if (!deptResponse.ok) {
        throw new Error("Failed to update department");
      }

      // Update active status if changed
      if (editForm.is_active !== selectedUser.is_active) {
        const endpoint = editForm.is_active ? "activate" : "suspend";
        const action = editForm.is_active ? "activated" : "suspended";

        const statusResponse = await fetchWithAuth(
          `${API_BASE_URL}/api/v1/admin/users/${selectedUser.id}/${endpoint}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body:
              endpoint === "suspend"
                ? JSON.stringify({ reason: "Admin action" })
                : undefined,
          },
        );

        if (!statusResponse.ok) {
          throw new Error(`Failed to ${endpoint} user`);
        }

        // Show specific success message for status change
        success(
          `User ${editForm.username} has been ${action}. ${endpoint === "suspend" ? "They will be logged out immediately and cannot log in until reactivated." : "They can now log in and access the system."}`,
        );
      } else {
        // Show generic success for other updates
        success(`User ${editForm.username} updated successfully!`);
      }

      setShowEditModal(false);
      setSelectedUser(null);
      fetchUsers();
    } catch (err) {
      // Show more descriptive error message
      const errorMessage = err.message || "Failed to update user";
      showError(
        `Error updating user: ${errorMessage}. Please try again or contact support if the issue persists.`,
      );
      console.error("Error updating user:", err);
    } finally {
      setProcessing(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;

    setProcessing(true);

    try {
      const response = await fetchWithAuth(
        `${API_BASE_URL}/api/v1/admin/users/${selectedUser.id}`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to delete user");
      }

      success(`User ${selectedUser.username} deleted successfully!`);
      setShowDeleteModal(false);
      setSelectedUser(null);
      fetchUsers();
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const getPermissionDescription = (permission) => {
    const descriptions = {
      // Expense permissions
      "expense:submit": "Submit new expenses",
      "expense:view_own": "View own expenses",
      "expense:view_department": "View department expenses",
      "expense:view_all": "View all expenses (company-wide)",
      "expense:edit_own": "Edit own pending expenses",
      "expense:edit_department": "Edit department expenses",
      "expense:edit_all": "Edit all expenses",
      "expense:delete_own": "Delete own pending expenses",
      "expense:approve_department":
        "Approve department expenses (up to $5,000)",
      "expense:approve_all": "Approve any expense (unlimited amount)",
      "expense:reject": "Reject expenses",
      "expense:bulk_approve": "Bulk approve multiple expenses",
      "expense:bulk_reject": "Bulk reject multiple expenses",
      "expense:withdraw": "Withdraw pending expenses",

      // Receipt permissions
      "receipt:upload": "Upload receipt attachments",
      "receipt:view_own": "View own receipts",
      "receipt:view_all": "View all receipts",
      "receipt:delete_own": "Delete own receipts",
      "receipt:delete_all": "Delete any receipt",
      "receipt:download": "Download receipt files",

      // Comment permissions
      "comment:add": "Add comments to expenses",
      "comment:view": "View expense comments",
      "comment:edit_own": "Edit own comments",
      "comment:delete_own": "Delete own comments",
      "comment:delete_any": "Delete any comment",

      // User permissions
      "user:view_own": "View own user profile",
      "user:view_department": "View department users",
      "user:view_all": "View all users",
      "user:create": "Create new user accounts",
      "user:edit_own": "Edit own profile",
      "user:edit_all": "Edit any user account",
      "user:delete": "Delete user accounts",
      "user:change_role": "Change user roles",
      "user:suspend": "Suspend/activate user accounts",

      // Report permissions
      "report:view_own": "View own expense reports",
      "report:view_department": "View department reports",
      "report:view_all": "View all company reports",
      "report:export": "Export reports to file",
      "report:generate": "Generate custom reports",

      // System permissions
      "system:configure": "Configure system settings",
      "system:maintenance": "Perform database maintenance",
      "system:health": "View system health status",
      "system:audit": "Access audit logs",

      // Billing permissions
      "billing:view": "View billing information",
      "billing:manage": "Manage billing and subscriptions",

      // AP2 Protocol permissions
      "ap2:create_mandate": "Create AP2 payment mandates",
      "ap2:view_mandate": "View AP2 payment mandates",
      "ap2:execute_payment": "Execute AP2 payments",
    };

    return (
      descriptions[permission] ||
      permission.replace(/:/g, ": ").replace(/_/g, " ")
    );
  };

  const handleViewPermissions = async (user) => {
    setSelectedUser(user);
    setShowPermissionsModal(true);

    try {
      const response = await fetchWithAuth(
        `${API_BASE_URL}/api/v1/admin/users/${user.id}/permissions`,
      );

      if (!response.ok) {
        throw new Error("Failed to fetch permissions");
      }

      const data = await response.json();
      setUserPermissions(data.permissions || []);
    } catch (err) {
      showError("Failed to load user permissions");
      setUserPermissions([]);
    }
  };

  const openEditModal = (user) => {
    setSelectedUser(user);
    setEditForm({
      username: user.username || "",
      full_name: user.full_name || "",
      email: user.email || "",
      role: user.role?.toUpperCase() || "EMPLOYEE",
      department_id: user.department_id || "",
      is_active: Boolean(user.is_active), // Convert to proper boolean
    });
    setShowEditModal(true);
  };

  const openDeleteModal = (user) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
  };

  // Users are already filtered by the backend based on searchTerm and roleFilter
  const filteredUsers = users;

  const getRoleBadgeColor = (role) => {
    const colors = {
      ADMIN: "bg-red-100 text-red-800",
      MANAGER: "bg-yellow-100 text-yellow-800",
      EMPLOYEE: "bg-green-100 text-green-800",
    };
    return colors[role] || "bg-gray-100 text-gray-800";
  };

  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    admins: users.filter((u) => u.role?.toLowerCase() === "admin").length,
    managers: users.filter((u) => u.role?.toLowerCase() === "manager").length,
    employees: users.filter((u) => u.role?.toLowerCase() === "employee").length,
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                <Users className="w-8 h-8 text-indigo-600" />
                User Management
              </h1>
              <p className="text-gray-600 mt-2">
                Manage user accounts, roles, and permissions
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={fetchUsers}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
              >
                <RefreshCw
                  className={`w-5 h-5 ${loading ? "animate-spin" : ""}`}
                />
                Refresh
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
              >
                <UserPlus className="w-5 h-5" />
                Create User
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-sm">Total Users</p>
            <p className="text-2xl font-bold text-indigo-600">{stats.total}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-sm">Active</p>
            <p className="text-2xl font-bold text-green-600">{stats.active}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-sm">Admins</p>
            <p className="text-2xl font-bold text-red-600">{stats.admins}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-sm">Managers</p>
            <p className="text-2xl font-bold text-yellow-600">
              {stats.managers}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-sm">Employees</p>
            <p className="text-2xl font-bold text-blue-600">
              {stats.employees}
            </p>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by name, email, or username..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div className="flex items-center gap-3">
              <Filter className="w-5 h-5 text-gray-600" />
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="min-w-[150px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="all">All Roles</option>
                <option value="ADMIN">Admin</option>
                <option value="MANAGER">Manager</option>
                <option value="EMPLOYEE">Employee</option>
              </select>
            </div>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Department
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Login
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-12 text-center">
                      <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                        <span className="ml-3 text-gray-600">
                          Loading users...
                        </span>
                      </div>
                    </td>
                  </tr>
                ) : filteredUsers.length === 0 ? (
                  <tr>
                    <td
                      colSpan="6"
                      className="px-6 py-12 text-center text-gray-500"
                    >
                      No users found
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((user) => (
                    <tr
                      key={user.id}
                      className={`hover:bg-gray-50 ${!user.is_active ? "opacity-60 bg-gray-50" : ""}`}
                    >
                      <td className="px-6 py-4">
                        <div>
                          <div className="font-medium text-gray-900">
                            {user.full_name || user.username}
                          </div>
                          <div className="text-sm text-gray-500">
                            {user.email}
                          </div>
                          <div className="text-xs text-gray-400">
                            @{user.username}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeColor(user.role)}`}
                        >
                          {user.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {user.department_id || (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {user.is_active ? (
                          <span className="inline-flex items-center gap-1 text-green-600 text-sm">
                            <Check className="w-4 h-4" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-600 text-sm">
                            <X className="w-4 h-4" />
                            Suspended
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {user.last_login
                          ? new Date(user.last_login).toLocaleDateString()
                          : "Never"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleViewPermissions(user)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="View Permissions"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => openEditModal(user)}
                            className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                            title="Edit User"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => openDeleteModal(user)}
                            disabled={user.id === currentUser?.id}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title={
                              user.id === currentUser?.id
                                ? "Can't delete yourself"
                                : "Delete User"
                            }
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create User Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                  <UserPlus className="w-6 h-6 text-indigo-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-800">
                    Create New User
                  </h3>
                  <p className="text-sm text-gray-600">
                    Add a new user to the system
                  </p>
                </div>
              </div>

              <form onSubmit={handleCreateUser} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={createForm.email}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, email: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="user@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Username *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.username}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, username: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="username"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.full_name}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        full_name: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="John Doe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Password *
                  </label>
                  <div className="relative">
                    <input
                      type={showCreatePassword ? "text" : "password"}
                      required
                      value={createForm.password}
                      onChange={(e) =>
                        setCreateForm({
                          ...createForm,
                          password: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCreatePassword(!showCreatePassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      tabIndex={-1}
                    >
                      {showCreatePassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Role *
                  </label>
                  <select
                    required
                    value={createForm.role}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, role: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    <option value="EMPLOYEE">Employee</option>
                    <option value="MANAGER">Manager</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Department (Optional)
                  </label>
                  <input
                    type="text"
                    value={createForm.department_id}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        department_id: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="sales, engineering, etc."
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    disabled={processing}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={processing}
                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium flex items-center justify-center gap-2"
                  >
                    {processing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Creating...
                      </>
                    ) : (
                      <>
                        <UserPlus className="w-4 h-4" />
                        Create User
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {showEditModal && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                  <Edit className="w-6 h-6 text-indigo-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-800">Edit User</h3>
                  <p className="text-sm text-gray-600">
                    {selectedUser.username}
                  </p>
                </div>
              </div>

              <form onSubmit={handleEditUser} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Username *
                  </label>
                  <input
                    type="text"
                    required
                    value={editForm.username}
                    onChange={(e) =>
                      setEditForm({ ...editForm, username: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="username"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={editForm.full_name}
                    onChange={(e) =>
                      setEditForm({ ...editForm, full_name: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="John Doe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={editForm.email}
                    onChange={(e) =>
                      setEditForm({ ...editForm, email: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="user@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Role
                  </label>
                  <select
                    required
                    value={editForm.role}
                    onChange={(e) =>
                      setEditForm({ ...editForm, role: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    <option value="EMPLOYEE">Employee</option>
                    <option value="MANAGER">Manager</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Department
                  </label>
                  <input
                    type="text"
                    value={editForm.department_id}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        department_id: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="sales, engineering, etc."
                  />
                </div>

                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Account Status
                  </label>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {editForm.is_active ? (
                        <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                          <Check className="w-4 h-4" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-red-100 text-red-800 rounded-full text-sm font-medium">
                          <X className="w-4 h-4" />
                          Suspended
                        </span>
                      )}
                      {selectedUser?.id === currentUser?.id && (
                        <span className="text-xs text-orange-600">
                          (Cannot modify own status)
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setEditForm({
                          ...editForm,
                          is_active: !editForm.is_active,
                        })
                      }
                      disabled={selectedUser?.id === currentUser?.id}
                      className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                        editForm.is_active ? "bg-green-600" : "bg-red-600"
                      }`}
                    >
                      <span
                        className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                          editForm.is_active ? "translate-x-8" : "translate-x-1"
                        }`}
                      />
                    </button>
                  </div>
                  {editForm.is_active !== selectedUser?.is_active && (
                    <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-xs text-yellow-800 font-medium flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        {editForm.is_active
                          ? "Activating this user will allow them to log in immediately upon saving."
                          : "Suspending this user will log them out immediately and block all access upon saving."}
                      </p>
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mt-2">
                    {editForm.is_active
                      ? "User can log in and access the system"
                      : "User account is suspended and cannot log in"}
                  </p>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedUser(null);
                    }}
                    disabled={processing}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={processing}
                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium"
                  >
                    {processing ? "Updating..." : "Update User"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteModal && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                  <AlertCircle className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-800">
                    Delete User
                  </h3>
                  <p className="text-sm text-gray-600">
                    This action cannot be undone
                  </p>
                </div>
              </div>

              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  Are you sure you want to delete{" "}
                  <span className="font-semibold">{selectedUser.username}</span>
                  ? All their data will be permanently removed from the system.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowDeleteModal(false);
                    setSelectedUser(null);
                  }}
                  disabled={processing}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteUser}
                  disabled={processing}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium flex items-center justify-center gap-2"
                >
                  {processing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      Delete User
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* View Permissions Modal */}
        {showPermissionsModal && selectedUser && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => {
              setShowPermissionsModal(false);
              setSelectedUser(null);
              setUserPermissions([]);
            }}
          >
            <div
              className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <Shield className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-800">
                      User Permissions
                    </h3>
                    <p className="text-sm text-gray-600">
                      {selectedUser.username} - {selectedUser.role}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setShowPermissionsModal(false);
                    setSelectedUser(null);
                    setUserPermissions([]);
                  }}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                  title="Close"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-4 mb-6">
                {userPermissions.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">
                    Loading permissions...
                  </p>
                ) : (
                  (() => {
                    const grouped = userPermissions.reduce((acc, perm) => {
                      const category = perm.split(":")[0];
                      if (!acc[category]) acc[category] = [];
                      acc[category].push(perm);
                      return acc;
                    }, {});

                    const categoryColors = {
                      expense: "bg-blue-50 border-blue-200",
                      receipt: "bg-green-50 border-green-200",
                      comment: "bg-purple-50 border-purple-200",
                      user: "bg-indigo-50 border-indigo-200",
                      report: "bg-yellow-50 border-yellow-200",
                      system: "bg-red-50 border-red-200",
                      billing: "bg-pink-50 border-pink-200",
                      ap2: "bg-teal-50 border-teal-200",
                    };

                    return Object.entries(grouped).map(([category, perms]) => (
                      <div
                        key={category}
                        className={`p-4 rounded-lg border ${categoryColors[category] || "bg-gray-50 border-gray-200"}`}
                      >
                        <h4 className="text-sm font-bold text-gray-800 mb-2 capitalize flex items-center gap-2">
                          <Shield className="w-4 h-4" />
                          {category} Permissions ({perms.length})
                        </h4>
                        <div className="grid grid-cols-1 gap-1">
                          {perms.map((perm, idx) => (
                            <div
                              key={idx}
                              className="flex items-start gap-2 text-xs"
                            >
                              <Check className="w-3.5 h-3.5 text-green-600 flex-shrink-0 mt-0.5" />
                              <span className="text-gray-700">
                                {getPermissionDescription(perm)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ));
                  })()
                )}
              </div>

              <button
                onClick={() => {
                  setShowPermissionsModal(false);
                  setSelectedUser(null);
                  setUserPermissions([]);
                }}
                className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserManagementDashboard;
