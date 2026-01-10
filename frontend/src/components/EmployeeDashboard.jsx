import React, { useState, useEffect } from "react";
import {
  Receipt,
  DollarSign,
  Clock,
  CheckCircle,
  Plus,
  Key,
  Trash2,
  History,
  Filter,
  Edit2,
  Upload,
  Download,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  User,
  LogOut,
  Copy,
  Check,
  Search,
  Repeat,
  TrendingUp,
} from "lucide-react";
import { expenseAPI, APIError } from "../services/api";
import { useToast } from "../hooks/useToast";
import { useAuth } from "../contexts/AuthContext";
import ChangePassword from "./ChangePassword";
import ReceiptUpload from "./ReceiptUpload";
import ExpenseEdit from "./ExpenseEdit";
import ExpenseExport from "./ExpenseExport";
import ReceiptList from "./ReceiptList";
import RoleBadge from "./RoleBadge";
import { getRoleTheme } from "../utils/roleThemes";
import RecurringExpenses from "../pages/RecurringExpenses";
import BudgetManagement from "../pages/BudgetManagement";
import NotificationCenter from "./NotificationCenter";
import BatchReceiptUpload from "./BatchReceiptUpload";

const EmployeeDashboard = () => {
  const { user, logout } = useAuth();
  const { success, error: showError } = useToast();

  // Format currency with commas
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const [activeTab, setActiveTab] = useState("active"); // 'active', 'history', 'recurring-expenses', or 'budgets'
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showReceiptUpload, setShowReceiptUpload] = useState(false);
  const [showExpenseEdit, setShowExpenseEdit] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showReceiptList, setShowReceiptList] = useState(false);
  const [showBatchUpload, setShowBatchUpload] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all"); // for history tab
  const [searchQuery, setSearchQuery] = useState(""); // for searching expenses
  const [sortField, setSortField] = useState("date"); // 'date', 'amount', 'category'
  const [sortDirection, setSortDirection] = useState("desc"); // 'asc' or 'desc'
  const [copiedTxId, setCopiedTxId] = useState(null); // Track copied transaction ID
  const [copiedExpenseId, setCopiedExpenseId] = useState(null); // Track copied expense ID
  const [currentPage, setCurrentPage] = useState(1); // For history pagination
  const [itemsPerPage] = useState(10); // Items per page for history
  const [newExpense, setNewExpense] = useState({
    amount: "",
    category: "TRAVEL",
    vendor: "",
    description: "",
    date: "", // Will be set when form opens
  });

  // Fetch user's expenses
  useEffect(() => {
    const fetchExpenses = async (isInitialLoad = false) => {
      try {
        // Only show loading spinner on initial load
        if (isInitialLoad) {
          setLoading(true);
        }
        const report = await expenseAPI.getExpenseReport(user?.id);
        if (report.expenses && Array.isArray(report.expenses)) {
          setExpenses(report.expenses);
        }
      } catch (err) {
        console.error("Error fetching expenses:", err);
        if (err instanceof APIError && err.status === 401) {
          showError("Session expired. Please login again.");
        } else if (isInitialLoad) {
          // Only show error on initial load to avoid spam
          showError("Failed to load expenses.");
        }
      } finally {
        if (isInitialLoad) {
          setLoading(false);
        }
      }
    };

    if (user) {
      fetchExpenses(true); // Initial load with loading spinner

      // Auto-refresh every 10 seconds (silent update)
      const interval = setInterval(() => {
        fetchExpenses(false);
      }, 10000);

      // Cleanup on unmount
      return () => clearInterval(interval);
    }
  }, [user]);

  // Reset to page 1 when search, filter, or tab changes
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, searchQuery, statusFilter]);

  const handleWithdrawExpense = async (expense) => {
    if (
      !window.confirm(
        `Are you sure you want to withdraw expense ${expense.id}? This action cannot be undone.`,
      )
    ) {
      return;
    }

    try {
      const result = await expenseAPI.withdrawExpense(expense.id);

      if (result.success) {
        // Remove from list
        setExpenses((prev) => prev.filter((e) => e.id !== expense.id));
        success(`Expense withdrawn successfully`);
      }
    } catch (err) {
      const errorMsg =
        err instanceof APIError ? err.message : "Failed to withdraw expense";
      showError(errorMsg);
    }
  };

  const handleCopyTransactionId = async (transactionId) => {
    try {
      await navigator.clipboard.writeText(transactionId);
      setCopiedTxId(transactionId);
      success("Transaction ID copied to clipboard!");

      // Reset copied state after 2 seconds
      setTimeout(() => {
        setCopiedTxId(null);
      }, 2000);
    } catch (err) {
      showError("Failed to copy transaction ID");
    }
  };

  const handleCopyExpenseId = async (expenseId) => {
    try {
      await navigator.clipboard.writeText(expenseId);
      setCopiedExpenseId(expenseId);
      success("Expense ID copied to clipboard!");

      // Reset copied state after 2 seconds
      setTimeout(() => {
        setCopiedExpenseId(null);
      }, 2000);
    } catch (err) {
      showError("Failed to copy expense ID");
    }
  };

  const handleExpenseSubmit = async () => {
    if (
      !newExpense.amount ||
      !newExpense.vendor ||
      !newExpense.description ||
      !newExpense.date
    ) {
      showError("Please fill in all required fields");
      return;
    }

    const tempId = `EXP-${Date.now()}`;
    const optimisticExpense = {
      id: tempId,
      amount: parseFloat(newExpense.amount),
      category: newExpense.category,
      vendor: newExpense.vendor,
      status: "pending",
      date: newExpense.date,
      description: newExpense.description,
      _optimistic: true,
    };

    // Optimistic update
    setExpenses((prev) => [...prev, optimisticExpense]);
    setShowExpenseForm(false);

    const expenseData = {
      user_id: user?.id || "current_user",
      amount: parseFloat(newExpense.amount),
      category: newExpense.category,
      vendor: newExpense.vendor,
      description: newExpense.description,
      date: newExpense.date,
    };

    try {
      const result = await expenseAPI.submitExpense(expenseData);

      const updatedExpense = result.expense || result;
      // Update with real data from server
      setExpenses((prev) =>
        prev.map((e) =>
          e.id === tempId ? { ...updatedExpense, _optimistic: false } : e,
        ),
      );

      setNewExpense({
        amount: "",
        category: "TRAVEL",
        vendor: "",
        description: "",
        date: "",
      });

      // Show different message based on auto-approval
      if (result.auto_approved && result.auto_approved_via === "intent_mandate") {
        success("✨ Auto-approved by AI agent via Intent Mandate (AP2)!");
      } else if (result.auto_approved && result.auto_approved_via === "approval_policy") {
        success(`Auto-approved by policy: ${result.message || "Approval Policy"}`);
      } else {
        success("Expense submitted successfully! Awaiting approval.");
      }
    } catch (err) {
      // Rollback optimistic update
      setExpenses((prev) => prev.filter((e) => e.id !== tempId));

      const errorMsg =
        err instanceof APIError ? err.message : "Failed to submit expense";
      showError(errorMsg);
      setShowExpenseForm(true);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: "bg-yellow-100 text-yellow-800",
      approved: "bg-green-100 text-green-800",
      rejected: "bg-red-100 text-red-800",
      withdrawn: "bg-gray-100 text-gray-600",
    };
    return (
      <span
        className={`text-xs px-2 py-1 rounded ${styles[status] || "bg-gray-100 text-gray-800"}`}
      >
        {status.toUpperCase()}
      </span>
    );
  };

  const getAutoApprovalBadge = (expense) => {
    if (!expense.auto_approved) return null;

    if (expense.auto_approved_via === "intent_mandate") {
      return (
        <span
          className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-800 ml-2"
          title="Auto-approved by AI agent using Intent Mandate (AP2 Protocol)"
        >
          ✨ AI Agent
        </span>
      );
    } else if (expense.auto_approved_via === "approval_policy") {
      return (
        <span
          className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800 ml-2"
          title="Auto-approved by organization policy"
        >
          📋 Policy
        </span>
      );
    }

    return null;
  };

  // Sorting function
  const handleSort = (field) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // New field, default to descending
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortExpenses = (expensesList) => {
    return [...expensesList].sort((a, b) => {
      let aValue, bValue;

      switch (sortField) {
        case "date":
          aValue = new Date(a.date || a.created_at);
          bValue = new Date(b.date || b.created_at);
          break;
        case "amount":
          aValue = parseFloat(a.amount);
          bValue = parseFloat(b.amount);
          break;
        case "category":
          aValue = (a.category || "").toLowerCase();
          bValue = (b.category || "").toLowerCase();
          break;
        default:
          return 0;
      }

      if (sortDirection === "asc") {
        return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
      } else {
        return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
      }
    });
  };

  // Filter expenses based on active tab and filters
  // IMPORTANT: Use .toLowerCase() for case-insensitive comparison as a defensive safeguard.
  // Backend now returns lowercase status values ("pending", "approved", etc.) but we normalize
  // here as well to prevent future case sensitivity issues if the backend changes.
  const activeExpenses = expenses.filter((e) => e.status?.toLowerCase() === "pending");
  const historyExpenses = expenses.filter((e) => {
    // History tab should exclude pending expenses (those are in Active tab)
    if (e.status?.toLowerCase() === "pending") return false;
    if (statusFilter === "all") return true;
    return e.status?.toLowerCase() === statusFilter?.toLowerCase();
  });

  // Apply search filter
  const searchFilteredExpenses = (
    activeTab === "active" ? activeExpenses : historyExpenses
  ).filter((expense) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      expense.id?.toLowerCase().includes(query) ||
      expense.vendor?.toLowerCase().includes(query) ||
      expense.description?.toLowerCase().includes(query) ||
      expense.category?.toLowerCase().includes(query) ||
      expense.amount?.toString().includes(query) ||
      expense.status?.toLowerCase().includes(query)
    );
  });

  const sortedExpenses = sortExpenses(searchFilteredExpenses);

  // Apply pagination for tabs with potentially many items
  const paginatedTabs = ["history", "active"];
  const shouldPaginate = paginatedTabs.includes(activeTab);
  const totalPages = shouldPaginate
    ? Math.ceil(sortedExpenses.length / itemsPerPage)
    : 1;
  const currentExpenses = shouldPaginate
    ? sortedExpenses.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage,
      )
    : sortedExpenses;

  const stats = {
    total: expenses.reduce((sum, e) => sum + e.amount, 0),
    pending: expenses.filter((e) => e.status === "pending").length,
    approved: expenses.filter((e) => e.status === "approved").length,
  };

  const theme = getRoleTheme("EMPLOYEE");

  return (
    <div
      className={`min-h-screen bg-gradient-to-br ${theme.colors.gradient} p-6`}
    >
      {/* Skip to main content link for accessibility */}
      <a href="#main-content" className="skip-to-content">
        Skip to main content
      </a>
      <div className="max-w-6xl mx-auto" id="main-content">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                  <Receipt className="w-8 h-8 text-blue-600" />
                  My Expenses
                </h1>
                <RoleBadge role="EMPLOYEE" showCapabilities={true} />
              </div>
              <p className="text-gray-600">{theme.description}</p>
            </div>

            {/* User Profile Section */}
            <div className="flex items-center gap-4">
              <div className="text-right border-r border-gray-300 pr-4">
                <div className="flex items-center gap-2 justify-end">
                  <User className="w-4 h-4 text-gray-600" />
                  <p className="text-sm font-semibold text-gray-800">
                    {user?.full_name || user?.username || "User"}
                  </p>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  {user?.role
                    ? user.role.charAt(0).toUpperCase() +
                      user.role.slice(1).toLowerCase()
                    : "Employee"}
                </p>
                <p className="text-xs text-gray-600">{user?.email}</p>
              </div>
              <NotificationCenter />
              <button
                onClick={async () => {
                  await logout();
                  window.location.href = "/login";
                }}
                className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-4 border-t border-gray-200">
            <button
              onClick={() => setShowExport(true)}
              className="flex items-center gap-2 px-4 py-3 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors font-medium"
            >
              <Download className="w-5 h-5" />
              Export
            </button>
            <button
              onClick={() => setShowChangePassword(true)}
              className="flex items-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
            >
              <Key className="w-5 h-5" />
              Change Password
            </button>
            <button
              onClick={() => {
                // Set today's date when opening the form
                setNewExpense((prev) => ({
                  ...prev,
                  date: new Date().toISOString().split("T")[0],
                }));
                setShowExpenseForm(true);
              }}
              className={`flex items-center gap-2 px-6 py-3 ${theme.colors.button} text-white rounded-lg transition-colors font-medium`}
            >
              <Plus className="w-5 h-5" />
              New Expense
            </button>
            <button
              onClick={() => setShowBatchUpload(true)}
              className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
            >
              <Upload className="w-5 h-5" />
              Batch Upload
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Submitted</p>
                <p className="text-2xl font-bold text-gray-800">
                  ${formatCurrency(stats.total)}
                </p>
              </div>
              <DollarSign
                className="w-10 h-10 text-blue-600"
              />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Pending Approval</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {stats.pending}
                </p>
              </div>
              <Clock className="w-10 h-10 text-yellow-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Approved</p>
                <p className="text-2xl font-bold text-green-600">
                  {stats.approved}
                </p>
              </div>
              <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-lg mb-6">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab("active")}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === "active"
                  ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              <Clock className="w-5 h-5" />
              Active Expenses
              {stats.pending > 0 && (
                <span
                  className={`ml-2 px-2 py-1 text-xs ${theme.colors.badge} rounded-full`}
                >
                  {stats.pending}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === "history"
                  ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              <History className="w-5 h-5" />
              History
            </button>
            <button
              onClick={() => setActiveTab("recurring-expenses")}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === "recurring-expenses"
                  ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              <Repeat className="w-5 h-5" />
              Recurring
            </button>
            <button
              onClick={() => setActiveTab("budgets")}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === "budgets"
                  ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              <TrendingUp className="w-5 h-5" />
              Budgets
            </button>
          </div>
        </div>

        {/* Search and Filter */}
        {(activeTab === "active" || activeTab === "history") && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex items-center gap-3 flex-wrap">
              {/* Search Box */}
              <div className="flex items-center gap-2 flex-1 min-w-[250px]">
                <Search className="w-5 h-5 text-gray-600" />
                <input
                  type="text"
                  placeholder="Search by ID, vendor, description, category..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  aria-label="Search expenses"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="text-gray-400 hover:text-gray-600"
                    title="Clear search"
                    aria-label="Clear search"
                  >
                    ×
                  </button>
                )}
              </div>

              {/* Status Filter - Only show on History tab */}
              {activeTab === "history" && (
                <>
                  <div className="border-l border-gray-300 h-8 mx-2"></div>
                  <Filter className="w-5 h-5 text-gray-600 flex-shrink-0" />
                  <span className="text-sm font-medium text-gray-700 flex-shrink-0">
                    Status:
                  </span>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[150px] bg-white"
                  >
                    <option value="all">All Statuses</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                    <option value="withdrawn">Withdrawn</option>
                  </select>
                </>
              )}
            </div>
          </div>
        )}

        {/* Expense Form Modal */}
        {showExpenseForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-bold text-gray-800 mb-4">
                Submit New Expense
              </h2>

              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="expense-date"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Expense Date <span className="text-red-600">*</span>
                  </label>
                  <input
                    id="expense-date"
                    type="date"
                    value={newExpense.date}
                    onChange={(e) =>
                      setNewExpense({ ...newExpense, date: e.target.value })
                    }
                    max={new Date().toISOString().split("T")[0]}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label
                    htmlFor="expense-amount"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Amount ($) <span className="text-red-600">*</span>
                  </label>
                  <input
                    id="expense-amount"
                    type="number"
                    step="0.01"
                    value={newExpense.amount}
                    onChange={(e) =>
                      setNewExpense({ ...newExpense, amount: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                    required
                  />
                </div>

                <div>
                  <label
                    htmlFor="expense-category"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Category
                  </label>
                  <select
                    id="expense-category"
                    value={newExpense.category}
                    onChange={(e) =>
                      setNewExpense({ ...newExpense, category: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="TRAVEL">Travel</option>
                    <option value="MEALS">Meals</option>
                    <option value="SOFTWARE">Software</option>
                    <option value="OFFICE_SUPPLIES">Office Supplies</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="expense-vendor"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Vendor <span className="text-red-600">*</span>
                  </label>
                  <input
                    id="expense-vendor"
                    type="text"
                    value={newExpense.vendor}
                    onChange={(e) =>
                      setNewExpense({ ...newExpense, vendor: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Vendor name"
                    required
                  />
                </div>

                <div>
                  <label
                    htmlFor="expense-description"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Description <span className="text-red-600">*</span>
                  </label>
                  <textarea
                    id="expense-description"
                    value={newExpense.description}
                    onChange={(e) =>
                      setNewExpense({
                        ...newExpense,
                        description: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    rows="3"
                    placeholder="Expense description"
                    required
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowExpenseForm(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExpenseSubmit}
                  className={`flex-1 px-4 py-2 ${theme.colors.button} text-white rounded-lg disabled:opacity-50`}
                >
                  Submit
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Recurring Expenses Tab */}
        {activeTab === "recurring-expenses" && <RecurringExpenses />}

        {/* Budget Management Tab */}
        {activeTab === "budgets" && <BudgetManagement />}

        {/* Expense List */}
        {(activeTab === "active" || activeTab === "history") && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-800">
                {activeTab === "active" ? "Active Expenses" : "Expense History"}
              </h2>
              {currentExpenses.length > 0 && (
                <span className="text-sm text-gray-600">
                  {currentExpenses.length} expense
                  {currentExpenses.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>

            {/* Sort Controls */}
            {currentExpenses.length > 0 && (
              <div className="flex items-center gap-2 mb-4 pb-4 border-b">
                <span className="text-sm font-medium text-gray-700">
                  Sort by:
                </span>
                <button
                  onClick={() => handleSort("date")}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    sortField === "date"
                      ? `${theme.colors.badge}`
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Date
                  {sortField === "date" &&
                    (sortDirection === "asc" ? (
                      <ArrowUp className="w-4 h-4" />
                    ) : (
                      <ArrowDown className="w-4 h-4" />
                    ))}
                </button>
                <button
                  onClick={() => handleSort("amount")}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    sortField === "amount"
                      ? `${theme.colors.badge}`
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Amount
                  {sortField === "amount" &&
                    (sortDirection === "asc" ? (
                      <ArrowUp className="w-4 h-4" />
                    ) : (
                      <ArrowDown className="w-4 h-4" />
                    ))}
                </button>
                <button
                  onClick={() => handleSort("category")}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    sortField === "category"
                      ? `${theme.colors.badge}`
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Category
                  {sortField === "category" &&
                    (sortDirection === "asc" ? (
                      <ArrowUp className="w-4 h-4" />
                    ) : (
                      <ArrowDown className="w-4 h-4" />
                    ))}
                </button>
              </div>
            )}

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <div
                    className={`animate-spin rounded-full h-8 w-8 border-b-2 border-${theme.colors.primary} mx-auto mb-2`}
                  ></div>
                  <p className="text-gray-600 text-sm">Loading expenses...</p>
                </div>
              </div>
            ) : currentExpenses.length === 0 ? (
              <div className="text-center py-12">
                {activeTab === "active" ? (
                  <>
                    <CheckCircle className="w-16 h-16 text-green-300 mx-auto mb-4" />
                    <p className="text-gray-500 text-lg font-medium">
                      All caught up!
                    </p>
                    <p className="text-gray-600 text-sm mt-2">
                      No pending expenses at the moment.
                    </p>
                  </>
                ) : (
                  <>
                    <Receipt className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">
                      No expenses match the current filter.
                    </p>
                  </>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="text-center py-3 px-2 text-sm font-semibold text-gray-700 w-12">
                        #
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                        ID
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                        Date
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                        Category
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                        Vendor
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                        Description
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">
                        Amount
                      </th>
                      <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">
                        Status
                      </th>
                      <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentExpenses.map((expense, index) => (
                      <React.Fragment key={expense.id}>
                        <tr
                          className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${expense._optimistic ? "opacity-60" : ""}`}
                        >
                          <td className="py-3 px-2 text-center text-sm font-medium text-gray-500">
                            {(currentPage - 1) * itemsPerPage + index + 1}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleCopyExpenseId(expense.id)}
                                className="p-1 hover:bg-gray-200 rounded transition-colors flex-shrink-0"
                                title="Copy expense ID"
                              >
                                {copiedExpenseId === expense.id ? (
                                  <Check className="w-3.5 h-3.5 text-green-700" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5 text-gray-600" />
                                )}
                              </button>
                              <span
                                className="text-sm font-medium text-gray-800 truncate max-w-[120px]"
                                title={expense.id}
                              >
                                {expense.id.substring(0, 8)}...
                              </span>
                              {expense.receipt_count > 0 && (
                                <button
                                  onClick={() => {
                                    setSelectedExpense(expense);
                                    setShowReceiptList(true);
                                  }}
                                  className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-800 flex items-center gap-1 hover:bg-green-200 transition-colors cursor-pointer flex-shrink-0"
                                  title="Click to view receipt details"
                                >
                                  <Receipt className="w-3 h-3" />
                                  {expense.receipt_count}
                                </button>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-600 whitespace-nowrap">
                            {formatDate(expense.date)}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {expense.category}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {expense.vendor}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-600 max-w-[250px]">
                            <div
                              className="truncate"
                              title={expense.description}
                            >
                              {expense.description}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right text-sm font-semibold text-gray-800 whitespace-nowrap">
                            ${formatCurrency(expense.amount)}
                          </td>
                          <td className="py-3 px-4 text-center">
                            {getStatusBadge(expense.status)}
                            {getAutoApprovalBadge(expense)}
                          </td>
                          <td className="py-3 px-4">
                            {expense.status?.toLowerCase() === "pending" &&
                              !expense._optimistic && (
                                <div className="flex gap-1 justify-center">
                                  <button
                                    onClick={() => {
                                      setSelectedExpense(expense);
                                      setShowExpenseEdit(true);
                                    }}
                                    className="p-1.5 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                                    title="Edit this expense"
                                  >
                                    <Edit2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => {
                                      setSelectedExpense(expense);
                                      setShowReceiptUpload(true);
                                    }}
                                    className={`p-1.5 ${theme.colors.badge} rounded hover:bg-${theme.colors.primaryLight} transition-colors`}
                                    title="Upload receipt"
                                  >
                                    <Upload className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() =>
                                      handleWithdrawExpense(expense)
                                    }
                                    className="p-1.5 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                                    title="Withdraw this expense"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              )}
                          </td>
                        </tr>
                        {/* Transaction ID row */}
                        {expense.transaction_id && (
                          <tr className="border-b border-gray-100">
                            <td colSpan="8" className="py-2 px-4 bg-green-50">
                              <div className="flex items-center gap-2">
                                <p className="text-xs text-green-700 font-mono">
                                  <span className="font-semibold">
                                    Transaction ID:
                                  </span>{" "}
                                  {expense.transaction_id}
                                </p>
                                <button
                                  onClick={() =>
                                    handleCopyTransactionId(
                                      expense.transaction_id,
                                    )
                                  }
                                  className="p-1 hover:bg-green-100 rounded transition-colors"
                                  title="Copy transaction ID"
                                >
                                  {copiedTxId === expense.transaction_id ? (
                                    <Check className="w-3.5 h-3.5 text-green-700" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5 text-green-600" />
                                  )}
                                </button>
                              </div>
                            </td>
                          </tr>
                        )}
                        {/* Rejection reason row */}
                        {expense.status?.toLowerCase() === "rejected" &&
                          expense.rejection_reason && (
                            <tr className="border-b border-gray-100">
                              <td colSpan="8" className="py-2 px-4 bg-red-50">
                                <p className="text-xs text-red-700">
                                  <span className="font-semibold">
                                    Rejection Reason:
                                  </span>{" "}
                                  {expense.rejection_reason}
                                </p>
                              </td>
                            </tr>
                          )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination for Tabs with Many Items */}
            {shouldPaginate && totalPages > 1 && (
              <div className="mt-6 flex items-center justify-between px-4 py-3 bg-white rounded-lg shadow">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <span>
                    Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
                    {Math.min(
                      currentPage * itemsPerPage,
                      sortedExpenses.length,
                    )}{" "}
                    of {sortedExpenses.length} expenses
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      setCurrentPage((prev) => Math.max(1, prev - 1))
                    }
                    disabled={currentPage === 1}
                    className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  {[...Array(totalPages)].map((_, idx) => {
                    const pageNum = idx + 1;
                    // Show first, last, current, and adjacent pages
                    if (
                      pageNum === 1 ||
                      pageNum === totalPages ||
                      Math.abs(pageNum - currentPage) <= 1
                    ) {
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`px-3 py-1 text-sm border rounded ${
                            currentPage === pageNum
                              ? "bg-blue-600 text-white border-blue-600"
                              : "border-gray-300 hover:bg-gray-50"
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    } else if (Math.abs(pageNum - currentPage) === 2) {
                      return (
                        <span key={pageNum} className="px-2 text-gray-500">
                          ...
                        </span>
                      );
                    }
                    return null;
                  })}
                  <button
                    onClick={() =>
                      setCurrentPage((prev) => Math.min(totalPages, prev + 1))
                    }
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Change Password Modal */}
        {showChangePassword && (
          <ChangePassword
            onClose={() => setShowChangePassword(false)}
            onSuccess={() => {
              success("Password changed successfully!");
              setShowChangePassword(false);
            }}
          />
        )}

        {/* Receipt Upload Modal */}
        {showReceiptUpload && selectedExpense && (
          <ReceiptUpload
            expenseId={selectedExpense.id}
            onSuccess={async (data) => {
              success("Receipt uploaded successfully!");
              setShowReceiptUpload(false);
              setSelectedExpense(null);
              // Refresh expense data to get updated receipt count
              try {
                const report = await expenseAPI.getExpenseReport(user?.id);
                if (report.expenses && Array.isArray(report.expenses)) {
                  setExpenses(report.expenses);
                }
              } catch (err) {
                console.error("Error refreshing expenses:", err);
              }
            }}
            onCancel={() => {
              setShowReceiptUpload(false);
              setSelectedExpense(null);
            }}
          />
        )}

        {/* Expense Edit Modal */}
        {showExpenseEdit && selectedExpense && (
          <ExpenseEdit
            expense={selectedExpense}
            currentUser={user}
            onSuccess={(updatedExpense) => {
              success("Expense updated successfully!");
              setShowExpenseEdit(false);
              setSelectedExpense(null);
              // Update the expense in the list
              setExpenses((prev) =>
                prev.map((e) =>
                  e.id === updatedExpense.id ? updatedExpense : e,
                ),
              );
            }}
            onCancel={() => {
              setShowExpenseEdit(false);
              setSelectedExpense(null);
            }}
          />
        )}

        {/* Export Modal */}
        {showExport && (
          <ExpenseExport
            expenses={expenses}
            onClose={() => setShowExport(false)}
          />
        )}

        {/* Receipt List Modal */}
        {showReceiptList && selectedExpense && (
          <ReceiptList
            receipts={selectedExpense.receipts || []}
            onClose={() => {
              setShowReceiptList(false);
              setSelectedExpense(null);
            }}
          />
        )}

        {/* Batch Receipt Upload Modal */}
        {showBatchUpload && (
          <BatchReceiptUpload
            onSuccess={() => {
              setShowBatchUpload(false);
              // Refresh expenses after successful batch upload
              const fetchExpenses = async () => {
                try {
                  const report = await expenseAPI.getExpenseReport(user?.id);
                  if (report.expenses && Array.isArray(report.expenses)) {
                    setExpenses(report.expenses);
                  }
                } catch (err) {
                  console.error("Error fetching expenses:", err);
                }
              };
              fetchExpenses();
            }}
            onCancel={() => setShowBatchUpload(false)}
          />
        )}
      </div>
    </div>
  );
};

export default EmployeeDashboard;
