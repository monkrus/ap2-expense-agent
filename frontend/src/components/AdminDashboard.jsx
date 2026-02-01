import React, { useState, useEffect, useRef } from "react";
import {
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  DollarSign,
  TrendingUp,
  Key,
  FileText,
  Filter,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  UserCog,
  LogOut,
  Copy,
  Check,
  AlertCircle,
  Plus,
  Search,
  Edit2,
  Trash2,
  Upload,
  History,
  Receipt,
  Activity,
  Database,
  CreditCard,
  Building2,
  Bot,
} from "lucide-react";
import { expenseAPI, APIError } from "../services/api";
import adminAPI from "../services/adminAPI";
import billingAPI from "../services/billingAPI";
import organizationAPI from "../services/organizationAPI";
import { useToast } from "../hooks/useToast";
import { useAuth } from "../contexts/AuthContext";
import { useOrganization } from "../contexts/OrganizationContext";
import ChangePassword from "./ChangePassword";
import UserManagementDashboard from "./UserManagementDashboard";
import RoleBadge from "./RoleBadge";
import ReceiptUpload from "./ReceiptUpload";
import ReceiptList from "./ReceiptList";
import { getRoleTheme } from "../utils/roleThemes";
import ApprovalPolicies from "./ApprovalPolicies";
import NotificationCenter from "./NotificationCenter";
import AnalyticsDashboard from "./AnalyticsDashboard";
import AIAssistant from "../pages/AIAssistant";
import { UpgradeBanner, UsageLimitWarning, SidebarUpgradeCard } from "./upsell";

