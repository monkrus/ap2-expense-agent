import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, XCircle, Clock, Users, DollarSign, TrendingUp, Key, FileText, Filter, ArrowUpDown, ArrowUp, ArrowDown, UserCog, LogOut, Copy, Check, AlertCircle, Plus, Briefcase, Search } from 'lucide-react';
import { expenseAPI, APIError } from '../services/api';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../contexts/AuthContext';
import ChangePassword from './ChangePassword';
import UserManagementDashboard from './UserManagementDashboard';
import RoleBadge from './RoleBadge';
import { getRoleTheme } from '../utils/roleThemes';

const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const { success, error: showError } = useToast();

  // Format currency with commas
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const [activeTab, setActiveTab] = useState('pending'); // 'pending', 'all', 'users', or 'my-expenses'
  const [pendingExpenses, setPendingExpenses] = useState([]);
  const [allExpenses, setAllExpenses] = useState([]);
  const [myExpenses, setMyExpenses] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all'); // for 'all' tab
  const [searchQuery, setSearchQuery] = useState(''); // for searching expenses
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [rejectingExpense, setRejectingExpense] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [sortField, setSortField] = useState('date'); // 'date', 'amount', 'category'
  const [sortDirection, setSortDirection] = useState('desc'); // 'asc' or 'desc'
  const [copiedTxId, setCopiedTxId] = useState(null); // Track copied transaction ID
  const [copiedExpenseId, setCopiedExpenseId] = useState(null); // Track copied expense ID
  const [currentPage, setCurrentPage] = useState(1); // For all expenses pagination
  const [itemsPerPage] = useState(10); // Items per page for all expenses
  const [newExpense, setNewExpense] = useState({
    amount: '',
    category: 'Travel',
    vendor: '',
    description: '',
    date: ''
  });

  // Fetch pending expenses
  useEffect(() => {
    if (activeTab === 'pending') {
      fetchPendingExpenses(true); // Initial load

      // Auto-refresh every 10 seconds (silent)
      const interval = setInterval(() => {
        fetchPendingExpenses(false);
      }, 10000);

      return () => clearInterval(interval);
    }
  }, [activeTab]);

  // Fetch all expenses
  useEffect(() => {
    if (activeTab === 'all') {
      fetchAllExpenses(true); // Initial load

      // Auto-refresh every 10 seconds (silent)
      const interval = setInterval(() => {
        fetchAllExpenses(false);
      }, 10000);

      return () => clearInterval(interval);
    }
  }, [activeTab, statusFilter]);

  // Fetch my expenses
  useEffect(() => {
    if (activeTab === 'my-expenses') {
      fetchMyExpenses(true);

      const interval = setInterval(() => {
        fetchMyExpenses(false);
      }, 10000);

      return () => clearInterval(interval);
    }
  }, [activeTab]);

  // Reset to page 1 when search, filter, or tab changes
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, searchQuery, statusFilter]);

  const fetchMyExpenses = async (isInitialLoad = false) => {
    try {
      if (isInitialLoad) {
        setLoading(true);
      }
      const data = await expenseAPI.getMyExpenses();
      if (data.expenses && Array.isArray(data.expenses)) {
        setMyExpenses(data.expenses);
      }
    } catch (err) {
      console.error('Error fetching my expenses:', err);
      if (isInitialLoad) {
        showError('Failed to load your expenses.');
      }
    } finally {
      if (isInitialLoad) {
        setLoading(false);
      }
    }
  };

  const fetchPendingExpenses = async (isInitialLoad = false) => {
    try {
      // Only show loading spinner on initial load
      if (isInitialLoad) {
        setLoading(true);
      }
      const data = await expenseAPI.getAllPendingExpenses();
      if (data.expenses && Array.isArray(data.expenses)) {
        setPendingExpenses(data.expenses);
      }
    } catch (err) {
      console.error('Error fetching pending expenses:', err);
      if (err instanceof APIError && err.status === 401) {
        showError('Session expired. Please login again.');
      } else if (err instanceof APIError && err.status === 403) {
        showError('You do not have permission to view all expenses.');
      } else if (isInitialLoad) {
        // Only show error on initial load
        showError('Failed to load pending expenses.');
      }
    } finally {
      if (isInitialLoad) {
        setLoading(false);
      }
    }
  };

  const fetchAllExpenses = async (isInitialLoad = false) => {
    try {
      // Only show loading spinner on initial load
      if (isInitialLoad) {
        setLoading(true);
      }
      console.log('[AdminDashboard] Fetching all expenses with statusFilter:', statusFilter);
      const filterValue = statusFilter !== 'all' ? statusFilter : null;
      console.log('[AdminDashboard] Sending filter value to API:', filterValue);
      console.log('[AdminDashboard] API URL will be: /expenses/all' + (filterValue ? `?status=${filterValue}` : ''));

      const data = await expenseAPI.getAllExpenses(filterValue);
      console.log('[AdminDashboard] API Response - full data:', JSON.stringify(data, null, 2));
      console.log('[AdminDashboard] API Response - expenses count:', data.expenses?.length);
      console.log('[AdminDashboard] API Response - pending_count:', data.pending_count);

      if (data.expenses && Array.isArray(data.expenses)) {
        console.log('[AdminDashboard] Setting allExpenses with', data.expenses.length, 'items');
        console.log('[AdminDashboard] Expense IDs:', data.expenses.map(e => e.id));
        console.log('[AdminDashboard] Expense statuses:', data.expenses.map(e => `${e.id}: ${e.status}`));
        setAllExpenses(data.expenses);
      } else {
        console.warn('[AdminDashboard] Invalid response format:', data);
        setAllExpenses([]);
      }
    } catch (err) {
      console.error('Error fetching all expenses:', err);
      console.error('Error details:', err.message, err.status, err.data);
      if (err instanceof APIError && err.status === 401) {
        showError('Session expired. Please login again.');
      } else if (err instanceof APIError && err.status === 403) {
        showError('You do not have permission to view all expenses.');
      } else if (isInitialLoad) {
        // Only show error on initial load
        showError('Failed to load expenses.');
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
      const result = await expenseAPI.approveExpense(expense.id, user?.id || 'admin');

      if (result.success) {
        // Remove from pending list
        setPendingExpenses(prev => prev.filter(e => e.id !== expense.id));
        success(`Expense ${expense.id} approved successfully!`);

        // Refresh all expenses if on that tab
        if (activeTab === 'all') {
          fetchAllExpenses();
        }
      }
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.message : 'Failed to approve expense';
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const openRejectModal = (expense) => {
    setRejectingExpense(expense);
    setRejectionReason('');
  };

  const handleRejectExpense = async () => {
    if (!rejectingExpense) return;

    setProcessing(true);

    try {
      const result = await expenseAPI.rejectExpense(
        rejectingExpense.id,
        user?.id || 'admin',
        rejectionReason || null
      );

      if (result.success) {
        // Remove from pending list
        setPendingExpenses(prev => prev.filter(e => e.id !== rejectingExpense.id));
        success(`Expense ${rejectingExpense.id} rejected.`);
        setRejectingExpense(null);
        setRejectionReason('');

        // Refresh all expenses if on that tab
        if (activeTab === 'all') {
          fetchAllExpenses();
        }
      }
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.message : 'Failed to reject expense';
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const handleSubmitExpense = async (e) => {
    e.preventDefault();
    setProcessing(true);

    if (!newExpense.date) {
      showError('Please select an expense date');
      setProcessing(false);
      return;
    }

    setShowExpenseForm(false);

    const expenseData = {
      user_id: user?.id || 'current_user',
      amount: parseFloat(newExpense.amount),
      category: newExpense.category,
      vendor: newExpense.vendor,
      description: newExpense.description,
      date: newExpense.date
    };

    try {
      const result = await expenseAPI.submitExpense(expenseData);

      if (result.success) {
        success('Expense submitted successfully!');

        // Reset form
        setNewExpense({
          amount: '',
          category: 'Travel',
          vendor: '',
          description: '',
          date: ''
        });

        // Refresh my expenses
        fetchMyExpenses();
      }
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.message : 'Failed to submit expense';
      showError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const openExpenseForm = () => {
    setNewExpense({
      ...newExpense,
      date: new Date().toISOString().split('T')[0]
    });
    setShowExpenseForm(true);
  };

  const handleCopyTransactionId = async (transactionId) => {
    try {
      await navigator.clipboard.writeText(transactionId);
      setCopiedTxId(transactionId);
      success('Transaction ID copied to clipboard!');

      // Reset copied state after 2 seconds
      setTimeout(() => {
        setCopiedTxId(null);
      }, 2000);
    } catch (err) {
      showError('Failed to copy transaction ID');
    }
  };

  const handleCopyExpenseId = async (expenseId) => {
    try {
      await navigator.clipboard.writeText(expenseId);
      setCopiedExpenseId(expenseId);
      success('Expense ID copied to clipboard!');

      // Reset copied state after 2 seconds
      setTimeout(() => {
        setCopiedExpenseId(null);
      }, 2000);
    } catch (err) {
      showError('Failed to copy expense ID');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      withdrawn: 'bg-gray-100 text-gray-600'
    };
    return (
      <span className={`text-xs px-2 py-1 rounded ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  // Sorting function
  const handleSort = (field) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to descending
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortExpenses = (expensesList) => {
    return [...expensesList].sort((a, b) => {
      let aValue, bValue;

      switch (sortField) {
        case 'date':
          aValue = new Date(a.date || a.created_at);
          bValue = new Date(b.date || b.created_at);
          break;
        case 'amount':
          aValue = parseFloat(a.amount);
          bValue = parseFloat(b.amount);
          break;
        case 'category':
          aValue = (a.category || '').toLowerCase();
          bValue = (b.category || '').toLowerCase();
          break;
        case 'user':
          aValue = (a.user_name || '').toLowerCase();
          bValue = (b.user_name || '').toLowerCase();
          break;
        default:
          return 0;
      }

      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
      } else {
        return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
      }
    });
  };

  const pendingStats = {
    total: pendingExpenses.length,
    totalAmount: pendingExpenses.reduce((sum, e) => sum + e.amount, 0),
    uniqueUsers: new Set(pendingExpenses.map(e => e.user_id)).size
  };

  // Apply search filter
  const searchFilteredExpenses = (activeTab === 'pending' ? pendingExpenses : allExpenses).filter(expense => {
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
  const paginatedTabs = ['all', 'pending', 'approved', 'rejected'];
  const shouldPaginate = paginatedTabs.includes(activeTab);
  const totalPages = shouldPaginate ? Math.ceil(sortedExpenses.length / itemsPerPage) : 1;
  const currentExpenses = shouldPaginate
    ? sortedExpenses.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)
    : sortedExpenses;

  const theme = getRoleTheme(user?.role?.toUpperCase() || 'ADMIN');

  // Debug logging
  console.log('[AdminDashboard] Render - activeTab:', activeTab);
  console.log('[AdminDashboard] Render - statusFilter:', statusFilter);
  console.log('[AdminDashboard] Render - pendingExpenses:', pendingExpenses.length);
  console.log('[AdminDashboard] Render - allExpenses:', allExpenses.length);
  console.log('[AdminDashboard] Render - currentExpenses:', currentExpenses.length);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                  <Shield className="w-8 h-8 text-blue-600" />
                  {user?.role === 'manager' ? 'Manager Dashboard' : user?.role === 'accountant' ? 'Accountant Dashboard' : 'Admin Dashboard'}
                </h1>
                <RoleBadge role={user?.role?.toUpperCase() || 'ADMIN'} showCapabilities={true} />
              </div>
              <p className="text-gray-600">{theme.description}</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowChangePassword(true)}
                className="flex items-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
              >
                <Key className="w-5 h-5" />
                Change Password
              </button>
              <button
                onClick={() => activeTab === 'pending' ? fetchPendingExpenses() : fetchAllExpenses()}
                disabled={loading}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50"
              >
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
              <button
                onClick={async () => {
                  await logout();
                  window.location.reload();
                }}
                title="Logout"
                className="flex items-center gap-2 px-4 py-3 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors font-medium"
              >
                <LogOut className="w-5 h-5" />
                Logout
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-lg mb-6">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('pending')}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'pending'
                  ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                  : 'text-gray-600 hover:text-gray-800'
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
              onClick={() => setActiveTab('all')}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'all'
                  ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <FileText className="w-5 h-5" />
              All Expenses
            </button>
            <button
              onClick={() => setActiveTab('my-expenses')}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'my-expenses'
                  ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Briefcase className="w-5 h-5" />
              My Expenses
            </button>
            {/* User Management Tab - Admin Only */}
            {user?.role === 'admin' && (
              <button
                onClick={() => setActiveTab('users')}
                className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                  activeTab === 'users'
                    ? `border-b-2 border-${theme.colors.primary} text-${theme.colors.primary}`
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                <UserCog className="w-5 h-5" />
                User Management
              </button>
            )}
          </div>
        </div>

        {/* Stats Cards - Only show for pending tab */}
        {activeTab === 'pending' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Pending Requests</p>
                  <p className="text-2xl font-bold text-blue-600">{pendingStats.total}</p>
                </div>
                <Clock className="w-10 h-10 text-blue-600" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Total Amount</p>
                  <p className="text-2xl font-bold text-gray-800">${formatCurrency(pendingStats.totalAmount)}</p>
                </div>
                <DollarSign className="w-10 h-10 text-green-500" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Employees</p>
                  <p className="text-2xl font-bold text-gray-800">{pendingStats.uniqueUsers}</p>
                </div>
                <Users className="w-10 h-10 text-blue-500" />
              </div>
            </div>
          </div>
        )}

        {/* Search and Filter - Show on pending and all tabs */}
        {(activeTab === 'pending' || activeTab === 'all') && (
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
                    onClick={() => setSearchQuery('')}
                    className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                    title="Clear search"
                  >
                    ×
                  </button>
                )}
              </div>

              {/* Status Filter - Only show on All Expenses tab */}
              {activeTab === 'all' && (
                <>
                  <div className="border-l border-gray-300 h-8 mx-2"></div>
                  <Filter className="w-5 h-5 text-gray-600 flex-shrink-0" />
                  <label htmlFor="status-filter" className="text-sm font-medium text-gray-700 flex-shrink-0">Status:</label>
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

        {/* My Expenses Tab */}
        {activeTab === 'my-expenses' && (
          <>
            {/* Submit Expense Button */}
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">My Expenses</h2>
                  <p className="text-gray-600">Submit and manage your expense claims</p>
                </div>
                <button
                  onClick={openExpenseForm}
                  className={`flex items-center gap-2 px-6 py-3 ${theme.colors.button} text-white rounded-lg transition-colors font-medium`}
                >
                  <Plus className="w-5 h-5" />
                  New Expense
                </button>
              </div>
            </div>

            {/* Expense Submission Form Modal */}
            {showExpenseForm && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 w-full max-w-md">
                  <h2 className="text-xl font-bold text-gray-800 mb-4">Submit New Expense</h2>

                  <form onSubmit={handleSubmitExpense} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Expense Date <span className="text-red-600">*</span>
                      </label>
                      <input
                        type="date"
                        value={newExpense.date}
                        onChange={(e) => setNewExpense({...newExpense, date: e.target.value})}
                        max={new Date().toISOString().split('T')[0]}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Amount ($) <span className="text-red-600">*</span>
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        value={newExpense.amount}
                        onChange={(e) => setNewExpense({...newExpense, amount: e.target.value})}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="0.00"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                      <select
                        value={newExpense.category}
                        onChange={(e) => setNewExpense({...newExpense, category: e.target.value})}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option>Travel</option>
                        <option>Meals</option>
                        <option>Software</option>
                        <option>Office Supplies</option>
                        <option>Other</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Vendor <span className="text-red-600">*</span>
                      </label>
                      <input
                        type="text"
                        value={newExpense.vendor}
                        onChange={(e) => setNewExpense({...newExpense, vendor: e.target.value})}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Vendor name"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Description <span className="text-red-600">*</span>
                      </label>
                      <textarea
                        value={newExpense.description}
                        onChange={(e) => setNewExpense({...newExpense, description: e.target.value})}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        rows="3"
                        placeholder="Expense description"
                        required
                      />
                    </div>

                    <div className="flex gap-3 mt-6">
                      <button
                        type="button"
                        onClick={() => setShowExpenseForm(false)}
                        className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={processing}
                        className={`flex-1 px-4 py-2 ${theme.colors.button} text-white rounded-lg disabled:opacity-50`}
                      >
                        {processing ? 'Submitting...' : 'Submit'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* My Expenses List */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">My Expense History</h3>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                    <p className="text-gray-500">Loading expenses...</p>
                  </div>
                </div>
              ) : myExpenses.length === 0 ? (
                <div className="text-center py-12">
                  <Briefcase className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500 text-lg font-medium">No expenses yet</p>
                  <p className="text-gray-400 text-sm mt-2">Click "New Expense" to submit your first expense claim.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {myExpenses.map((expense) => (
                    <div
                      key={expense.id}
                      className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow bg-gradient-to-r from-white to-gray-50"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-gray-800">{expense.vendor}</h3>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                              expense.status === 'approved' ? 'bg-green-100 text-green-800' :
                              expense.status === 'rejected' ? 'bg-red-100 text-red-800' :
                              expense.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {expense.status.toUpperCase()}
                            </span>
                          </div>
                          <p className="text-gray-600 text-sm mb-2">{expense.description}</p>
                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span>{expense.category}</span>
                            <span>•</span>
                            <span>{new Date(expense.date || expense.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-blue-600">${formatCurrency(expense.amount)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* User Management Tab */}
        {activeTab === 'users' && (
          <UserManagementDashboard />
        )}

        {/* Expenses List - Only show for pending and all tabs */}
        {(activeTab === 'pending' || activeTab === 'all') && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              {activeTab === 'pending' ? 'Pending Expense Requests' : 'Expense History'}
            </h2>
            {currentExpenses.length > 0 && (
              <span className="text-sm text-gray-600">
                {currentExpenses.length} expense{currentExpenses.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Sort Controls */}
          {currentExpenses.length > 0 && (
            <div className="flex items-center gap-2 mb-4 pb-4 border-b">
              <span className="text-sm font-medium text-gray-700">Sort by:</span>
              <button
                onClick={() => handleSort('date')}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  sortField === 'date'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Date
                {sortField === 'date' && (
                  sortDirection === 'asc' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={() => handleSort('amount')}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  sortField === 'amount'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Amount
                {sortField === 'amount' && (
                  sortDirection === 'asc' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={() => handleSort('category')}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  sortField === 'category'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Category
                {sortField === 'category' && (
                  sortDirection === 'asc' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={() => handleSort('user')}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  sortField === 'user'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                User
                {sortField === 'user' && (
                  sortDirection === 'asc' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />
                )}
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                <p className="text-gray-600 text-sm">Loading expenses...</p>
              </div>
            </div>
          ) : currentExpenses.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-16 h-16 text-green-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg font-medium">
                {activeTab === 'pending' ? 'All caught up!' : 'No expenses found'}
              </p>
              <p className="text-gray-400 text-sm mt-2">
                {activeTab === 'pending'
                  ? 'No pending expense requests at the moment.'
                  : 'No expenses match the current filter.'}
              </p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[300px] overflow-y-auto">
              {currentExpenses.map((expense, index) => (
                <div
                  key={expense.id}
                  className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow bg-gradient-to-r from-white to-gray-50 relative"
                >
                  {/* Row Number Badge */}
                  <div className="absolute top-3 left-3 w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-semibold">
                    {(currentPage - 1) * itemsPerPage + index + 1}
                  </div>
                  <div className="flex items-start justify-between mb-4 ml-10">
                    <div className="flex-1">
                      {/* Employee Info */}
                      <div className="flex items-center gap-2 mb-2">
                        <Users className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-700">
                          {expense.user_name || 'Unknown User'}
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
                        <span className="font-semibold text-gray-800 text-sm" title={expense.id}>
                          {expense.id.substring(0, 8)}...
                        </span>
                        {getStatusBadge(expense.status)}
                      </div>
                      <p className="text-sm text-gray-600 mb-1">{expense.description}</p>
                      <p className="text-xs text-gray-500">
                        {expense.vendor} • {expense.category} • Submitted {formatDate(expense.created_at || expense.date)}
                      </p>

                      {/* Approval/Rejection Info */}
                      {expense.approved_at && (
                        <p className="text-xs text-gray-600 mt-2">
                          {expense.status === 'approved' ? 'Approved' : 'Rejected'} by {expense.approved_by_name || 'Admin'} on {formatDate(expense.approved_at)}
                        </p>
                      )}

                      {/* Transaction ID */}
                      {expense.transaction_id && (
                        <div className="flex items-center gap-2 mt-1">
                          <p className="text-xs text-green-600 font-mono">TX: {expense.transaction_id}</p>
                          <button
                            onClick={() => handleCopyTransactionId(expense.transaction_id)}
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
                      {expense.status === 'rejected' && expense.rejection_reason && (
                        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                          <p className="text-xs font-medium text-red-800 mb-1">Rejection Reason:</p>
                          <p className="text-xs text-red-700">{expense.rejection_reason}</p>
                        </div>
                      )}
                    </div>

                    {/* Amount */}
                    <div className="text-right ml-4">
                      <p className="text-2xl font-bold text-gray-800">${formatCurrency(expense.amount)}</p>
                      <p className="text-xs text-gray-500">{expense.category}</p>
                    </div>
                  </div>

                  {/* Action Buttons - Only for pending expenses */}
                  {expense.status === 'pending' && (
                    <>
                      {/* Manager Approval Limit Warning */}
                      {user?.role === 'manager' && expense.amount > 5000 && (
                        <div className="pt-4 border-t border-gray-200">
                          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-amber-800">
                              <p className="font-medium">Admin Approval Required</p>
                              <p className="text-amber-700 mt-1">
                                This expense (${expense.amount.toLocaleString()}) exceeds your approval limit of $5,000.
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
                          disabled={processing || (user?.role === 'manager' && expense.amount > 5000)}
                          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                            user?.role === 'manager' && expense.amount > 5000
                              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                              : 'bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed'
                          }`}
                          title={user?.role === 'manager' && expense.amount > 5000 ? 'Exceeds manager approval limit' : ''}
                        >
                          <CheckCircle className="w-4 h-4" />
                          {user?.role === 'manager' && expense.amount > 5000 ? 'Cannot Approve' : 'Approve via AP2'}
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

                  {processing && (
                    <div className="mt-3 flex items-center justify-center gap-2 text-sm text-blue-600">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                      Processing with AP2 protocol...
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        )}

        {/* Pagination for Tabs with Many Items */}
        {shouldPaginate && totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between px-4 py-3 bg-white rounded-lg shadow">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, sortedExpenses.length)} of {sortedExpenses.length} expenses</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              {[...Array(totalPages)].map((_, idx) => {
                const pageNum = idx + 1;
                // Show first, last, current, and adjacent pages
                if (pageNum === 1 || pageNum === totalPages || Math.abs(pageNum - currentPage) <= 1) {
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-1 text-sm border rounded ${
                        currentPage === pageNum
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                } else if (Math.abs(pageNum - currentPage) === 2) {
                  return <span key={pageNum} className="px-2 text-gray-500">...</span>;
                }
                return null;
              })}
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* AP2 Protocol Info - Only show for pending and all tabs */}
        {(activeTab === 'pending' || activeTab === 'all') && (
          <div className="mt-6 bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600" />
              Powered by Google AP2 Protocol
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">Authorization</h4>
                <p className="text-sm text-blue-800">Every approval creates cryptographic Intent Mandates proving authorization</p>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <h4 className="font-semibold text-green-900 mb-2">Authenticity</h4>
                <p className="text-sm text-green-800">Cart Mandates ensure accurate transaction details are preserved</p>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <h4 className="font-semibold text-purple-900 mb-2">Accountability</h4>
                <p className="text-sm text-purple-800">Complete audit trail with Payment Mandates for compliance</p>
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
                  <h3 className="text-xl font-bold text-gray-800">Reject Expense</h3>
                  <p className="text-sm text-gray-600">ID: {rejectingExpense.id}</p>
                </div>
              </div>

              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">
                  <span className="font-medium">Employee:</span> {rejectingExpense.user_name}
                </p>
                <p className="text-sm text-gray-600 mb-1">
                  <span className="font-medium">Amount:</span> ${formatCurrency(rejectingExpense.amount)}
                </p>
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Description:</span> {rejectingExpense.description}
                </p>
              </div>

              <div className="mb-6">
                <label htmlFor="rejection-reason" className="block text-sm font-medium text-gray-700 mb-2">
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
                  The employee will see this reason with their rejected expense.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setRejectingExpense(null);
                    setRejectionReason('');
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
              success('Password changed successfully!');
              setShowChangePassword(false);
            }}
          />
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;

