import React, { useState, useEffect } from 'react';
import { Receipt, DollarSign, Clock, CheckCircle, Plus, Key, Trash2, History, Filter, Edit2, Upload, Download, ArrowUpDown, ArrowUp, ArrowDown, User, LogOut } from 'lucide-react';
import { expenseAPI, APIError } from '../services/api';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../contexts/AuthContext';
import ChangePassword from './ChangePassword';
import ReceiptUpload from './ReceiptUpload';
import ExpenseEdit from './ExpenseEdit';
import ExpenseExport from './ExpenseExport';
import ReceiptList from './ReceiptList';

const EmployeeDashboard = () => {
  const { user, logout } = useAuth();
  const { success, error: showError } = useToast();

  const [activeTab, setActiveTab] = useState('active'); // 'active' or 'history'
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showReceiptUpload, setShowReceiptUpload] = useState(false);
  const [showExpenseEdit, setShowExpenseEdit] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showReceiptList, setShowReceiptList] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all'); // for history tab
  const [sortField, setSortField] = useState('date'); // 'date', 'amount', 'category'
  const [sortDirection, setSortDirection] = useState('desc'); // 'asc' or 'desc'
  const [newExpense, setNewExpense] = useState({
    amount: '',
    category: 'Travel',
    vendor: '',
    description: '',
    date: '' // Will be set when form opens
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
        console.error('Error fetching expenses:', err);
        if (err instanceof APIError && err.status === 401) {
          showError('Session expired. Please login again.');
        } else if (isInitialLoad) {
          // Only show error on initial load to avoid spam
          showError('Failed to load expenses.');
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

  const handleWithdrawExpense = async (expense) => {
    if (!window.confirm(`Are you sure you want to withdraw expense ${expense.id}? This action cannot be undone.`)) {
      return;
    }

    try {
      const result = await expenseAPI.withdrawExpense(expense.id);

      if (result.success) {
        // Remove from list
        setExpenses(prev => prev.filter(e => e.id !== expense.id));
        success(`Expense withdrawn successfully`);
      }
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.message : 'Failed to withdraw expense';
      showError(errorMsg);
    }
  };

  const handleExpenseSubmit = async () => {
    if (!newExpense.amount || !newExpense.vendor || !newExpense.description || !newExpense.date) {
      showError('Please fill in all required fields');
      return;
    }

    const tempId = `EXP-${Date.now()}`;
    const optimisticExpense = {
      id: tempId,
      amount: parseFloat(newExpense.amount),
      category: newExpense.category,
      vendor: newExpense.vendor,
      status: 'pending',
      date: newExpense.date,
      description: newExpense.description,
      _optimistic: true
    };

    // Optimistic update
    setExpenses(prev => [...prev, optimisticExpense]);
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

      // Update with real data from server
      setExpenses(prev => prev.map(e =>
        e.id === tempId ? { ...result.expense, _optimistic: false } : e
      ));

      setNewExpense({ amount: '', category: 'Travel', vendor: '', description: '', date: '' });
      success('Expense submitted successfully! Awaiting approval.');
    } catch (err) {
      // Rollback optimistic update
      setExpenses(prev => prev.filter(e => e.id !== tempId));

      const errorMsg = err instanceof APIError ? err.message : 'Failed to submit expense';
      showError(errorMsg);
      setShowExpenseForm(true);
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

  // Filter expenses based on active tab and filters
  const activeExpenses = expenses.filter(e => e.status === 'pending');
  const historyExpenses = expenses.filter(e => {
    if (statusFilter === 'all') return true;
    return e.status === statusFilter;
  });

  const currentExpenses = sortExpenses(activeTab === 'active' ? activeExpenses : historyExpenses);

  const stats = {
    total: expenses.reduce((sum, e) => sum + e.amount, 0),
    pending: expenses.filter(e => e.status === 'pending').length,
    approved: expenses.filter(e => e.status === 'approved').length
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                <Receipt className="w-8 h-8 text-indigo-600" />
                My Expenses
              </h1>
              <p className="text-gray-600 mt-2">Submit and track your expense requests</p>
            </div>

            {/* User Profile Section */}
            <div className="flex items-center gap-4">
              <div className="text-right border-r border-gray-300 pr-4">
                <div className="flex items-center gap-2 justify-end">
                  <User className="w-4 h-4 text-gray-600" />
                  <p className="text-sm font-semibold text-gray-800">
                    {user?.full_name || user?.username || 'User'}
                  </p>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  {user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1).toLowerCase() : 'Employee'}
                </p>
                <p className="text-xs text-gray-400">{user?.email}</p>
              </div>
              <button
                onClick={async () => {
                  await logout();
                  window.location.href = '/login';
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
                setNewExpense(prev => ({ ...prev, date: new Date().toISOString().split('T')[0] }));
                setShowExpenseForm(true);
              }}
              className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
            >
              <Plus className="w-5 h-5" />
              New Expense
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Submitted</p>
                <p className="text-2xl font-bold text-gray-800">${stats.total.toFixed(2)}</p>
              </div>
              <DollarSign className="w-10 h-10 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Pending Approval</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
              </div>
              <Clock className="w-10 h-10 text-yellow-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Approved</p>
                <p className="text-2xl font-bold text-green-600">{stats.approved}</p>
              </div>
              <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-lg mb-6">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('active')}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'active'
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Clock className="w-5 h-5" />
              Active Expenses
              {stats.pending > 0 && (
                <span className="ml-2 px-2 py-1 text-xs bg-indigo-100 text-indigo-800 rounded-full">
                  {stats.pending}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'history'
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <History className="w-5 h-5" />
              History
            </button>
          </div>
        </div>

        {/* Filter for History tab */}
        {activeTab === 'history' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex items-center gap-3">
              <Filter className="w-5 h-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Filter by Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="all">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="withdrawn">Withdrawn</option>
              </select>
            </div>
          </div>
        )}

        {/* Expense Form Modal */}
        {showExpenseForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h2 className="text-xl font-bold text-gray-800 mb-4">Submit New Expense</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Expense Date <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="date"
                    value={newExpense.date}
                    onChange={(e) => setNewExpense({...newExpense, date: e.target.value})}
                    max={new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Amount ($) <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="number"
                    step="1"
                    value={newExpense.amount}
                    onChange={(e) => setNewExpense({...newExpense, amount: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="0.00"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={newExpense.category}
                    onChange={(e) => setNewExpense({...newExpense, category: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
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
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
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
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
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
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Submit
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Expense List */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800">
              {activeTab === 'active' ? 'Active Expenses' : 'Expense History'}
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
                    ? 'bg-indigo-100 text-indigo-700'
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
                    ? 'bg-indigo-100 text-indigo-700'
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
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Category
                {sortField === 'category' && (
                  sortDirection === 'asc' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />
                )}
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-2"></div>
                <p className="text-gray-600 text-sm">Loading expenses...</p>
              </div>
            </div>
          ) : currentExpenses.length === 0 ? (
            <div className="text-center py-12">
              {activeTab === 'active' ? (
                <>
                  <CheckCircle className="w-16 h-16 text-green-300 mx-auto mb-4" />
                  <p className="text-gray-500 text-lg font-medium">All caught up!</p>
                  <p className="text-gray-400 text-sm mt-2">No pending expenses at the moment.</p>
                </>
              ) : (
                <>
                  <Receipt className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No expenses match the current filter.</p>
                </>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">ID</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Date</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Category</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Vendor</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Description</th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">Amount</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Status</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {currentExpenses.map((expense) => (
                    <React.Fragment key={expense.id}>
                      <tr className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${expense._optimistic ? 'opacity-60' : ''}`}>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-800 truncate max-w-[120px]" title={expense.id}>
                              {expense.id}
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
                          <div className="truncate" title={expense.description}>
                            {expense.description}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right text-sm font-semibold text-gray-800 whitespace-nowrap">
                          ${expense.amount.toFixed(2)}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {getStatusBadge(expense.status)}
                        </td>
                        <td className="py-3 px-4">
                          {expense.status === 'pending' && !expense._optimistic && (
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
                                className="p-1.5 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 transition-colors"
                                title="Upload receipt"
                              >
                                <Upload className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleWithdrawExpense(expense)}
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
                            <p className="text-xs text-green-700 font-mono">
                              <span className="font-semibold">Transaction ID:</span> {expense.transaction_id}
                            </p>
                          </td>
                        </tr>
                      )}
                      {/* Rejection reason row */}
                      {expense.status === 'rejected' && expense.rejection_reason && (
                        <tr className="border-b border-gray-100">
                          <td colSpan="8" className="py-2 px-4 bg-red-50">
                            <p className="text-xs text-red-700">
                              <span className="font-semibold">Rejection Reason:</span> {expense.rejection_reason}
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
        </div>

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

        {/* Receipt Upload Modal */}
        {showReceiptUpload && selectedExpense && (
          <ReceiptUpload
            expenseId={selectedExpense.id}
            onSuccess={async (data) => {
              success('Receipt uploaded successfully!');
              setShowReceiptUpload(false);
              setSelectedExpense(null);
              // Refresh expense data to get updated receipt count
              try {
                const report = await expenseAPI.getExpenseReport(user?.id);
                if (report.expenses && Array.isArray(report.expenses)) {
                  setExpenses(report.expenses);
                }
              } catch (err) {
                console.error('Error refreshing expenses:', err);
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
              success('Expense updated successfully!');
              setShowExpenseEdit(false);
              setSelectedExpense(null);
              // Update the expense in the list
              setExpenses(prev => prev.map(e =>
                e.id === updatedExpense.id ? updatedExpense : e
              ));
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
      </div>
    </div>
  );
};

export default EmployeeDashboard;