const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const { formatDateOnly: formatDate } = useOrganization();
  const { success, error: showError } = useToast();

  // Format currency with commas
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const [activeTab, setActiveTab] = useState("pending"); // 'pending', 'all', 'archived', 'users', 'approval-policies' (Approval Rules), 'analytics', 'ai-assistant' (AP2 Automation)
  const [pendingExpenses, setPendingExpenses] = useState([]);
  const [allExpenses, setAllExpenses] = useState([]);
  const [archivedExpenses, setArchivedExpenses] = useState([]);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [monthlyUsage, setMonthlyUsage] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all"); // for 'all' tab
  const [searchQuery, setSearchQuery] = useState(""); // for searching expenses
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showReceiptUpload, setShowReceiptUpload] = useState(false);
  const [showReceiptList, setShowReceiptList] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [rejectingExpense, setRejectingExpense] = useState(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [sortField, setSortField] = useState(() => {
    return localStorage.getItem("adminDashboard_sortField") || "date";
  });
  const [sortDirection, setSortDirection] = useState(() => {
    return localStorage.getItem("adminDashboard_sortDirection") || "desc";
  });
  const [copiedTxId, setCopiedTxId] = useState(null); // Track copied transaction ID
  const [copiedExpenseId, setCopiedExpenseId] = useState(null); // Track copied expense ID
  const [currentPage, setCurrentPage] = useState(1); // For all expenses pagination
  const [itemsPerPage] = useState(10); // Items per page for all expenses
  const [selectedExpenses, setSelectedExpenses] = useState([]); // Track selected expenses for bulk actions
  const hasLoadedData = useRef(false); // Track if initial data load has happened
  const [orgReady, setOrgReady] = useState(false);

  useEffect(() => {
    if (!user) return;

    let cancelled = false;
    const ensureOrgContext = async () => {
      try {
        const orgs = await organizationAPI.listOrganizations();
        const orgList = Array.isArray(orgs) ? orgs : orgs ? [orgs] : [];
        const savedOrgId = organizationAPI.getCurrentOrganizationId();

        if (orgList.length === 0) {
          organizationAPI.setCurrentOrganizationId(null);
          return;
        }

        if (!savedOrgId || !orgList.some((org) => org.id === savedOrgId)) {
          organizationAPI.setCurrentOrganizationId(orgList[0].id);
        }
      } catch (err) {
        console.error("Error loading organizations:", err);
      } finally {
        if (!cancelled) {
          setOrgReady(true);
        }
      }
    };

    ensureOrgContext();

    return () => {
      cancelled = true;
    };
  }, [user]);

  // Fetch all data on initial mount
  useEffect(() => {
    // Only fetch if user is loaded and we haven't loaded data yet
    if (!user || !orgReady || hasLoadedData.current) return;

    // Fetch all data sets on initial load in parallel
    // Only the first call shows loading spinner
    const loadAllData = async () => {
      setLoading(true);
      try {
        await Promise.all([
          fetchPendingExpenses(false),
          fetchAllExpenses(false),
          user.role === "admin"
            ? fetchArchivedExpenses(false)
            : Promise.resolve(),
          user.role === "admin" ? fetchDashboardStats() : Promise.resolve(),
          // Load billing data for upsell banners
          (async () => {
            try {
              const [sub, usage] = await Promise.all([
                billingAPI.getSubscription(),
                billingAPI.getMonthlyUsage(),
              ]);
              setSubscription(sub);
              setMonthlyUsage(usage);
            } catch (err) {
              console.error("Error loading billing data:", err);
            }
          })(),
        ]);
        hasLoadedData.current = true;
      } finally {
        setLoading(false);
      }
    };

    loadAllData();
  }, [user, orgReady]); // Depend on user and org context

  // Auto-refresh the active tab's data every 10 seconds
  useEffect(() => {
    if (!orgReady) return;
    const interval = setInterval(() => {
      // Always refresh dashboard stats to keep numbers in sync
      if (user?.role === "admin") {
        fetchDashboardStats();
      }
      // Refresh active tab data
      if (activeTab === "pending") {
        fetchPendingExpenses(false);
      } else if (activeTab === "all") {
        fetchAllExpenses(false);
      } else if (activeTab === "archived") {
        fetchArchivedExpenses(false);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [activeTab, statusFilter, orgReady, user?.role]);

  // Refresh all expenses when status filter changes on 'all' tab
  useEffect(() => {
    if (activeTab === "all" && orgReady) {
      fetchAllExpenses(true);
    }
  }, [statusFilter, orgReady]);

  // Reset to page 1 and clear selections when search, filter, or tab changes
  useEffect(() => {
    setCurrentPage(1);
    setSelectedExpenses([]);
  }, [activeTab, searchQuery, statusFilter]);

  // Save sort preferences to localStorage
  useEffect(() => {
    localStorage.setItem("adminDashboard_sortField", sortField);
    localStorage.setItem("adminDashboard_sortDirection", sortDirection);
  }, [sortField, sortDirection]);

  const fetchPendingExpenses = async (isInitialLoad = false) => {
    // Don't fetch if no organization is selected
    const currentOrgId = organizationAPI.getCurrentOrganizationId();
    if (!currentOrgId) {
      setPendingExpenses([]);
      return;
    }

    try {
      // Only show loading spinner on initial load
      if (isInitialLoad) {
        setLoading(true);
      }
      const data = await expenseAPI.getAllPendingExpenses();
      // Handle both formats: {expenses: [...]} or plain [...]
      const expenses = Array.isArray(data) ? data : (data.expenses || []);
      setPendingExpenses(expenses);
    } catch (err) {
      console.error("Error fetching pending expenses:", err);
      if (err instanceof APIError && err.status === 401) {
        showError("Session expired. Please login again.");
      } else if (
        err instanceof APIError &&
        err.status === 400 &&
        err.message?.includes("Organization context required")
      ) {
        // Silently handle - user has no organization
        setPendingExpenses([]);
        return;
      } else if (
        err instanceof APIError &&
        err.status === 403 &&
        err.message?.includes("access to this organization")
      ) {
        return;
      } else if (err instanceof APIError && err.status === 403) {
        showError("You do not have permission to view all expenses.");
      } else if (isInitialLoad) {
        // Only show error on initial load
        showError("Failed to load pending expenses.");
      }
    } finally {
      if (isInitialLoad) {
        setLoading(false);
      }
    }
  };

  const fetchAllExpenses = async (isInitialLoad = false) => {
    // Don't fetch if no organization is selected
    const currentOrgId = organizationAPI.getCurrentOrganizationId();
    if (!currentOrgId) {
      setAllExpenses([]);
      return;
    }

    try {
      // Only show loading spinner on initial load
      if (isInitialLoad) {
        setLoading(true);
      }
      const filterValue = statusFilter !== "all" ? statusFilter : null;

      const data = await expenseAPI.getAllExpenses(filterValue);

      // Handle both formats: {expenses: [...]} or plain [...]
      const expenses = Array.isArray(data) ? data : (data.expenses || []);
      setAllExpenses(expenses);
    } catch (err) {
      console.error("Error fetching all expenses:", err);
      console.error("Error details:", err.message, err.status, err.data);
      if (err instanceof APIError && err.status === 401) {
        showError("Session expired. Please login again.");
      } else if (
        err instanceof APIError &&
        err.status === 400 &&
        err.message?.includes("Organization context required")
      ) {
        // Silently handle - user has no organization
        setAllExpenses([]);
        return;
      } else if (
        err instanceof APIError &&
        err.status === 403 &&
        err.message?.includes("access to this organization")
      ) {
        return;
      } else if (err instanceof APIError && err.status === 403) {
        showError("You do not have permission to view all expenses.");
      } else if (isInitialLoad) {
        // Only show error on initial load
        showError("Failed to load expenses.");
      }
      setAllExpenses([]);
    } finally {
      if (isInitialLoad) {
        setLoading(false);
      }
    }
  };

  const handleApproveExpense = async (expense) => {
    setProcessing(true);

    try {
      const result = await expenseAPI.approveExpense(
        expense.id,
        user?.id || "admin",
      );

      if (result.success) {
        // Remove from pending list
        setPendingExpenses((prev) => prev.filter((e) => e.id !== expense.id));
        success(`Expense ${expense.id} approved successfully!`);

        // Always refresh all expenses and stats to keep data in sync
        fetchAllExpenses();
        if (user?.role === "admin") {
          fetchDashboardStats();
        }
      }
    } catch (err) {
      const errorMsg =
        err instanceof APIError ? err.message : "Failed to approve expense";
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const openRejectModal = (expense) => {
    setRejectingExpense(expense);
    setRejectionReason("");
  };

  const handleRejectExpense = async () => {
    if (!rejectingExpense) return;

    setProcessing(true);

    try {
      const result = await expenseAPI.rejectExpense(
        rejectingExpense.id,
        user?.id || "admin",
        rejectionReason || null,
      );

      if (result.success) {
        // Remove from pending list
        setPendingExpenses((prev) =>
          prev.filter((e) => e.id !== rejectingExpense.id),
        );
        success(`Expense ${rejectingExpense.id} rejected.`);
        setRejectingExpense(null);
        setRejectionReason("");

        // Always refresh all expenses and stats to keep data in sync
        fetchAllExpenses();
        if (user?.role === "admin") {
          fetchDashboardStats();
        }
      }
    } catch (err) {
      const errorMsg =
        err instanceof APIError ? err.message : "Failed to reject expense";
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const fetchArchivedExpenses = async (isInitialLoad = false) => {
    // Don't fetch if no organization is selected
    const currentOrgId = organizationAPI.getCurrentOrganizationId();
    if (!currentOrgId) {
      setArchivedExpenses([]);
      return;
    }

    try {
      if (isInitialLoad) {
        setLoading(true);
      }
      const data = await expenseAPI.getArchivedExpenses();
      // Handle both formats: {expenses: [...]} or plain [...]
      const expenses = Array.isArray(data) ? data : (data.expenses || []);
      setArchivedExpenses(expenses);
    } catch (err) {
      console.error("Error fetching archived expenses:", err);
      if (err instanceof APIError && err.status === 401) {
        showError("Session expired. Please login again.");
      } else if (
        err instanceof APIError &&
        err.status === 400 &&
        err.message?.includes("Organization context required")
      ) {
        // Silently handle - user has no organization
        setArchivedExpenses([]);
        return;
      } else if (
        err instanceof APIError &&
        err.status === 403 &&
        err.message?.includes("access to this organization")
      ) {
        return;
      } else if (err instanceof APIError && err.status === 403) {
        showError("You do not have permission to view archived expenses.");
      } else if (isInitialLoad) {
        showError("Failed to load archived expenses.");
      }
    } finally {
      if (isInitialLoad) {
        setLoading(false);
      }
    }
  };

  const fetchDashboardStats = async () => {
    try {
      const stats = await adminAPI.getDashboardStats();
      setDashboardStats(stats);
    } catch (err) {
      console.error("Error fetching dashboard stats:", err);
      // Don't show error toast for stats, just log it
    }
  };

  const handleArchiveAllExpenses = async () => {
    const confirmed = window.confirm(
      "Archive all approved and rejected expenses? This will move them to the Archive tab. They can be unarchived later if needed.",
    );

    if (!confirmed) return;

    setProcessing(true);

    try {
      const result = await expenseAPI.archiveAllExpenses();

      if (result.success) {
        // Refresh both views BEFORE showing success message
        await Promise.all([
          fetchAllExpenses(false),
          fetchArchivedExpenses(false),
        ]);

        success(
          `Successfully archived ${result.statistics.expenses_archived} expense(s)!`,
        );
      }
    } catch (err) {
      const errorMsg =
        err instanceof APIError ? err.message : "Failed to archive expenses";
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const handleUnarchiveExpense = async (expenseId) => {
    setProcessing(true);

    try {
      const result = await expenseAPI.unarchiveExpense(expenseId);

      if (result.success) {
        // Refresh both views BEFORE showing success message
        await Promise.all([
          fetchAllExpenses(false),
          fetchArchivedExpenses(false),
        ]);

        success("Expense unarchived successfully!");
      }
    } catch (err) {
      const errorMsg =
        err instanceof APIError ? err.message : "Failed to unarchive expense";
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const handleArchiveSelected = async () => {
    if (selectedExpenses.length === 0) {
      showError("Please select at least one expense to archive");
      return;
    }

    const confirmed = window.confirm(
      `Archive ${selectedExpenses.length} selected expense(s)? They will be moved to the Archive tab.`,
    );

    if (!confirmed) return;

    setProcessing(true);

    try {
      // Archive each selected expense
      const promises = selectedExpenses.map((expenseId) =>
        expenseAPI.archiveExpense(expenseId),
      );

      await Promise.all(promises);

      // Refresh both views BEFORE showing success message
      await Promise.all([
        fetchAllExpenses(false),
        fetchArchivedExpenses(false),
      ]);

      // Clear selections and show success after data is refreshed
      setSelectedExpenses([]);
      success(`Successfully archived ${selectedExpenses.length} expense(s)!`);
    } catch (err) {
      const errorMsg =
        err instanceof APIError
          ? err.message
          : "Failed to archive selected expenses";
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const handleUnarchiveSelected = async () => {
    if (selectedExpenses.length === 0) {
      showError("Please select at least one expense to unarchive");
      return;
    }

    const confirmed = window.confirm(
      `Restore ${selectedExpenses.length} selected expense(s) to active?`,
    );

    if (!confirmed) return;

    setProcessing(true);

    try {
      // Unarchive each selected expense
      const promises = selectedExpenses.map((expenseId) =>
        expenseAPI.unarchiveExpense(expenseId),
      );

      await Promise.all(promises);

      // Refresh both views BEFORE showing success message
      await Promise.all([
        fetchAllExpenses(false),
        fetchArchivedExpenses(false),
      ]);

      // Switch to "All Expenses" tab to show the restored expenses
      setActiveTab("all");

      // Clear selections and show success after data is refreshed
      setSelectedExpenses([]);
      success(`Successfully restored ${selectedExpenses.length} expense(s)! Switched to "All Expenses" tab.`);
    } catch (err) {
      const errorMsg =
        err instanceof APIError
          ? err.message
          : "Failed to unarchive selected expenses";
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const handleUnarchiveAllExpenses = async () => {
    const confirmed = window.confirm(
      "Restore all archived expenses to active? This will move them back to the All Expenses tab.",
    );

    if (!confirmed) return;

    setProcessing(true);

    try {
      const result = await expenseAPI.unarchiveAllExpenses();

      if (result.success) {
        // Refresh both views BEFORE showing success message
        await Promise.all([
          fetchAllExpenses(false),
          fetchArchivedExpenses(false),
        ]);

        // Switch to "All Expenses" tab to show the restored expenses
        setActiveTab("all");

        success(
          `Successfully restored ${result.statistics.expenses_unarchived} expense(s)! Switched to "All Expenses" tab.`,
        );
      }
    } catch (err) {
      const errorMsg =
        err instanceof APIError ? err.message : "Failed to restore expenses";
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const toggleExpenseSelection = (expenseId) => {
    setSelectedExpenses((prev) => {
      if (prev.includes(expenseId)) {
        return prev.filter((id) => id !== expenseId);
      } else {
        return [...prev, expenseId];
      }
    });
  };

  const toggleSelectAll = () => {
    // Filter out pending expenses when on "all" tab (can't archive pending)
    const selectableExpenses =
      activeTab === "all"
        ? currentExpenses.filter((e) => e.status !== "pending")
        : currentExpenses;

    const selectableIds = selectableExpenses.map((e) => e.id);

    if (
      selectedExpenses.length === selectableIds.length &&
      selectableIds.length > 0
    ) {
      setSelectedExpenses([]);
    } else {
      setSelectedExpenses(selectableIds);
    }
  };

  const handleViewReceipt = (expense) => {
    setSelectedExpense(expense);
    setShowReceiptUpload(true);
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

  const normalizeStatusValue = (status) => {
    if (!status) return "";
    const normalized = status.toString().toLowerCase();
    if (normalized.startsWith("expensestatus.")) {
      return normalized.replace("expensestatus.", "");
    }
    return normalized;
  };

  const getStatusBadge = (status) => {
    const normalizedStatus = normalizeStatusValue(status);
    const styles = {
      pending: "bg-yellow-100 text-yellow-800",
      approved: "bg-green-100 text-green-800",
      rejected: "bg-red-100 text-red-800",
      withdrawn: "bg-gray-100 text-gray-600",
    };
    return (
      <span
        className={`text-xs px-2 py-1 rounded ${
          styles[normalizedStatus] || "bg-gray-100 text-gray-800"
        }`}
      >
        {normalizedStatus.toUpperCase()}
      </span>
    );
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

  const handleResetSort = () => {
    setSortField("date");
    setSortDirection("desc");
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
        case "user":
          aValue = (a.user_name || "").toLowerCase();
          bValue = (b.user_name || "").toLowerCase();
          break;
        case "status":
          // Custom order: PENDING -> APPROVED -> REJECTED -> WITHDRAWN
          const statusOrder = {
            PENDING: 0,
            APPROVED: 1,
            REJECTED: 2,
            WITHDRAWN: 3,
          };
          aValue = statusOrder[a.status?.toUpperCase()] ?? 999;
          bValue = statusOrder[b.status?.toUpperCase()] ?? 999;
          break;
        case "vendor":
          aValue = (a.vendor || "").toLowerCase();
          bValue = (b.vendor || "").toLowerCase();
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

  const pendingStats = {
    total: pendingExpenses.length,
    totalAmount: pendingExpenses.reduce((sum, e) => sum + e.amount, 0),
    uniqueUsers: new Set(pendingExpenses.map((e) => e.user_id)).size,
  };

  // Stats for all expenses tab - use case-insensitive comparison
  const allExpensesStats = {
    total: allExpenses.length,
    totalAmount: allExpenses.reduce((sum, e) => sum + (e.amount || 0), 0),
    pending: allExpenses.filter((e) => e.status?.toLowerCase() === "pending").length,
    approved: allExpenses.filter((e) => e.status?.toLowerCase() === "approved").length,
    rejected: allExpenses.filter((e) => e.status?.toLowerCase() === "rejected").length,
    pendingAmount: allExpenses
      .filter((e) => e.status?.toLowerCase() === "pending")
      .reduce((sum, e) => sum + (e.amount || 0), 0),
    approvedAmount: allExpenses
      .filter((e) => e.status?.toLowerCase() === "approved")
      .reduce((sum, e) => sum + (e.amount || 0), 0),
  };

  // Apply search filter
  const getCurrentExpenseList = () => {
    if (activeTab === "pending") return pendingExpenses;
    if (activeTab === "archived") return archivedExpenses;
    return allExpenses;
  };

  const searchFilteredExpenses = getCurrentExpenseList().filter((expense) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      expense.id?.toLowerCase().includes(query) ||
      expense.vendor?.toLowerCase().includes(query) ||
      expense.description?.toLowerCase().includes(query) ||
      expense.category?.toLowerCase().includes(query) ||
      expense.amount?.toString().includes(query) ||
      expense.status?.toLowerCase().includes(query) ||
      expense.user_email?.toLowerCase().includes(query) ||
      expense.user_name?.toLowerCase().includes(query)
    );
  });

  const sortedExpenses = sortExpenses(searchFilteredExpenses);

  // Apply pagination for tabs with potentially many items
  const paginatedTabs = ["all", "pending", "approved", "rejected"];
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

  const theme = getRoleTheme(user?.role?.toUpperCase() || "ADMIN");

  // Helper function to get proper tab border/text color classes based on role
  const getTabActiveClasses = () => {
    const roleUpper = user?.role?.toUpperCase() || "ADMIN";
    switch (roleUpper) {
      case "MANAGER":
        return "border-b-2 border-blue-600 text-blue-600";
      case "ADMIN":
        return "border-b-2 border-purple-600 text-purple-600";
      default:
        return "border-b-2 border-blue-600 text-blue-600";
    }
  };

  // Helper function to get background gradient based on role
  const getBackgroundGradient = () => {
    const roleUpper = user?.role?.toUpperCase() || "ADMIN";
    switch (roleUpper) {
      case "MANAGER":
        return "from-blue-50 to-cyan-100";
      case "ADMIN":
        return "from-purple-50 to-indigo-100";
      default:
        return "from-blue-50 to-indigo-100";
    }
  };

  // Helper function to get spinner color based on role
  const getSpinnerClasses = () => {
    const roleUpper = user?.role?.toUpperCase() || "ADMIN";
    switch (roleUpper) {
      case "MANAGER":
        return "border-blue-600";
      case "ADMIN":
        return "border-purple-600";
      default:
        return "border-blue-600";
    }
  };

  // Helper function to get text color based on role
  const getTextColor = () => {
    const roleUpper = user?.role?.toUpperCase() || "ADMIN";
    switch (roleUpper) {
      case "MANAGER":
        return "text-blue-600";
      case "ADMIN":
        return "text-purple-600";
      default:
        return "text-blue-600";
    }
  };

  // Debug logging (can be removed in production)
  // Determine if user is on free/starter plan for upsells
  const isFreePlan =
    !subscription || subscription?.tier?.toLowerCase() === "free";
  const isStarterPlan = subscription?.tier?.toLowerCase() === "starter";
  const showUpsells = isFreePlan || isStarterPlan;

  const usageLimitKeyMap = {
    ai_categorization: "max_ai_categorizations",
    ap2_transaction: "max_ap2_transactions",
    ocr_scan: "ocr_scans_included",
    expense: "max_expenses_per_month",
    active_users: "max_users",
  };

  const resolveUsageLimit = (usageKey, usageEntry) => {
    if (
      usageEntry &&
      usageEntry.limit !== null &&
      usageEntry.limit !== undefined
    ) {
      return usageEntry.limit;
    }
    const limitKey = usageLimitKeyMap[usageKey] || `max_${usageKey}`;
    return subscription?.limits?.[limitKey] ?? null;
  };

  const getUsageQuantity = (usageEntry) => {
    if (!usageEntry) return 0;
    if (typeof usageEntry === "number") return usageEntry;
    return usageEntry.quantity || 0;
  };

  // Calculate usage percentages for upsell warnings
  const getUsagePercent = (usageKey) => {
    const usageEntry = monthlyUsage?.usage?.[usageKey];
    if (!usageEntry) return 0;
    const usage = getUsageQuantity(usageEntry);
    const limitValue = resolveUsageLimit(usageKey, usageEntry);
    if (limitValue === null || limitValue === undefined) return 0;
    const limit =
      typeof limitValue === "string" ? Number(limitValue) : limitValue;
    if (!Number.isFinite(limit)) return 0;
    if (limit === 0) return usage > 0 ? 100 : 0;
    return Math.round((usage / limit) * 100);
  };

  const aiUsagePercent = getUsagePercent("ai_categorization");
  const expenseUsagePercent = getUsagePercent("expense");

  return (
    <div
      className={`min-h-screen bg-gradient-to-br ${getBackgroundGradient()}`}
    >
      {/* Upsell Banner - Show for free/starter users */}
      {showUpsells && (
        <UpgradeBanner
          variant={
            isFreePlan ? "upgrade" : aiUsagePercent >= 80 ? "limit" : "upgrade"
          }
          usagePercent={aiUsagePercent >= 80 ? aiUsagePercent : null}
          feature={aiUsagePercent >= 80 ? "AI categorizations" : null}
        />
      )}

      <div className="p-6">
        <div className="max-w-7xl mx-auto">
          {/* Usage Warnings */}
          {showUpsells && monthlyUsage && (
            <div className="mb-4 space-y-3">
              {aiUsagePercent >= 70 && (
                <UsageLimitWarning
                  feature="AI categorizations"
                  currentUsage={
                    monthlyUsage.usage?.ai_categorization?.quantity || 0
                  }
                  limit={
                    (monthlyUsage?.usage?.ai_categorization?.limit ??
                      subscription?.limits?.max_ai_categorizations) ||
                    100
                  }
                />
              )}
              {expenseUsagePercent >= 70 && (
                <UsageLimitWarning
                  feature="expenses"
                  currentUsage={monthlyUsage.usage?.expense?.quantity || 0}
                  limit={
                    (monthlyUsage?.usage?.expense?.limit ??
                      subscription?.limits?.max_expenses_per_month) ||
                    500
                  }
                />
              )}
            </div>
          )}

          {/* Header */}
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            {/* Title Row */}
            <div className="mb-4">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                  <Shield className="w-8 h-8 text-blue-600" />
                  {user?.role === "manager"
                    ? "Manager Dashboard"
                    : user?.role === "accountant"
                      ? "Accountant Dashboard"
                      : "Admin Dashboard"}
                </h1>
                <RoleBadge
                  role={user?.role?.toUpperCase() || "ADMIN"}
                  showCapabilities={true}
                />
              </div>
              <p className="text-gray-600">{theme.description}</p>
            </div>

            {/* Actions Row */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              {/* Left side - Feature actions */}
              <div className="flex flex-wrap items-center gap-2">
                {user?.role === "admin" && (
                  <button
                    onClick={() => (window.location.href = "/organizations")}
                    title="Manage Organizations"
                    className="flex items-center gap-2 px-3 py-2 bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 transition-colors font-medium text-sm whitespace-nowrap"
                  >
                    <Building2 className="w-4 h-4" />
                    Organizations
                  </button>
                )}
                <button
                  onClick={() => (window.location.href = "/billing")}
                  title="View Billing Dashboard"
                  className="flex items-center gap-2 px-3 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors font-medium text-sm whitespace-nowrap"
                >
                  <CreditCard className="w-4 h-4" />
                  Billing
                </button>
                <button
                  onClick={() => setShowChangePassword(true)}
                  title="Change Password"
                  className="flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors font-medium text-sm whitespace-nowrap"
                >
                  <Key className="w-4 h-4" />
                  Change Password
                </button>
              </div>

              {/* Right side - System actions */}
              <div className="flex items-center gap-2">
                <NotificationCenter />
                <button
                  onClick={async () => {
                    await logout();
                    window.location.reload();
                  }}
                  title="Logout"
                  className="flex items-center gap-2 px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors font-medium text-sm whitespace-nowrap"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="bg-white rounded-lg shadow-lg mb-6">
            <div className="flex border-b border-gray-200">
              <button
                onClick={() => setActiveTab("pending")}
                className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                  activeTab === "pending"
                    ? getTabActiveClasses()
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                <Clock className="w-5 h-5" />
                Pending Approvals
                {pendingStats.total > 0 && (
                  <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                    {pendingStats.total}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab("all")}
                className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                  activeTab === "all"
                    ? getTabActiveClasses()
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                <FileText className="w-5 h-5" />
                All Expenses
                {allExpenses.length > 0 && (
                  <span className="ml-2 px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                    {allExpenses.length}
                  </span>
                )}
              </button>
              {/* Archive Tab - Admin Only */}
              {user?.role === "admin" && (
                <button
                  onClick={() => setActiveTab("archived")}
                  className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                    activeTab === "archived"
                      ? getTabActiveClasses()
                      : "text-gray-600 hover:text-gray-800"
                  }`}
                >
                  <History className="w-5 h-5" />
                  Archived
                  {archivedExpenses.length > 0 && (
                    <span className="ml-2 px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded-full">
                      {archivedExpenses.length}
                    </span>
                  )}
                </button>
              )}
              {/* User Management Tab - Admin Only */}
              {user?.role === "admin" && (
                <button
                  onClick={() => setActiveTab("users")}
                  className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                    activeTab === "users"
                      ? getTabActiveClasses()
                      : "text-gray-600 hover:text-gray-800"
                  }`}
                >
                  <UserCog className="w-5 h-5" />
                  User Management
                </button>
              )}
              {/* Approval Rules Tab */}
              <button
                onClick={() => setActiveTab("approval-policies")}
                className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                  activeTab === "approval-policies"
                    ? getTabActiveClasses()
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                <CheckCircle className="w-5 h-5" />
                Approval Rules
              </button>
              {/* Analytics Tab */}
              <button
                onClick={() => setActiveTab("analytics")}
                className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                  activeTab === "analytics"
                    ? getTabActiveClasses()
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                <TrendingUp className="w-5 h-5" />
                Analytics
              </button>
              {/* AP2 Automation Tab - AP2 Intent Mandates */}
              <button
                onClick={() => setActiveTab("ai-assistant")}
                className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                  activeTab === "ai-assistant"
                    ? getTabActiveClasses()
                    : "text-gray-600 hover:text-gray-800"
                }`}
                title="AP2 Protocol - AI Agent Automation"
              >
                <Bot className="w-5 h-5" />
                AP2 Automation
              </button>
            </div>
          </div>

          {/* Dashboard Stats Cards - Show when no specific tab content */}
          {activeTab === "pending" && dashboardStats && (
            <div className="mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Users</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {dashboardStats.users?.total || 0}
                    </p>
                  </div>
                  <Users className="w-10 h-10 text-blue-500 opacity-50" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Active Users</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {dashboardStats.users?.active_30d || 0}
                    </p>
                  </div>
                  <Activity className="w-10 h-10 text-green-500 opacity-50" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Expenses</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {dashboardStats.expenses?.total_count || 0}
                    </p>
                  </div>
                  <DollarSign className="w-10 h-10 text-purple-500 opacity-50" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-indigo-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Monthly Revenue</p>
                    <p className="text-2xl font-bold text-gray-900">
                      $
                      {(dashboardStats.revenue?.monthly_recurring || 0).toFixed(
                        2,
                      )}
                    </p>
                  </div>
                  <TrendingUp className="w-10 h-10 text-indigo-500 opacity-50" />
                </div>
              </div>
            </div>
          )}

          {/* Stats Cards - Only show for pending tab */}
          {activeTab === "pending" && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Pending Requests</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {pendingStats.total}
                    </p>
                  </div>
                  <Clock className="w-10 h-10 text-blue-600" />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Amount</p>
                    <p className="text-2xl font-bold text-gray-800">
                      ${formatCurrency(pendingStats.totalAmount)}
                    </p>
                  </div>
                  <DollarSign className="w-10 h-10 text-green-500" />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Pending Submitters</p>
                    <p className="text-2xl font-bold text-gray-800">
                      {pendingStats.uniqueUsers}
                    </p>
                  </div>
                  <Users className="w-10 h-10 text-blue-500" />
                </div>
              </div>
            </div>
          )}

          {/* Stats Cards - Show for all expenses tab */}
          {activeTab === "all" && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Expenses</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {allExpensesStats.total}
                    </p>
                  </div>
                  <FileText className="w-8 h-8 text-blue-500 opacity-50" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Pending</p>
                    <p className="text-2xl font-bold text-yellow-600">
                      {allExpensesStats.pending}
                    </p>
                    <p className="text-sm text-gray-500">
                      ${formatCurrency(allExpensesStats.pendingAmount)}
                    </p>
                  </div>
                  <Clock className="w-8 h-8 text-yellow-500 opacity-50" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Approved</p>
                    <p className="text-2xl font-bold text-green-600">
                      {allExpensesStats.approved}
                    </p>
                    <p className="text-sm text-gray-500">
                      ${formatCurrency(allExpensesStats.approvedAmount)}
                    </p>
                  </div>
                  <CheckCircle className="w-8 h-8 text-green-500 opacity-50" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Rejected</p>
                    <p className="text-2xl font-bold text-red-600">
                      {allExpensesStats.rejected}
                    </p>
                  </div>
                  <XCircle className="w-8 h-8 text-red-500 opacity-50" />
                </div>
              </div>
            </div>
          )}

          {/* Search and Filter - Show on pending, all, and archived tabs */}
          {(activeTab === "pending" ||
            activeTab === "all" ||
            activeTab === "archived") && (
            <div className="bg-white rounded-lg shadow p-4 mb-6">
              <div className="flex items-center gap-3 flex-wrap">
                {/* Search Box */}
                <div className="flex items-center gap-2 flex-1 min-w-[250px]">
                  <Search className="w-5 h-5 text-gray-600" />
                  <input
                    type="text"
                    placeholder="Search by ID, vendor, description, category, user..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                      title="Clear search"
                    >
                      ×
                    </button>
                  )}
                </div>

                {/* Status Filter - Only show on All Expenses tab */}
                {activeTab === "all" && (
                  <>
                    <div className="border-l border-gray-300 h-8 mx-2"></div>
                    <Filter className="w-5 h-5 text-gray-600 flex-shrink-0" />
                    <label
                      htmlFor="status-filter"
                      className="text-sm font-medium text-gray-700 flex-shrink-0"
                    >
                      Status:
                    </label>
                    <select
                      id="status-filter"
                      name="statusFilter"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[150px] bg-white"
                    >
                      <option value="all">All Statuses</option>
                      <option value="pending">Pending</option>
                      <option value="approved">Approved</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </>
                )}
              </div>
            </div>
          )}

          {/* User Management Tab */}
          {activeTab === "users" && <UserManagementDashboard />}

          {/* Approval Rules Tab */}
          {activeTab === "approval-policies" && <ApprovalPolicies />}

          {/* Analytics Tab */}
          {activeTab === "analytics" && <AnalyticsDashboard />}

          {/* AP2 Automation Tab - AP2 Intent Mandates & Agent Protocol */}
          {activeTab === "ai-assistant" && <AIAssistant />}

          {/* Expenses List - Show for pending, all, and archived tabs */}
          {(activeTab === "pending" ||
            activeTab === "all" ||
            activeTab === "archived") && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-blue-600" />
                  {activeTab === "pending"
                    ? "Pending Expense Requests"
                    : activeTab === "archived"
                      ? "Archived Expenses"
                      : "Expense History"}
                </h2>
                <div className="flex items-center gap-3">
                  {currentExpenses.length > 0 && (
                    <span className="text-sm text-gray-600">
                      {currentExpenses.length} expense
                      {currentExpenses.length !== 1 ? "s" : ""}
                      {selectedExpenses.length > 0 &&
                        ` (${selectedExpenses.length} selected)`}
                    </span>
                  )}

                  {/* Bulk Action Buttons for "All Expenses" tab */}
                  {user?.role === "admin" && activeTab === "all" && (
                    <>
                      {selectedExpenses.length > 0 && (
                        <button
                          onClick={handleArchiveSelected}
                          disabled={processing}
                          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                          title="Archive selected expenses"
                        >
                          <History className="w-4 h-4" />
                          Archive Selected ({selectedExpenses.length})
                        </button>
                      )}
                      <button
                        onClick={handleArchiveAllExpenses}
                        disabled={processing || currentExpenses.length === 0}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                        title="Archive all approved and rejected expenses"
                      >
                        <History className="w-4 h-4" />
                        Archive All
                      </button>
                    </>
                  )}

                  {/* Bulk Action Buttons for "Archived" tab */}
                  {user?.role === "admin" && activeTab === "archived" && (
                    <>
                      {selectedExpenses.length > 0 && (
                        <button
                          onClick={handleUnarchiveSelected}
                          disabled={processing}
                          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                          title="Restore selected expenses to active"
                        >
                          <Upload className="w-4 h-4" />
                          Restore Selected ({selectedExpenses.length})
                        </button>
                      )}
                      <button
                        onClick={handleUnarchiveAllExpenses}
                        disabled={processing || currentExpenses.length === 0}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                        title="Restore all archived expenses to active"
                      >
                        <Upload className="w-4 h-4" />
                        Restore All
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Sort Controls */}
              {currentExpenses.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-4 pb-4 border-b">
                  {/* Select All Checkbox - Only show on "all" and "archived" tabs for admins */}
                  {user?.role === "admin" &&
                    (activeTab === "all" || activeTab === "archived") && (
                      <>
                        <div className="flex items-center gap-2 mr-4">
                          <input
                            type="checkbox"
                            id="select-all"
                            checked={(() => {
                              const selectableExpenses =
                                activeTab === "all"
                                  ? currentExpenses.filter(
                                      (e) => e.status !== "pending",
                                    )
                                  : currentExpenses;
                              return (
                                selectedExpenses.length ===
                                  selectableExpenses.length &&
                                selectableExpenses.length > 0
                              );
                            })()}
                            onChange={toggleSelectAll}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          <label
                            htmlFor="select-all"
                            className="text-sm font-medium text-gray-700 cursor-pointer"
                          >
                            Select All{" "}
                            {activeTab === "all"
                              ? "(approved/rejected only)"
                              : ""}
                          </label>
                        </div>
                        <div className="border-l border-gray-300 h-6 mx-2"></div>
                      </>
                    )}
                  <span className="text-sm font-medium text-gray-700">
                    Sort by:
                  </span>
                  <button
                    onClick={() => handleSort("date")}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      sortField === "date"
                        ? "bg-blue-100 text-blue-800"
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
                        ? "bg-blue-100 text-blue-800"
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
                        ? "bg-blue-100 text-blue-800"
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
                  <button
                    onClick={() => handleSort("user")}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      sortField === "user"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    User
                    {sortField === "user" &&
                      (sortDirection === "asc" ? (
                        <ArrowUp className="w-4 h-4" />
                      ) : (
                        <ArrowDown className="w-4 h-4" />
                      ))}
                  </button>
                  <button
                    onClick={() => handleSort("status")}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      sortField === "status"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    Status
                    {sortField === "status" &&
                      (sortDirection === "asc" ? (
                        <ArrowUp className="w-4 h-4" />
                      ) : (
                        <ArrowDown className="w-4 h-4" />
                      ))}
                  </button>
                  <button
                    onClick={() => handleSort("vendor")}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      sortField === "vendor"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    Vendor
                    {sortField === "vendor" &&
                      (sortDirection === "asc" ? (
                        <ArrowUp className="w-4 h-4" />
                      ) : (
                        <ArrowDown className="w-4 h-4" />
                      ))}
                  </button>
                  {(sortField !== "date" || sortDirection !== "desc") && (
                    <button
                      onClick={handleResetSort}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors bg-gray-200 text-gray-700 hover:bg-gray-300 border border-gray-400"
                      title="Reset to default sort (Date, newest first)"
                    >
                      Reset
                    </button>
                  )}
                </div>
              )}

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div
                      className={`animate-spin rounded-full h-8 w-8 border-b-2 ${getSpinnerClasses()} mx-auto mb-2`}
                    ></div>
                    <p className="text-gray-600 text-sm">Loading expenses...</p>
                  </div>
                </div>
              ) : currentExpenses.length === 0 ? (
                <div className="text-center py-12">
                  <CheckCircle className="w-16 h-16 text-green-300 mx-auto mb-4" />
                  <p className="text-gray-500 text-lg font-medium">
                    {activeTab === "pending"
                      ? "All caught up!"
                      : "No expenses found"}
                  </p>
                  <p className="text-gray-400 text-sm mt-2">
                    {activeTab === "pending"
                      ? "No pending expense requests at the moment."
                      : "No expenses match the current filter."}
                  </p>
                </div>
              ) : (
                <div className="space-y-4 max-h-[700px] overflow-y-auto">
                  {currentExpenses.map((expense, index) => {
                    const statusKey = normalizeStatusValue(expense.status);
                    const isPending = statusKey === "pending";
                    const isApproved = statusKey === "approved";
                    const isRejected = statusKey === "rejected";
                    return (
                      <div
                        key={expense.id}
                        className={`border rounded-lg p-5 hover:shadow-md transition-shadow bg-gradient-to-r from-white to-gray-50 relative ${
                          selectedExpenses.includes(expense.id)
                            ? "border-blue-500 border-2 shadow-md"
                            : "border-gray-200"
                        }`}
                      >
                      {/* Row Number Badge */}
                      <div className="absolute top-3 left-3 w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-semibold">
                        {(currentPage - 1) * itemsPerPage + index + 1}
                      </div>

                      {/* Selection Checkbox - Only show on "all" and "archived" tabs for admins */}
                      {user?.role === "admin" &&
                        (activeTab === "all" || activeTab === "archived") && (
                          <div className="absolute top-3 right-3">
                            <input
                              type="checkbox"
                              checked={selectedExpenses.includes(expense.id)}
                              onChange={() =>
                                toggleExpenseSelection(expense.id)
                              }
                              disabled={
                                activeTab === "all" &&
                                expense.status?.toLowerCase() === "pending"
                              }
                              className={`w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 ${
                                activeTab === "all" &&
                                expense.status?.toLowerCase() === "pending"
                                  ? "cursor-not-allowed opacity-50"
                                  : "cursor-pointer"
                              }`}
                              title={
                                activeTab === "all" &&
                                expense.status?.toLowerCase() === "pending"
                                  ? "Cannot archive pending expenses - approve or reject first"
                                  : "Select this expense"
                              }
                            />
                          </div>
                        )}

                      <div className="flex items-start justify-between mb-4 ml-10 mr-8">
                        <div className="flex-1">
                          {/* Employee Info */}
                          <div className="flex items-center gap-2 mb-2">
                            <Users className="w-4 h-4 text-gray-500" />
                            <span className="text-sm font-medium text-gray-700">
                              {expense.user_name || "Unknown User"}
                            </span>
                            <span className="text-xs text-gray-500">
                              ({expense.user_email})
                            </span>
                          </div>

                          {/* Expense Info */}
                          <div className="flex items-center gap-2 mb-1">
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
                              className="font-semibold text-gray-800 text-sm"
                              title={expense.id}
                            >
                              {expense.id.substring(0, 8)}...
                            </span>
                            {getStatusBadge(expense.status)}
                          </div>
                          <p className="text-sm text-gray-600 mb-1">
                            {expense.description}
                          </p>
                          <p className="text-xs text-gray-500">
                            {expense.vendor} • {expense.category} • Submitted{" "}
                            {formatDate(expense.created_at || expense.date)}
                          </p>

                          {/* Approval/Rejection Info */}
                          {expense.approved_at && (
                            <p className="text-xs text-gray-600 mt-2">
                          {isApproved ? "Approved" : "Rejected"}{" "}
                              by {expense.approved_by_name || "Admin"} on{" "}
                              {formatDate(expense.approved_at)}
                            </p>
                          )}

                          {/* Transaction ID */}
                          {expense.transaction_id && (
                            <div className="flex items-center gap-2 mt-1">
                              <p className="text-xs text-green-600 font-mono">
                                TX: {expense.transaction_id}
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
                          )}

                          {/* Rejection Reason */}
                          {isRejected &&
                            expense.rejection_reason && (
                              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                                <p className="text-xs font-medium text-red-800 mb-1">
                                  Rejection Reason:
                                </p>
                                <p className="text-xs text-red-700">
                                  {expense.rejection_reason}
                                </p>
                              </div>
                            )}
                        </div>

                        {/* Amount */}
                        <div className="text-right ml-4">
                          <p className="text-2xl font-bold text-gray-800">
                            ${formatCurrency(expense.amount)}
                          </p>
                          <p className="text-xs text-gray-500">
                            {expense.category}
                          </p>
                        </div>
                      </div>

                      {/* Action Buttons - Only for pending expenses */}
                      {isPending && activeTab !== "archived" && (
                          <>
                            {/* Manager Approval Limit Warning */}
                            {user?.role === "manager" &&
                              expense.amount > 5000 && (
                                <div className="pt-4 border-t border-gray-200">
                                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                                    <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                                    <div className="text-sm text-amber-800">
                                      <p className="font-medium">
                                        Admin Approval Required
                                      </p>
                                      <p className="text-amber-700 mt-1">
                                        This expense ($
                                        {expense.amount.toLocaleString()})
                                        exceeds your approval limit of $5,000.
                                        Only admins can approve this expense.
                                      </p>
                                    </div>
                                  </div>
                                </div>
                              )}

                            {/* Action Buttons */}
                            <div className="flex gap-3 pt-4 border-t border-gray-200">
                              <button
                                onClick={() => handleApproveExpense(expense)}
                                disabled={
                                  processing ||
                                  (user?.role === "manager" &&
                                    expense.amount > 5000)
                                }
                                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                                  user?.role === "manager" &&
                                  expense.amount > 5000
                                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                                    : "bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                }`}
                                title={
                                  user?.role === "manager" &&
                                  expense.amount > 5000
                                    ? "Exceeds manager approval limit"
                                    : ""
                                }
                              >
                                <CheckCircle className="w-4 h-4" />
                                {user?.role === "manager" &&
                                expense.amount > 5000
                                  ? "Cannot Approve"
                                  : "Approve via AP2"}
                              </button>
                              <button
                                onClick={() => openRejectModal(expense)}
                                disabled={processing}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                              >
                                <XCircle className="w-4 h-4" />
                                Reject
                              </button>
                            </div>
                          </>
                        )}

                      {/* Unarchive Button - Only for archived expenses (Admin only) */}
                      {activeTab === "archived" && user?.role === "admin" && (
                        <div className="flex gap-3 pt-4 border-t border-gray-200">
                          <button
                            onClick={() => handleUnarchiveExpense(expense.id)}
                            disabled={processing}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                          >
                            <Upload className="w-4 h-4" />
                            Restore to Active
                          </button>
                        </div>
                      )}

                      {processing && (
                        <div
                          className={`mt-3 flex items-center justify-center gap-2 text-sm ${getTextColor()}`}
                        >
                          <div
                            className={`animate-spin rounded-full h-4 w-4 border-b-2 ${getSpinnerClasses()}`}
                          ></div>
                          Processing with AP2 protocol...
                        </div>
                      )}
                    </div>
                  );
                })}
                </div>
              )}
            </div>
          )}

          {/* Pagination for Tabs with Many Items */}
          {shouldPaginate && totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between px-4 py-3 bg-white rounded-lg shadow">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span>
                  Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
                  {Math.min(currentPage * itemsPerPage, sortedExpenses.length)}{" "}
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

          {/* AP2 Protocol Info - Show for pending, all, and archived tabs */}
          {(activeTab === "pending" ||
            activeTab === "all" ||
            activeTab === "archived") && (
            <div className="mt-6 bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-600" />
                Powered by Google AP2 Protocol
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">
                    Authorization
                  </h4>
                  <p className="text-sm text-blue-800">
                    Every approval creates cryptographic Intent Mandates proving
                    authorization
                  </p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-semibold text-green-900 mb-2">
                    Authenticity
                  </h4>
                  <p className="text-sm text-green-800">
                    Cart Mandates ensure accurate transaction details are
                    preserved
                  </p>
                </div>
                <div className="p-4 bg-purple-50 rounded-lg">
                  <h4 className="font-semibold text-purple-900 mb-2">
                    Accountability
                  </h4>
                  <p className="text-sm text-purple-800">
                    Complete audit trail with Payment Mandates for compliance
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Rejection Modal */}
          {rejectingExpense && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                    <XCircle className="w-6 h-6 text-red-600" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-800">
                      Reject Expense
                    </h3>
                    <p className="text-sm text-gray-600">
                      ID: {rejectingExpense.id}
                    </p>
                  </div>
                </div>

                <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Employee:</span>{" "}
                    {rejectingExpense.user_name}
                  </p>
                  <p className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Amount:</span> $
                    {formatCurrency(rejectingExpense.amount)}
                  </p>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Description:</span>{" "}
                    {rejectingExpense.description}
                  </p>
                </div>

                <div className="mb-6">
                  <label
                    htmlFor="rejection-reason"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Rejection Reason (Optional)
                  </label>
                  <textarea
                    id="rejection-reason"
                    name="rejectionReason"
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    rows="4"
                    placeholder="Provide a reason for rejecting this expense..."
                    disabled={processing}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    The employee will see this reason with their rejected
                    expense.
                  </p>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setRejectingExpense(null);
                      setRejectionReason("");
                    }}
                    disabled={processing}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRejectExpense}
                    disabled={processing}
                    className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    {processing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Rejecting...
                      </>
                    ) : (
                      <>
                        <XCircle className="w-4 h-4" />
                        Reject Expense
                      </>
                    )}
                  </button>
                </div>
              </div>
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
              }}
              onCancel={() => {
                setShowReceiptUpload(false);
                setSelectedExpense(null);
              }}
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
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
