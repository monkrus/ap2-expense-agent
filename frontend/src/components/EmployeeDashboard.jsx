import React, { useState, useEffect } from 'react';
import { Receipt, DollarSign, Clock, CheckCircle, Plus, Key, Trash2, History, Filter, Edit2, Upload, Download, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { expenseAPI, APIError } from '../services/api';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../contexts/AuthContext';
import ChangePassword from './ChangePassword';
import ReceiptUpload from './ReceiptUpload';
import ExpenseEdit from './ExpenseEdit';
import ExpenseExport from './ExpenseExport';

const EmployeeDashboard = () => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  const [activeTab, setActiveTab] = useState('active'); // 'active' or 'history'
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showReceiptUpload, setShowReceiptUpload] = useState(false);
  const [showExpenseEdit, setShowExpenseEdit] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all'); // for history tab
  const [sortField, setSortField] = useState('date'); // 'date', 'amount', 'category'
  const [sortDirection, setSortDirection] = useState('desc'); // 'asc' or 'desc'
  const [newExpense, setNewExpense] = useState({
    amount: '',
    category: 'Travel',
    vendor: '',
    description: ''
  });

  // Fetch user's expenses
  useEffect(() => {
    const fetchExpenses = async () => {
      try {
        setLoading(true);
        const report = await expenseAPI.getExpenseReport(user?.id);
        if (report.expenses && Array.isArray(report.expenses)) {
          setExpenses(report.expenses);
        }
      } catch (err) {
        console.error('Error fetching expenses:', err);
        if (err instanceof APIError && err.status === 401) {
          showError('Session expired. Please login again.');
        } else {
          showError('Failed to load expenses.');
        }
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchExpenses();

      // Auto-refresh every 10 seconds
      const interval = setInterval(() => {
        fetchExpenses();
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
    if (!newExpense.amount || !newExpense.vendor || !newExpense.description) {
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
      date: new Date().toISOString().split('T')[0],
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
      description: newExpense.description
    };

    try {
      const result = await expenseAPI.submitExpense(expenseData);

      // Update with real data from server
      setExpenses(prev => prev.map(e =>
        e.id === tempId ? { ...result.expense, _optimistic: false } : e
      ));

      setNewExpense({ amount: '', category: 'Travel', vendor: '', description: '' });
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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                <Receipt className="w-8 h-8 text-indigo-600" />
                My Expenses
              </h1>
              <p className="text-gray-600 mt-2">Submit and track your expense requests</p>
            </div>
            <div className="flex items-center gap-3">
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
                onClick={() => setShowExpenseForm(true)}
                className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
              >
                <Plus className="w-5 h-5" />
                New Expense
              </button>
            </div>
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
                    Amount ($) <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
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
            <div className="space-y-3">
              {currentExpenses.map((expense) => (
                <div
                  key={expense.id}
                  className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${expense._optimistic ? 'opacity-60' : ''}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-gray-800">{expense.id}</span>
                        {getStatusBadge(expense.status)}
                      </div>
                      <p className="text-sm text-gray-600">{expense.description}</p>
                      <p className="text-xs text-gray-500 mt-1">{expense.vendor} • {formatDate(expense.date)}</p>
                      {expense.transaction_id && (
                        <p className="text-xs text-green-600 mt-1 font-mono">Approved - TX: {expense.transaction_id}</p>
                      )}
                      {expense.status === 'rejected' && expense.rejection_reason && (
                        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                          <p className="text-xs font-medium text-red-800 mb-1">Rejection Reason:</p>
                          <p className="text-xs text-red-700">{expense.rejection_reason}</p>
                        </div>
                      )}
                    </div>
                    <div className="text-right flex flex-col items-end gap-2">
                      <div>
                        <p className="text-lg font-bold text-gray-800">${expense.amount.toFixed(2)}</p>
                        <p className="text-xs text-gray-500">{expense.category}</p>
                      </div>
                      {expense.status === 'pending' && !expense._optimistic && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setSelectedExpense(expense);
                              setShowExpenseEdit(true);
                            }}
                            className="flex items-center gap-1 px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                            title="Edit this expense"
                          >
                            <Edit2 className="w-3 h-3" />
                            Edit
                          </button>
                          <button
                            onClick={() => {
                              setSelectedExpense(expense);
                              setShowReceiptUpload(true);
                            }}
                            className="flex items-center gap-1 px-3 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 transition-colors"
                            title="Upload receipt"
                          >
                            <Upload className="w-3 h-3" />
                            Receipt
                          </button>
                          <button
                            onClick={() => handleWithdrawExpense(expense)}
                            className="flex items-center gap-1 px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                            title="Withdraw this expense"
                          >
                            <Trash2 className="w-3 h-3" />
                            Withdraw
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
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
            onSuccess={(data) => {
              success('Receipt uploaded successfully!');
              setShowReceiptUpload(false);
              setSelectedExpense(null);
              // Refresh expenses to show updated data
              setExpenses(prev => prev.map(e =>
                e.id === selectedExpense.id ? { ...e, receipt_url: data.receipt_url } : e
              ));
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
      </div>
    </div>
  );
};

export default EmployeeDashboard;
